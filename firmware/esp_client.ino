// ================================================
// Client ESP32 firmware: pegboard sensor node
// Routes commands from PC (via Server) and streams sensor data when enabled.
// This firmware implements binary message protocol with checksum verification.
// Client receives commands from PC (forwarded by Server) and sends ACK/DATA back to PC.
// ================================================
#include <esp_now.h>
#include <WiFi.h>
#include <Adafruit_NeoPixel.h>
#include <Wire.h>

/*
Message header (little-endian, with XOR checksum):
  msg_type(u8)     - what the message means
  seq(u32)         - running number so PC can match ACK/NACK
  payload_len(u16) - how many payload bytes follow
  src(u8)          - who sent it
  dst(u8)          - who should receive it
  flags(u8)        - options (e.g., ACK required)
  checksum(u8)     - XOR of all other header bytes and payload

Message types (CLIENT):
  0x10 CMD_LED_SET_N    payload: Format A: count(u8) + holes[count] + r + g + b
                                 Format B: count(u8) + [hole,r,g,b]×count
  0x11 CMD_LED_SHOW     payload: none
  0x12 CMD_HOLE_START   payload: hole(u8), mode(u8)
  0x13 CMD_HOLE_STOP    payload: none
  0x14 CD_REED_START   payload: period_us(u32)
  0x15 CMD_REED_STOP    payload: none
  0x80 MSG_ACK          payload: optional
  0x81 MSG_NACK         payload: error_code(u8)
  0x91 DATA_REED        payload: time_us(u32), reed_bits(u32)
  0x92 DATA_HALL        payload: hole(u8), plugged(u8), reaction_us(u32), x(i16), y(i16), z(i16)

Routing addresses:
  ADDR_PC=1, ADDR_SERVER=2, ADDR_CLIENT=3
  Commands: src=PC, dst=CLIENT
  ACK/DATA: src=CLIENT, dst=PC

Error codes:
  1 BAD_LEN, 2 BAD_MSG, 3 BAD_PAYLOAD
*/

// ----- Hardware pins -----
#define I2C_SDA 21
#define I2C_SCL 22

// Hole group selection pins (6 groups)
#define GROUP_F 35
#define GROUP_E 32
#define GROUP_D 33
#define GROUP_C 25
#define GROUP_B 26
#define GROUP_A 27

// Hall sensor config
#define HALL_SENSOR_ADRESS 0x0C
#define SENSOR_R1 254
#define SENSOR_R2 253
#define SENSOR_R3 251
#define SENSOR_B  247

// I2C sub-hole addresses
#define SUB_H_0 0x20
#define SUB_H_1 0x22
#define SUB_H_2 0x24
#define SUB_H_3 0x26

// Reed switches (I2C)
#define REED_0 0x21
#define REED_1 0x23
#define REED_2 0x25
#define REED_INT 12

// LED strip
#define LED_PIN 2
#define NUMBER_OF_HOLES 21
#define LEDS_PER_HOLE 8

// ESP-NOW MAC addresses
#define MAC_SERVER {0x14, 0x33, 0x5C, 0x5B, 0xE3, 0x14}  // Server: 14:33:5C:5B:E3:14

// ----- Routing addresses -----
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
  CMD_LED_SET_N = 0x10,
  CMD_LED_SHOW = 0x11,
  CMD_HOLE_START = 0x12,
  CMD_HOLE_STOP = 0x13,
  CMD_REED_START = 0x14,
  CMD_REED_STOP = 0x15,
  MSG_ACK = 0x80,
  MSG_NACK = 0x81,
  DATA_REED = 0x91,
  DATA_HALL = 0x92
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
  uint8_t  checksum;
} MessageHeader;

// ----- Hardware state -----
static const uint8_t kServerMacAddress[] = MAC_SERVER;
static const size_t MAX_MSG_SIZE = 256;
static const size_t ESPNOW_QUEUE_SIZE = 8;

// Hole mapping tables (20 holes indexed 0-19, plus 1 extra for safety)
static const uint8_t hole_group_pins[] = {
  GROUP_F, GROUP_E, GROUP_E, GROUP_D, GROUP_C, GROUP_B, GROUP_B, GROUP_A,
  GROUP_F, GROUP_F, GROUP_E, GROUP_E, GROUP_D, GROUP_D, GROUP_C, GROUP_C,
  GROUP_B, GROUP_B, GROUP_A, GROUP_A, GROUP_A
};
static const uint8_t hole_sub_addresses[] = {
  SUB_H_0, SUB_H_0, SUB_H_1, SUB_H_0, SUB_H_0, SUB_H_0, SUB_H_1, SUB_H_0,
  SUB_H_3, SUB_H_2, SUB_H_3, SUB_H_2, SUB_H_2, SUB_H_3, SUB_H_3, SUB_H_2,
  SUB_H_3, SUB_H_2, SUB_H_2, SUB_H_3, SUB_H_0
};

typedef struct {
  uint8_t data[MAX_MSG_SIZE];
  uint8_t len;
} EspNowPacket;

static volatile uint8_t espnow_queue_head = 0;
static volatile uint8_t espnow_queue_tail = 0;
static EspNowPacket espnow_queue[ESPNOW_QUEUE_SIZE];
static portMUX_TYPE espnow_queue_mutex = portMUX_INITIALIZER_UNLOCKED;

// LED strip controller
static Adafruit_NeoPixel pixels(NUMBER_OF_HOLES * LEDS_PER_HOLE, LED_PIN, NEO_GRB + NEO_KHZ800);

// ----- Measurement state -----
static bool reed_stream_enabled = false;
static uint32_t reed_sample_period_us = 10000;
static uint32_t next_reed_sample_us = 0;
static uint32_t last_reed_value = 0;
static uint32_t client_sequence_counter = 1;

static bool hole_meas_enabled = false;
static uint8_t active_hole = 0;
static uint8_t active_sub_address = SUB_H_0;
static uint8_t hole_meas_mode = 0;
static uint32_t hole_start_time_us = 0;
static bool was_plugged = false;

// Duplicate command protection (simple: remember last processed seq)
static uint32_t last_cmd_seq = 0;
static uint8_t last_cmd_result = MSG_ACK;  // ACK or NACK
static uint8_t last_cmd_error = 0;

// ----- Helper: XOR checksum calculation -----
static uint8_t calculate_checksum(const uint8_t *header_ptr, size_t header_len, const uint8_t *payload, size_t payload_len) {
  uint8_t checksum = 0;
  for (size_t i = 0; i < header_len && i < 10; i++) {
    checksum ^= header_ptr[i];
  }
  for (size_t i = 0; i < payload_len; i++) {
    checksum ^= payload[i];
  }
  return checksum;
}

// ----- ESP-NOW TX: send to Server (which will relay to PC) -----
static void espnow_send_to_server(const uint8_t *data, size_t len) {
  if (len > 0 && len <= 250) {
    esp_now_send(kServerMacAddress, data, len);
  }
}

// ----- Message builders (ACK/NACK/DATA to PC) -----
static void send_message_to_pc(uint8_t msg_type, uint32_t seq, const uint8_t *payload, uint16_t payload_len) {
  MessageHeader hdr;
  hdr.msg_type = msg_type;
  hdr.seq = seq;
  hdr.payload_len = payload_len;
  hdr.src = ADDR_CLIENT;
  hdr.dst = ADDR_PC;  // Logical destination is PC
  hdr.flags = 0;
  hdr.checksum = 0;

  uint8_t frame[MAX_MSG_SIZE];
  size_t total_len = sizeof(MessageHeader) + payload_len;
  if (total_len > sizeof(frame)) {
    return;
  }
  memcpy(frame, &hdr, sizeof(MessageHeader));
  if (payload_len > 0 && payload != NULL) {
    memcpy(frame + sizeof(MessageHeader), payload, payload_len);
  }

  uint8_t checksum = calculate_checksum(frame, sizeof(MessageHeader), payload, payload_len);
  ((MessageHeader *)frame)->checksum = checksum;

  espnow_send_to_server(frame, total_len);
}

static void send_ack(uint32_t seq, const uint8_t *payload, uint16_t payload_len) {
  send_message_to_pc(MSG_ACK, seq, payload, payload_len);
}

static void send_nack(uint32_t seq, uint8_t error_code) {
  uint8_t payload[1] = {error_code};
  send_message_to_pc(MSG_NACK, seq, payload, 1);
}

// ----- Hardware: Reed switches (3x I2C expanders = 24 bits) -----
static void setup_reed(void) {
  pinMode(REED_INT, INPUT_PULLUP);
  Wire.beginTransmission(REED_0);
  Wire.write(0xFF);
  Wire.endTransmission();
  Wire.beginTransmission(REED_1);
  Wire.write(0xFF);
  Wire.endTransmission();
  Wire.beginTransmission(REED_2);
  Wire.write(0xFF);
  Wire.endTransmission();
}

static uint32_t read_reed(void) {
  digitalWrite(GROUP_A, LOW);
  digitalWrite(GROUP_B, LOW);
  digitalWrite(GROUP_C, LOW);
  digitalWrite(GROUP_D, LOW);
  digitalWrite(GROUP_E, LOW);
  digitalWrite(GROUP_F, LOW);

  uint32_t value = 0;
  Wire.requestFrom(REED_2, 1);
  while (Wire.available()) {
    value += Wire.read();
  }
  value = value << 8;
  Wire.requestFrom(REED_1, 1);
  while (Wire.available()) {
    value += Wire.read();
  }
  value = value << 8;
  Wire.requestFrom(REED_0, 1);
  while (Wire.available()) {
    value += Wire.read();
  }
  return (~value) & 0xFFFFFF;
}

// ----- Hardware: Hall sensors (I2C, TLE493D) -----
static void select_hole(uint8_t hole) {
  if (hole >= NUMBER_OF_HOLES) {
    return;
  }
  digitalWrite(GROUP_A, HIGH);
  digitalWrite(GROUP_B, HIGH);
  digitalWrite(GROUP_C, HIGH);
  digitalWrite(GROUP_D, HIGH);
  digitalWrite(GROUP_E, HIGH);
  digitalWrite(GROUP_F, HIGH);
  digitalWrite(hole_group_pins[hole], LOW);
  active_sub_address = hole_sub_addresses[hole];
}

static void deselect_all_holes(void) {
  digitalWrite(GROUP_A, LOW);
  digitalWrite(GROUP_B, LOW);
  digitalWrite(GROUP_C, LOW);
  digitalWrite(GROUP_D, LOW);
  digitalWrite(GROUP_E, LOW);
  digitalWrite(GROUP_F, LOW);

  Wire.beginTransmission(SUB_H_0);
  Wire.write(0xFF);
  Wire.write(0xFF);
  Wire.endTransmission();
  Wire.beginTransmission(SUB_H_1);
  Wire.write(0xFF);
  Wire.write(0xFF);
  Wire.endTransmission();
  Wire.beginTransmission(SUB_H_2);
  Wire.write(0xFF);
  Wire.write(0xFF);
  Wire.endTransmission();
  Wire.beginTransmission(SUB_H_3);
  Wire.write(0xFF);
  Wire.write(0xFF);
  Wire.endTransmission();

  digitalWrite(GROUP_A, HIGH);
  digitalWrite(GROUP_B, HIGH);
  digitalWrite(GROUP_C, HIGH);
  digitalWrite(GROUP_D, HIGH);
  digitalWrite(GROUP_E, HIGH);
  digitalWrite(GROUP_F, HIGH);
}

static void select_sensor(uint8_t sensor_id) {
  Wire.beginTransmission(active_sub_address);
  Wire.write(sensor_id);
  Wire.write(0x00);
  Wire.endTransmission();
}

static void deselect_sensor(void) {
  Wire.beginTransmission(active_sub_address);
  Wire.write(0xFF);
  Wire.write(0xFF);
  Wire.endTransmission();
}

static void start_single_measurement(void) {
  Wire.beginTransmission(HALL_SENSOR_ADRESS);
  Wire.write(0x3E);
  Wire.endTransmission();
}

static void read_measurement(int16_t *x, int16_t *y, int16_t *z) {
  Wire.beginTransmission(HALL_SENSOR_ADRESS);
  Wire.write(0x4E);
  Wire.endTransmission();
  Wire.requestFrom(HALL_SENSOR_ADRESS, 9);
  if (Wire.available() >= 7) {
    Wire.read();  // status byte
    *x = Wire.read() << 8;
    *x += Wire.read();
    *y = Wire.read() << 8;
    *y += Wire.read();
    *z = Wire.read() << 8;
    *z += Wire.read();
  }
}

// ----- Hardware: LED strip -----
static void set_hole_color(uint8_t hole, uint8_t r, uint8_t g, uint8_t b) {
  if (hole >= NUMBER_OF_HOLES) {
    return;
  }
  for (int i = hole * LEDS_PER_HOLE; i < (hole + 1) * LEDS_PER_HOLE; i++) {
    pixels.setPixelColor(i, pixels.Color(r, g, b));
  }
}

// ----- Command handlers (PC -> Client) -----
static void handle_cmd_led_show(uint32_t seq, const uint8_t *payload, uint16_t len, bool ack_req) {
  if (len != 0) {
    if (ack_req) send_nack(seq, ERR_BAD_PAYLOAD);
    return;
  }
  pixels.show();
  if (ack_req) send_ack(seq, NULL, 0);
}

static void handle_cmd_led_set_n(uint32_t seq, const uint8_t *payload, uint16_t len, bool ack_req) {
  if (len < 1) {
    if (ack_req) send_nack(seq, ERR_BAD_PAYLOAD);
    return;
  }
  
  uint8_t count = payload[0];
  if (count == 0) {
    if (ack_req) send_nack(seq, ERR_BAD_PAYLOAD);
    return;
  }
  
  // Auto-detect format by payload length
  uint16_t format_a_len = 1 + count + 3;  // count + holes[] + r + g + b
  uint16_t format_b_len = 1 + count * 4;  // count + [hole,r,g,b]×count
  
  if (len == format_a_len) {
    // Format A: shared color for all holes
    uint8_t r = payload[1 + count];
    uint8_t g = payload[1 + count + 1];
    uint8_t b = payload[1 + count + 2];
    
    for (uint8_t i = 0; i < count; i++) {
      uint8_t hole = payload[1 + i];
      set_hole_color(hole, r, g, b);
    }
    if (ack_req) send_ack(seq, NULL, 0);
  }
  else if (len == format_b_len) {
    // Format B: individual colors per hole
    for (uint8_t i = 0; i < count; i++) {
      uint8_t hole = payload[1 + i * 4];
      uint8_t r = payload[1 + i * 4 + 1];
      uint8_t g = payload[1 + i * 4 + 2];
      uint8_t b = payload[1 + i * 4 + 3];
      set_hole_color(hole, r, g, b);
    }
    if (ack_req) send_ack(seq, NULL, 0);
  }
  else {
    // Invalid length for both formats
    if (ack_req) send_nack(seq, ERR_BAD_PAYLOAD);
  }
}

static void handle_cmd_hole_start(uint32_t seq, const uint8_t *payload, uint16_t len, bool ack_req) {
  if (len != 2) {
    if (ack_req) send_nack(seq, ERR_BAD_PAYLOAD);
    return;
  }
  uint8_t hole = payload[0];
  uint8_t mode = payload[1];
  if (hole >= NUMBER_OF_HOLES) {
    if (ack_req) send_nack(seq, ERR_BAD_PAYLOAD);
    return;
  }
  active_hole = hole;
  hole_meas_mode = mode;
  select_hole(hole);
  hole_meas_enabled = true;
  hole_start_time_us = micros();
  was_plugged = false;
  if (ack_req) send_ack(seq, NULL, 0);
}

static void handle_cmd_hole_stop(uint32_t seq, const uint8_t *payload, uint16_t len, bool ack_req) {
  if (len != 0) {
    if (ack_req) send_nack(seq, ERR_BAD_PAYLOAD);
    return;
  }
  hole_meas_enabled = false;
  deselect_all_holes();
  if (ack_req) send_ack(seq, NULL, 0);
}

static void handle_cmd_reed_start(uint32_t seq, const uint8_t *payload, uint16_t len, bool ack_req) {
  if (len != 4) {
    if (ack_req) send_nack(seq, ERR_BAD_PAYLOAD);
    return;
  }
  uint32_t period_us;
  memcpy(&period_us, payload, sizeof(uint32_t));
  if (period_us == 0) {
    if (ack_req) send_nack(seq, ERR_BAD_PAYLOAD);
    return;
  }
  reed_sample_period_us = period_us;
  reed_stream_enabled = true;
  next_reed_sample_us = micros();
  last_reed_value = read_reed();
  if (ack_req) send_ack(seq, NULL, 0);
}

static void handle_cmd_reed_stop(uint32_t seq, const uint8_t *payload, uint16_t len, bool ack_req) {
  if (len != 0) {
    if (ack_req) send_nack(seq, ERR_BAD_PAYLOAD);
    return;
  }
  reed_stream_enabled = false;
  if (ack_req) send_ack(seq, NULL, 0);
}

// -----Router: dispatch incoming command -----
static void dispatch_command(const MessageHeader *hdr, const uint8_t *payload) {
  bool ack_req = (hdr->flags & FLAG_ACK_REQUIRED) != 0;

  // Duplicate protection: if same seq, resend previous result
  if (hdr->seq == last_cmd_seq && last_cmd_seq != 0) {
    if (last_cmd_result == MSG_NACK && ack_req) {
      send_nack(hdr->seq, last_cmd_error);
    } else if (last_cmd_result == MSG_ACK && ack_req) {
      send_ack(hdr->seq, NULL, 0);
    }
    return;
  }

  // Process new command
  last_cmd_seq = hdr->seq;
  last_cmd_result = MSG_ACK;
  last_cmd_error = 0;

  switch (hdr->msg_type) {
    case CMD_LED_SET_N:
      handle_cmd_led_set_n(hdr->seq, payload, hdr->payload_len, ack_req);
      break;
    case CMD_LED_SHOW:
      handle_cmd_led_show(hdr->seq, payload, hdr->payload_len, ack_req);
      break;
    case CMD_HOLE_START:
      handle_cmd_hole_start(hdr->seq, payload, hdr->payload_len, ack_req);
      break;
    case CMD_HOLE_STOP:
      handle_cmd_hole_stop(hdr->seq, payload, hdr->payload_len, ack_req);
      break;
    case CMD_REED_START:
      handle_cmd_reed_start(hdr->seq, payload, hdr->payload_len, ack_req);
      break;
    case CMD_REED_STOP:
      handle_cmd_reed_stop(hdr->seq, payload, hdr->payload_len, ack_req);
      break;
    default:
      last_cmd_result = MSG_NACK;
      last_cmd_error = ERR_BAD_MSG;
      if (ack_req) send_nack(hdr->seq, ERR_BAD_MSG);
      break;
  }
}

// ----- Router: handle decoded frame -----
static void handle_decoded_frame(const uint8_t *frame, size_t len) {
  if (len < sizeof(MessageHeader)) {
    return;
  }
  MessageHeader hdr;
  memcpy(&hdr, frame, sizeof(MessageHeader));

  size_t expected_len = sizeof(MessageHeader) + hdr.payload_len;
  if (expected_len != len) {
    if (hdr.src == ADDR_PC && hdr.dst == ADDR_CLIENT && (hdr.flags & FLAG_ACK_REQUIRED)) {
      send_nack(hdr.seq, ERR_BAD_LEN);
    }
    return;
  }

  const uint8_t *payload = frame + sizeof(MessageHeader);

  // Verify checksum (for PC commands)
  if (hdr.dst == ADDR_CLIENT && hdr.src == ADDR_PC) {
    uint8_t expected_checksum = calculate_checksum(frame, sizeof(MessageHeader), payload, hdr.payload_len);
    if (hdr.checksum != expected_checksum) {
      if (hdr.flags & FLAG_ACK_REQUIRED) {
        send_nack(hdr.seq, ERR_BAD_MSG);
      }
      return;
    }
  }

  if (hdr.dst == ADDR_CLIENT) {
    dispatch_command(&hdr, payload);
  }
}

// ----- ESP-NOW RX callback (ISR context: queue only) -----
static void IRAM_ATTR on_espnow_recv(const esp_now_recv_info_t *recv_info, const uint8_t *data, int len) {
  (void)recv_info;
  if (len <= 0 || len > (int)MAX_MSG_SIZE) {
    return;
  }

  portENTER_CRITICAL_ISR(&espnow_queue_mutex);
  uint8_t next_head = (espnow_queue_head + 1) % ESPNOW_QUEUE_SIZE;
  if (next_head != espnow_queue_tail) {
    espnow_queue[espnow_queue_head].len = (uint8_t)len;
    memcpy(espnow_queue[espnow_queue_head].data, data, len);
    espnow_queue_head = next_head;
  }
  portEXIT_CRITICAL_ISR(&espnow_queue_mutex);
}

// ----- Process queued ESP-NOW packets -----
static void handle_espnow_queue(void) {
  while (true) {
    portENTER_CRITICAL(&espnow_queue_mutex);
    if (espnow_queue_tail == espnow_queue_head) {
      portEXIT_CRITICAL(&espnow_queue_mutex);
      break;
    }
    EspNowPacket packet = espnow_queue[espnow_queue_tail];
    espnow_queue_tail = (espnow_queue_tail + 1) % ESPNOW_QUEUE_SIZE;
    portEXIT_CRITICAL(&espnow_queue_mutex);

    handle_decoded_frame(packet.data, packet.len);
  }
}

// ----- Measurement tasks (non-blocking) -----
static void send_reed_data(uint32_t reed_bits) {
  uint8_t payload[8];
  uint32_t now_us = micros();
  memcpy(payload, &now_us, sizeof(uint32_t));
  memcpy(payload + 4, &reed_bits, sizeof(uint32_t));

  uint32_t seq = client_sequence_counter++;
  send_message_to_pc(DATA_REED, seq, payload, sizeof(payload));
}

static void handle_reed_stream(void) {
  if (!reed_stream_enabled) {
    return;
  }
  uint32_t now_us = micros();
  if ((int32_t)(now_us - next_reed_sample_us) < 0) {
    return;
  }
  next_reed_sample_us = now_us + reed_sample_period_us;

  uint32_t reed_val = read_reed();
  if (reed_val != last_reed_value) {
    send_reed_data(reed_val);
    last_reed_value = reed_val;
  }
}

static void send_hall_data(uint8_t hole, uint8_t plugged, uint32_t reaction_us, int16_t x, int16_t y, int16_t z) {
  uint8_t payload[13];
  payload[0] = hole;
  payload[1] = plugged;
  memcpy(payload + 2, &reaction_us, sizeof(uint32_t));
  memcpy(payload + 6, &x, sizeof(int16_t));
  memcpy(payload + 8, &y, sizeof(int16_t));
  memcpy(payload + 10, &z, sizeof(int16_t));

  uint32_t seq = client_sequence_counter++;
  send_message_to_pc(DATA_HALL, seq, payload, sizeof(payload));
}

static void handle_hole_measurement(void) {
  if (!hole_meas_enabled) {
    return;
  }

  uint32_t reed_val = read_reed();
  bool plugged = (reed_val & (1 << active_hole)) != 0;
  uint32_t reaction_us = micros() - hole_start_time_us;

  // Mode 0: simple plug detection
  if (hole_meas_mode == 0) {
    if (plugged != was_plugged) {
      send_hall_data(active_hole, plugged ? 1 : 0, reaction_us, 0, 0, 0);
      was_plugged = plugged;
    }
  }
  // Mode 1: read hall sensors when plugged
  else if (hole_meas_mode == 1) {
    if (plugged) {
      select_sensor(SENSOR_B);
      delayMicroseconds(500);
      start_single_measurement();
      delay(3);
      int16_t x, y, z;
      read_measurement(&x, &y, &z);
      deselect_sensor();
      send_hall_data(active_hole, 1, reaction_us, x, y, z);
      was_plugged = true;
    } else {
      if (was_plugged) {
        send_hall_data(active_hole, 0, reaction_us, 0, 0, 0);
        was_plugged = false;
      }
    }
  }
}

// ================================================
// SETUP
// ================================================
void setup() {
  Serial.begin(115200);

  // I2C
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(40000);

  // Reed switches
  setup_reed();

  // Group pins for hole selection
  pinMode(GROUP_A, OUTPUT);
  pinMode(GROUP_B, OUTPUT);
  pinMode(GROUP_C, OUTPUT);
  pinMode(GROUP_D, OUTPUT);
  pinMode(GROUP_E, OUTPUT);
  pinMode(GROUP_F, OUTPUT);
  deselect_all_holes();

  // LED strip
  pixels.begin();
  pixels.clear();
  pixels.show();

  // ESP-NOW
  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }
  esp_now_register_recv_cb(on_espnow_recv);

  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(peerInfo));
  memcpy(peerInfo.peer_addr, kServerMacAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);

  Serial.println("Client ready");
  Serial.print("MAC: ");
  Serial.println(WiFi.macAddress());
}

// ================================================
// LOOP (minimal scheduler)
// ================================================
void loop() {
  // Process incoming commands
  handle_espnow_queue();

  // Run measurement tasks if enabled
  handle_reed_stream();
  handle_hole_measurement();
}
