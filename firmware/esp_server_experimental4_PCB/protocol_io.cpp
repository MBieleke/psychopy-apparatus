#include "protocol_io.h"

#include <Arduino.h>
#include <string.h>

#include "apparatus_protocol.h"
#include "protocol_utils.h"

static uint8_t serial_cobs_rx_buffer[MAX_COBS_SIZE];
static size_t serial_cobs_rx_length = 0;

static uint8_t serial_decode_buffer[MAX_MSG_SIZE];
static uint8_t serial_encode_buffer[MAX_COBS_SIZE + 1];

static const size_t SERIAL_TX_QUEUE_SIZE = 4096;
static uint8_t serial_tx_queue[SERIAL_TX_QUEUE_SIZE];
static size_t serial_tx_head = 0;
static size_t serial_tx_tail = 0;
static uint32_t serial_tx_drop_frames = 0;
static uint32_t server_sequence_counter = 1;

static size_t serial_tx_queue_count(void) {
  if (serial_tx_head >= serial_tx_tail) return serial_tx_head - serial_tx_tail;
  return SERIAL_TX_QUEUE_SIZE - (serial_tx_tail - serial_tx_head);
}

static size_t serial_tx_queue_free(void) {
  return (SERIAL_TX_QUEUE_SIZE - 1) - serial_tx_queue_count();
}

static bool serial_tx_enqueue_bytes(const uint8_t *data, size_t len) {
  if (len == 0) return true;
  if (len > serial_tx_queue_free()) return false;

  size_t first_chunk = SERIAL_TX_QUEUE_SIZE - serial_tx_head;
  if (first_chunk > len) first_chunk = len;
  memcpy(&serial_tx_queue[serial_tx_head], data, first_chunk);
  serial_tx_head = (serial_tx_head + first_chunk) % SERIAL_TX_QUEUE_SIZE;

  size_t remaining = len - first_chunk;
  if (remaining > 0) {
    memcpy(&serial_tx_queue[serial_tx_head], data + first_chunk, remaining);
    serial_tx_head = (serial_tx_head + remaining) % SERIAL_TX_QUEUE_SIZE;
  }

  return true;
}

void protocol_io_poll_tx(void) {
  int available = Serial.availableForWrite();
  while (available > 0 && serial_tx_tail != serial_tx_head) {
    size_t contiguous = (serial_tx_head >= serial_tx_tail)
      ? (serial_tx_head - serial_tx_tail)
      : (SERIAL_TX_QUEUE_SIZE - serial_tx_tail);

    size_t chunk = (size_t)available;
    if (chunk > contiguous) chunk = contiguous;
    if (chunk == 0) break;

    size_t written = Serial.write(&serial_tx_queue[serial_tx_tail], chunk);
    if (written == 0) break;

    serial_tx_tail = (serial_tx_tail + written) % SERIAL_TX_QUEUE_SIZE;
    available -= (int)written;
    if (written < chunk) break;
  }
}

void protocol_io_send_frame(const uint8_t *data, size_t len) {
  if (len == 0) return;

  size_t encoded_len = cobs_encode(data, len, serial_encode_buffer);
  if (encoded_len == 0 || encoded_len >= sizeof(serial_encode_buffer)) return;
  serial_encode_buffer[encoded_len++] = 0x00;

  if (!serial_tx_enqueue_bytes(serial_encode_buffer, encoded_len)) {
    protocol_io_poll_tx();
    if (!serial_tx_enqueue_bytes(serial_encode_buffer, encoded_len)) {
      serial_tx_drop_frames++;
    }
  }
}

void protocol_io_send_message_to_pc(uint8_t msg_type, uint32_t seq, const uint8_t *payload, uint16_t payload_len) {
  MessageHeader hdr;
  hdr.msg_type = msg_type;
  hdr.seq = seq;
  hdr.payload_len = payload_len;
  hdr.src = ADDR_SERVER;
  hdr.dst = ADDR_PC;
  hdr.flags = 0;
  hdr.checksum = 0;

  uint8_t frame[MAX_MSG_SIZE];
  size_t total_len = sizeof(MessageHeader) + payload_len;
  if (total_len > sizeof(frame)) return;

  memcpy(frame, &hdr, sizeof(MessageHeader));
  if (payload_len > 0 && payload) memcpy(frame + sizeof(MessageHeader), payload, payload_len);

  uint8_t checksum = calculate_checksum(frame, sizeof(MessageHeader), payload, payload_len);
  ((MessageHeader *)frame)->checksum = checksum;

  protocol_io_send_frame(frame, total_len);
}

void protocol_io_send_ack(uint32_t seq, const uint8_t *payload, uint16_t payload_len) {
  protocol_io_send_message_to_pc(MSG_ACK, seq, payload, payload_len);
}

void protocol_io_send_nack(uint32_t seq, uint8_t error_code) {
  uint8_t payload[1] = { error_code };
  protocol_io_send_message_to_pc(MSG_NACK, seq, payload, 1);
}

void protocol_io_send_force_data(uint8_t device, int16_t value, int16_t raw_counts) {
  uint8_t payload[9];
  uint32_t now_us = micros();
  memcpy(payload, &now_us, sizeof(uint32_t));
  memcpy(payload + 4, &value, sizeof(int16_t));
  memcpy(payload + 6, &raw_counts, sizeof(int16_t));
  payload[8] = device;

  uint32_t seq = server_sequence_counter++;
  protocol_io_send_message_to_pc(DATA_FORCE, seq, payload, sizeof(payload));
}

void protocol_io_poll_rx(ProtocolFrameHandler frame_handler) {
  while (Serial.available() > 0) {
    uint8_t b = (uint8_t)Serial.read();
    if (b == 0x00) {
      if (serial_cobs_rx_length > 0) {
        size_t decoded_len = cobs_decode(serial_cobs_rx_buffer, serial_cobs_rx_length, serial_decode_buffer, sizeof(serial_decode_buffer));
        if (decoded_len > 0 && frame_handler) frame_handler(serial_decode_buffer, decoded_len);
      }
      serial_cobs_rx_length = 0;
    } else {
      if (serial_cobs_rx_length < sizeof(serial_cobs_rx_buffer)) serial_cobs_rx_buffer[serial_cobs_rx_length++] = b;
      else serial_cobs_rx_length = 0;
    }
  }
}

uint32_t protocol_io_get_drop_frames(void) {
  return serial_tx_drop_frames;
}
