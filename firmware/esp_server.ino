// ================================================
// Server ESP32 firmware: measurement, forwarding, actions.
// This file is intentionally verbose and heavily commented for non-programmers.
// The server behaves like a small post office:
//   1) It forwards PC <-> Client messages without changing them.
//   2) It executes local actions (motor, light sensor, magnets).
//   3) It streams force measurements when requested.
#include <esp_now.h>          // ESP-NOW wireless communication library
#include <WiFi.h>             // WiFi library (required for ESP-NOW)
#include "FastAccelStepper.h" // Fast stepper motor control library

/*
Message header (little-endian, with XOR checksum):
  msg_type(u8)     - what the message means
  seq(u32)         - running number so PC can match ACK/NACK
  payload_len(u16) - how many payload bytes follow
  src(u8)          - who sent it
  dst(u8)          - who should receive it
  flags(u8)        - options (e.g., ACK required)
  checksum(u8)     - XOR of all other header bytes and payload

Message types:
  0x01 CMD_MOTOR        payload: action(u8), dir(u8), speed_us(u16)
  0x02 CMD_LIGHT        payload: none (ACK payload: light_state(u8))
  0x03 CMD_FORCE_START  payload: period_us(u32), device(u8)
  0x04 CMD_FORCE_STOP   payload: none
  0x05 CMD_MAGNET       payload: channel(u8), state(u8)
  0x80 MSG_ACK          payload: optional
  0x81 MSG_NACK         payload: error_code(u8)
  0x90 DATA_FORCE       payload: time_us(u32), value(i16), device(u8)

Error codes:
  1 BAD_LEN, 2 BAD_MSG, 3 BAD_PAYLOAD
*/

// ----- Hardware pins (change only if your wiring changes) -----
// Motor driver pins
#define MOTOR_STEP_PIN 22
#define MOTOR_DIR_PIN 23
#define MOTOR_ENABLE_PIN 21
#define MOTOR_ACCELERATION_STEPS 2000
#define MIN_STEP_INTERVAL_US 200

// Light sensor (null position) pin
#define LIGHT_SENSOR_PIN 4

// Force sensors (ADC) and magnets (digital outputs)
#define FORCE_SENSOR_RIGHT_PIN 32
#define FORCE_SENSOR_LEFT_PIN 33
#define MAGNET_RIGHT_PIN 18
#define MAGNET_LEFT_PIN 19

#define MAC_CLIENT {0x14, 0x33, 0x5C, 0x5B, 0xB1, 0xEC}  // Client: 14:33:5C:5B:B1:EC

// ----- Routing addresses in the message header -----
enum {
  ADDR_PC = 1,
  ADDR_SERVER = 2,
  ADDR_CLIENT = 3
};

// ----- Header flags -----
enum {
  FLAG_ACK_REQUIRED = 0x01
};

// ----- Message types -----
enum {
  CMD_MOTOR = 0x01,
  CMD_LIGHT = 0x02,
  CMD_FORCE_START = 0x03,
  CMD_FORCE_STOP = 0x04,
  CMD_MAGNET = 0x05,
  MSG_ACK = 0x80,
  MSG_NACK = 0x81,
  DATA_FORCE = 0x90
};

// ----- Error codes -----
enum {
  ERR_BAD_LEN = 1,
  ERR_BAD_MSG = 2,
  ERR_BAD_PAYLOAD = 3
};

typedef struct __attribute__((packed)) {
  uint8_t  msg_type;
  uint32_t seq;
  uint16_t payload_len;
  uint8_t  src;
  uint8_t  dst;
  uint8_t  flags;
  uint8_t  checksum;  // XOR of header (excluding checksum) + payload
} MessageHeader;

// Fixed MAC of the client device (ESP-NOW peer).
static const uint8_t kClientMacAddress[] = MAC_CLIENT;

// Buffer sizes (kept small to avoid memory pressure).
static const size_t MAX_MSG_SIZE = 256;   // Raw (decoded) message size
static const size_t MAX_COBS_SIZE = 300;  // COBS framed size
static const size_t ESPNOW_MAX_SIZE = 250;
static const uint8_t ESPNOW_QUEUE_SIZE = 8;

// Serial receive buffer (COBS framed input).
static uint8_t serial_cobs_rx_buffer[MAX_COBS_SIZE];
static size_t serial_cobs_rx_length = 0;

// Temporary decode/encode buffers for serial frames.
static uint8_t serial_decode_buffer[MAX_MSG_SIZE];
static uint8_t serial_encode_buffer[MAX_COBS_SIZE + 1];

typedef struct {
  uint8_t data[ESPNOW_MAX_SIZE];
  uint8_t len;
} EspNowPacket;

// Small queue for packets arriving from ESP-NOW.
static volatile uint8_t espnow_queue_head = 0;
static volatile uint8_t espnow_queue_tail = 0;
static EspNowPacket espnow_queue[ESPNOW_QUEUE_SIZE];
static portMUX_TYPE espnow_queue_mutex = portMUX_INITIALIZER_UNLOCKED;

// Motor control state (applied in loop, not in callbacks).
FastAccelStepperEngine engine = FastAccelStepperEngine();
FastAccelStepper *stepper = NULL;
static bool motor_direction_forward = true;
static bool motor_start_pending = false;
static bool motor_stop_pending = false;
static int motor_step_interval_us = 1000;

// Measurement state (force sensor streaming).
static bool force_stream_enabled = false;
static uint32_t force_sample_period_us = 10000;
static uint32_t next_force_sample_us = 0;
static uint8_t force_sensor_select = 0;
static uint32_t server_sequence_counter = 1;

// Convert raw ADC value to approximate Newtons.
static int16_t adc_to_newton(int adc_value) {
  return (int16_t)(0.21586f * (float)adc_value);
}

// COBS encoder/decoder for framed USB serial.
// COBS replaces zero bytes, then uses 0x00 as a message separator.
static size_t cobs_encode(const uint8_t *input, size_t length, uint8_t *output) {
  size_t read_index = 0;
  size_t write_index = 1;
  size_t code_index = 0;
  uint8_t code = 1;

  while (read_index < length) {
    if (input[read_index] == 0) {
      output[code_index] = code;
      code = 1;
      code_index = write_index++;
      read_index++;
    } else {
      output[write_index++] = input[read_index++];
      code++;
      if (code == 0xFF) {
        output[code_index] = code;
        code = 1;
        code_index = write_index++;
      }
    }
  }

  output[code_index] = code;
  return write_index;
}

static size_t cobs_decode(const uint8_t *input, size_t length, uint8_t *output, size_t max_output) {
  size_t read_index = 0;
  size_t write_index = 0;

  while (read_index < length) {
    uint8_t code = input[read_index++];
    if (code == 0 || (read_index + code - 1) > length) {
      return 0;
    }
    for (uint8_t i = 1; i < code; i++) {
      if (write_index >= max_output) {
        return 0;
      }
      output[write_index++] = input[read_index++];
    }
    if (code != 0xFF && read_index < length) {
      if (write_index >= max_output) {
        return 0;
      }
      output[write_index++] = 0;
    }
  }

  return write_index;
}

// Checksum helper: calculate XOR of all bytes in header (excluding checksum field) + payload.
static uint8_t calculate_checksum(const uint8_t *header_ptr, size_t header_len, const uint8_t *payload, size_t payload_len) {
  uint8_t checksum = 0;
  // XOR the header (first 10 bytes, excluding the checksum byte at position 10)
  for (size_t i = 0; i < header_len && i < 10; i++) {
    checksum ^= header_ptr[i];
  }
  // XOR the payload
  for (size_t i = 0; i < payload_len; i++) {
    checksum ^= payload[i];
  }
  return checksum;
}

// Serial TX helper (COBS framing, no blocking work in callbacks).
// (send a message over USB without pausing other work.)
static void serial_send_frame(const uint8_t *data, size_t len) {
  if (len == 0) {
    return;
  }
  size_t encoded_len = cobs_encode(data, len, serial_encode_buffer);
  serial_encode_buffer[encoded_len++] = 0x00;
  Serial.write(serial_encode_buffer, encoded_len);
}

// ACK/NACK helpers for PC commands.
static void send_message_to_pc(uint8_t msg_type, uint32_t seq, const uint8_t *payload, uint16_t payload_len) {
  MessageHeader hdr;
  hdr.msg_type = msg_type;
  hdr.seq = seq;
  hdr.payload_len = payload_len;
  hdr.src = ADDR_SERVER;
  hdr.dst = ADDR_PC;
  hdr.flags = 0;
  hdr.checksum = 0;  // Calculate below

  uint8_t frame[MAX_MSG_SIZE];
  size_t total_len = sizeof(MessageHeader) + payload_len;
  if (total_len > sizeof(frame)) {
    return;
  }
  memcpy(frame, &hdr, sizeof(MessageHeader));
  if (payload_len > 0 && payload != NULL) {
    memcpy(frame + sizeof(MessageHeader), payload, payload_len);
  }
  
  // Calculate and set checksum
  uint8_t checksum = calculate_checksum(frame, sizeof(MessageHeader), payload, payload_len);
  ((MessageHeader *)frame)->checksum = checksum;
  
  serial_send_frame(frame, total_len);
}

static void send_ack(uint32_t seq, const uint8_t *payload, uint16_t payload_len) {
  send_message_to_pc(MSG_ACK, seq, payload, payload_len);
}

static void send_nack(uint32_t seq, uint8_t error_code) {
  uint8_t payload[1];
  payload[0] = error_code;
  send_message_to_pc(MSG_NACK, seq, payload, 1);
}

// Measurement payload sender (force stream to PC).
static void send_force_data(uint8_t device, int16_t value) {
  uint8_t payload[7];
  uint32_t now_us = micros();
  memcpy(payload, &now_us, sizeof(uint32_t));
  memcpy(payload + 4, &value, sizeof(int16_t));
  payload[6] = device;

  uint32_t seq = server_sequence_counter++;
  send_message_to_pc(DATA_FORCE, seq, payload, sizeof(payload));
}

// Actions: motor control.
static void motor_apply_start(uint8_t dir, uint16_t speed_us) {
  if (speed_us < MIN_STEP_INTERVAL_US) {
    speed_us = MIN_STEP_INTERVAL_US;
  }
  motor_step_interval_us = (int)speed_us;
  motor_direction_forward = (dir != 0);
  motor_start_pending = true;
}

static void motor_apply_stop(void) {
  motor_stop_pending = true;
}

// Actions: execute commands addressed to the server.
static void handle_command(const MessageHeader *hdr, const uint8_t *payload) {
  bool ack_required = (hdr->flags & FLAG_ACK_REQUIRED) != 0;
  switch (hdr->msg_type) {
    case CMD_MOTOR: {
      // Motor command: action(0=stop,1=start), dir(0=backward,1=forward), speed_us.
      if (hdr->payload_len != 4) {
        if (ack_required) {
          send_nack(hdr->seq, ERR_BAD_PAYLOAD);
        }
        return;
      }
      uint8_t action = payload[0];
      uint8_t dir = payload[1];
      uint16_t speed_us = 0;
      memcpy(&speed_us, payload + 2, sizeof(uint16_t));
      if (action == 0) {
        motor_apply_stop();
      } else {
        motor_apply_start(dir, speed_us);
      }
      if (ack_required) {
        send_ack(hdr->seq, NULL, 0);
      }
      break;
    }
    case CMD_LIGHT: {
      // Light sensor query: returns digital value from LIGHT_SENSOR_PIN.
      if (hdr->payload_len != 0) {
        if (ack_required) {
          send_nack(hdr->seq, ERR_BAD_PAYLOAD);
        }
        return;
      }
      uint8_t light_state = (uint8_t)digitalRead(LIGHT_SENSOR_PIN);
      if (ack_required) {
        send_ack(hdr->seq, &light_state, 1);
      }
      break;
    }
    case CMD_FORCE_START: {
      // Start measurement: period_us (sample interval) + device selector.
      if (hdr->payload_len != 5) {
        if (ack_required) {
          send_nack(hdr->seq, ERR_BAD_PAYLOAD);
        }
        return;
      }
      uint32_t period = 0;
      memcpy(&period, payload, sizeof(uint32_t));
      uint8_t device = payload[4];
      if (period == 0 || device > 2) {
        if (ack_required) {
          send_nack(hdr->seq, ERR_BAD_PAYLOAD);
        }
        return;
      }
      force_sample_period_us = period;
      force_sensor_select = device;
      force_stream_enabled = true;
      next_force_sample_us = micros();
      if (ack_required) {
        uint8_t ack_payload[5];
        memcpy(ack_payload, &force_sample_period_us, sizeof(uint32_t));
        ack_payload[4] = force_sensor_select;
        send_ack(hdr->seq, ack_payload, sizeof(ack_payload));
      }
      break;
    }
    case CMD_FORCE_STOP: {
      // Stop measurement stream immediately.
      if (hdr->payload_len != 0) {
        if (ack_required) {
          send_nack(hdr->seq, ERR_BAD_PAYLOAD);
        }
        return;
      }
      force_stream_enabled = false;
      if (ack_required) {
        send_ack(hdr->seq, NULL, 0);
      }
      break;
    }
    case CMD_MAGNET: {
      // Magnet control: channel(0=right,1=left,2=both), state(0=off,1=on).
      if (hdr->payload_len != 2) {
        if (ack_required) {
          send_nack(hdr->seq, ERR_BAD_PAYLOAD);
        }
        return;
      }
      uint8_t channel = payload[0];
      uint8_t state = payload[1];
      if (channel > 2) {
        if (ack_required) {
          send_nack(hdr->seq, ERR_BAD_PAYLOAD);
        }
        return;
      }
      if (channel == 0 || channel == 2) {
        digitalWrite(MAGNET_RIGHT_PIN, state ? HIGH : LOW);
      }
      if (channel == 1 || channel == 2) {
        digitalWrite(MAGNET_LEFT_PIN, state ? HIGH : LOW);
      }
      if (ack_required) {
        uint8_t ack_payload[2] = {channel, state};
        send_ack(hdr->seq, ack_payload, sizeof(ack_payload));
      }
      break;
    }
    default:
      if (ack_required) {
        send_nack(hdr->seq, ERR_BAD_MSG);
      }
      break;
  }
}

// Router: forward PC->client or execute local command.
static void handle_decoded_frame(const uint8_t *frame, size_t len) {
  if (len < sizeof(MessageHeader)) {
    return;
  }
  MessageHeader hdr;
  memcpy(&hdr, frame, sizeof(MessageHeader));

  size_t expected_len = sizeof(MessageHeader) + hdr.payload_len;
  if (expected_len != len) {
    if (hdr.src == ADDR_PC && hdr.dst == ADDR_SERVER && (hdr.flags & FLAG_ACK_REQUIRED)) {
      send_nack(hdr.seq, ERR_BAD_LEN);
    }
    return;
  }

  const uint8_t *payload = frame + sizeof(MessageHeader);
  
  // Verify checksum (only for PC commands to server)
  if (hdr.dst == ADDR_SERVER && hdr.src == ADDR_PC) {
    uint8_t expected_checksum = calculate_checksum(frame, sizeof(MessageHeader), payload, hdr.payload_len);
    if (hdr.checksum != expected_checksum) {
      if (hdr.flags & FLAG_ACK_REQUIRED) {
        send_nack(hdr.seq, ERR_BAD_MSG);  // Use BAD_MSG for checksum failure
      }
      return;
    }
  }

  if (hdr.dst == ADDR_CLIENT) {
    // Forward PC -> Client without looking inside the payload.
    esp_now_send(kClientMacAddress, frame, len);
    return;
  }

  if (hdr.dst == ADDR_SERVER) {
    // Local action on server hardware.
    handle_command(&hdr, payload);
  }
}

// Router: USB serial RX (COBS), non-blocking.
// We collect bytes until 0x00, then decode the frame and dispatch it.
static void handle_serial_rx(void) {
  while (Serial.available() > 0) {
    uint8_t b = (uint8_t)Serial.read();
    if (b == 0x00) {
      if (serial_cobs_rx_length > 0) {
        size_t decoded_len = cobs_decode(serial_cobs_rx_buffer, serial_cobs_rx_length, serial_decode_buffer, sizeof(serial_decode_buffer));
        if (decoded_len > 0) {
          handle_decoded_frame(serial_decode_buffer, decoded_len);
        }
      }
      serial_cobs_rx_length = 0;
    } else {
      if (serial_cobs_rx_length < sizeof(serial_cobs_rx_buffer)) {
        serial_cobs_rx_buffer[serial_cobs_rx_length++] = b;
      } else {
        serial_cobs_rx_length = 0;
      }
    }
  }
}

// Router: ESP-NOW RX ISR, queue only.
// This runs in interrupt context, so it must be fast and non-blocking.
static void IRAM_ATTR on_espnow_recv(const esp_now_recv_info_t *recv_info, const uint8_t *incomingData, int len) {
  (void)recv_info;
  if (len <= 0 || len > (int)ESPNOW_MAX_SIZE) {
    return;
  }

  portENTER_CRITICAL_ISR(&espnow_queue_mutex);
  uint8_t next_head = (uint8_t)((espnow_queue_head + 1) % ESPNOW_QUEUE_SIZE);
  if (next_head != espnow_queue_tail) {
    espnow_queue[espnow_queue_head].len = (uint8_t)len;
    memcpy(espnow_queue[espnow_queue_head].data, incomingData, len);
    espnow_queue_head = next_head;
  } else {
    // Queue full: drop packet to keep interrupt handler fast.
  }
  portEXIT_CRITICAL_ISR(&espnow_queue_mutex);
}

// Router: forward queued ESP-NOW packets to PC.
static void handle_espnow_rx_queue(void) {
  while (true) {
    portENTER_CRITICAL(&espnow_queue_mutex);
    if (espnow_queue_tail == espnow_queue_head) {
      portEXIT_CRITICAL(&espnow_queue_mutex);
      break;
    }
    EspNowPacket packet = espnow_queue[espnow_queue_tail];
    espnow_queue_tail = (uint8_t)((espnow_queue_tail + 1) % ESPNOW_QUEUE_SIZE);
    portEXIT_CRITICAL(&espnow_queue_mutex);

    serial_send_frame(packet.data, packet.len);
  }
}

// Measurement: periodic force sampling and streaming.
// Runs at the requested period (e.g., 10 ms = 100 Hz).
static void handle_force_stream(void) {
  if (!force_stream_enabled) {
    return;
  }
  uint32_t now = micros();
  if ((int32_t)(now - next_force_sample_us) < 0) {
    return;
  }
  next_force_sample_us = now + force_sample_period_us;

  // device selector: 0 = right, 1 = left, 2 = both.
  if (force_sensor_select == 0 || force_sensor_select == 2) {
    int16_t value = adc_to_newton(analogRead(FORCE_SENSOR_RIGHT_PIN));
    send_force_data(0, value);
  }
  if (force_sensor_select == 1 || force_sensor_select == 2) {
    int16_t value = adc_to_newton(analogRead(FORCE_SENSOR_LEFT_PIN));
    send_force_data(1, value);
  }
}

// Actions: apply pending motor commands.
static void handle_motor_state(void) {
  if (!stepper) {
    return;
  }
  if (motor_start_pending) {
    stepper->setSpeedInUs(motor_step_interval_us);
    stepper->setAcceleration(MOTOR_ACCELERATION_STEPS);
    if (motor_direction_forward) {
      stepper->runForward();
    } else {
      stepper->runBackward();
    }
    motor_start_pending = false;
  }
  if (motor_stop_pending) {
    stepper->stopMove();
    motor_stop_pending = false;
  }
}

void setup() {
  // Basic serial link to the PC.
  Serial.begin(115200);

  // ESP-NOW setup: we only need station mode and one peer (client).
  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    return;
  }
  esp_now_register_recv_cb(on_espnow_recv);

  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(peerInfo));
  memcpy(peerInfo.peer_addr, kClientMacAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);

  // Motor setup (stepper driver).
  engine.init();
  stepper = engine.stepperConnectToPin(MOTOR_STEP_PIN);
  if (stepper) {
    stepper->setDirectionPin(MOTOR_DIR_PIN);
    stepper->setEnablePin(MOTOR_ENABLE_PIN);
    stepper->setAutoEnable(true);
  }

  // Sensor and magnet I/O.
  pinMode(LIGHT_SENSOR_PIN, INPUT);
  pinMode(MAGNET_RIGHT_PIN, OUTPUT);
  pinMode(MAGNET_LEFT_PIN, OUTPUT);
}

void loop() {
  // Router: PC->Client and Client->PC forwarding.
  handle_serial_rx();
  handle_espnow_rx_queue();

  // Measurement: force streaming if enabled.
  handle_force_stream();

  // Actions: apply motor start/stop.
  handle_motor_state();
}
