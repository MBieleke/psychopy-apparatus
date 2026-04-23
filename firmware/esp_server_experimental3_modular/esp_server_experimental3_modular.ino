// ================================================
// Experimental server ESP32 firmware: measurement, forwarding, actions.
// Adds persistent server/client pairing and a selectable force backend.
// Default experimental backend uses ADS1115 acquisition and extends
// DATA_FORCE with embedded raw ADC counts while preserving force semantics.
// ================================================

#include <Arduino.h>
#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <string.h>

#include "apparatus_config.h"
#include "apparatus_protocol.h"
#include "force_service.h"
#include "motor_control.h"
#include "pairing_radio.h"
#include "protocol_io.h"
#include "protocol_utils.h"

static void forward_frame_to_pc(const uint8_t *data, size_t len) {
  protocol_io_send_frame(data, len);
}

static void handle_command(const MessageHeader *hdr, const uint8_t *payload) {
  bool ack_required = (hdr->flags & FLAG_ACK_REQUIRED) != 0;

  switch (hdr->msg_type) {
    case CMD_MOTOR: {
      if (hdr->payload_len != 4) { if (ack_required) protocol_io_send_nack(hdr->seq, ERR_BAD_PAYLOAD); return; }
      uint8_t action = payload[0];
      uint8_t dir = payload[1];
      uint16_t speed_us = 0;
      memcpy(&speed_us, payload + 2, sizeof(uint16_t));
      if (action == 0) motor_control_queue_stop();
      else motor_control_queue_start(dir, speed_us);
      if (ack_required) protocol_io_send_ack(hdr->seq, NULL, 0);
      break;
    }
    case CMD_LIGHT: {
      if (hdr->payload_len != 0) { if (ack_required) protocol_io_send_nack(hdr->seq, ERR_BAD_PAYLOAD); return; }
      uint8_t light_state = (uint8_t)digitalRead(LIGHT_SENSOR_PIN);
      if (ack_required) protocol_io_send_ack(hdr->seq, &light_state, 1);
      break;
    }
    case CMD_FORCE_START: {
      if (hdr->payload_len != 5) { if (ack_required) protocol_io_send_nack(hdr->seq, ERR_BAD_PAYLOAD); return; }
      uint32_t period = 0;
      memcpy(&period, payload, sizeof(uint32_t));
      uint8_t device = payload[4];
      if (!force_service_validate_start(period, device)) { if (ack_required) protocol_io_send_nack(hdr->seq, ERR_BAD_PAYLOAD); return; }

      force_service_queue_start(period, device);

      if (ack_required) {
        uint8_t ack_payload[5];
        memcpy(ack_payload, &period, sizeof(uint32_t));
        ack_payload[4] = device;
        protocol_io_send_ack(hdr->seq, ack_payload, sizeof(ack_payload));
      }
      break;
    }
    case CMD_FORCE_STOP: {
      if (hdr->payload_len != 0) { if (ack_required) protocol_io_send_nack(hdr->seq, ERR_BAD_PAYLOAD); return; }
      force_service_stop();
      if (ack_required) protocol_io_send_ack(hdr->seq, NULL, 0);
      break;
    }
    case CMD_MAGNET: {
      if (hdr->payload_len != 2) { if (ack_required) protocol_io_send_nack(hdr->seq, ERR_BAD_PAYLOAD); return; }
      uint8_t channel = payload[0];
      uint8_t state = payload[1];
      if (channel > 2) { if (ack_required) protocol_io_send_nack(hdr->seq, ERR_BAD_PAYLOAD); return; }
      if (channel == 0 || channel == 2) digitalWrite(MAGNET_RIGHT_PIN, state ? HIGH : LOW);
      if (channel == 1 || channel == 2) digitalWrite(MAGNET_LEFT_PIN, state ? HIGH : LOW);
      if (ack_required) {
        uint8_t ack_payload[2] = {channel, state};
        protocol_io_send_ack(hdr->seq, ack_payload, sizeof(ack_payload));
      }
      break;
    }
    default:
      if (ack_required) protocol_io_send_nack(hdr->seq, ERR_BAD_MSG);
      break;
  }
}

static void handle_decoded_frame(const uint8_t *frame, size_t len) {
  if (len < sizeof(MessageHeader)) return;

  MessageHeader hdr;
  memcpy(&hdr, frame, sizeof(MessageHeader));

  size_t expected_len = sizeof(MessageHeader) + hdr.payload_len;
  if (expected_len != len) {
    if (hdr.src == ADDR_PC && hdr.dst == ADDR_SERVER && (hdr.flags & FLAG_ACK_REQUIRED)) protocol_io_send_nack(hdr.seq, ERR_BAD_LEN);
    return;
  }

  const uint8_t *payload = frame + sizeof(MessageHeader);

  if (hdr.dst == ADDR_SERVER && hdr.src == ADDR_PC) {
    uint8_t expected_checksum = calculate_checksum(frame, sizeof(MessageHeader), payload, hdr.payload_len);
    if (hdr.checksum != expected_checksum) {
      if (hdr.flags & FLAG_ACK_REQUIRED) protocol_io_send_nack(hdr.seq, ERR_BAD_MSG);
      return;
    }
  }

  if (hdr.dst == ADDR_CLIENT) {
    if (len > ESPNOW_MAX_SIZE) {
      if (hdr.src == ADDR_PC && (hdr.flags & FLAG_ACK_REQUIRED)) protocol_io_send_nack(hdr.seq, ERR_BAD_LEN);
      return;
    }
    if (!pairing_radio_send_to_client(frame, len)) {
      if (hdr.src == ADDR_PC && (hdr.flags & FLAG_ACK_REQUIRED)) protocol_io_send_nack(hdr.seq, ERR_BAD_MSG);
      return;
    }
    return;
  }

  if (hdr.dst == ADDR_SERVER) handle_command(&hdr, payload);
}

void setup() {
  Serial.begin(APPARATUS_SERIAL_BAUD);

  WiFi.mode(WIFI_STA);
  PC_LOG_PRINTLN("ROLE: SERVER");
  PC_LOG_PRINT("MAC: ");
  PC_LOG_PRINTLN(WiFi.macAddress());

  esp_wifi_set_promiscuous(true);
  esp_wifi_set_channel(ESPNOW_FIXED_CHANNEL, WIFI_SECOND_CHAN_NONE);
  esp_wifi_set_promiscuous(false);

  if (esp_now_init() != ESP_OK) return;
  esp_now_register_recv_cb(pairing_radio_on_recv);

  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(peerInfo));
  memcpy(peerInfo.peer_addr, kPairingBroadcastMacAddress, 6);
  peerInfo.channel = ESPNOW_FIXED_CHANNEL;
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);

  pairing_radio_init(millis());
  motor_control_init();

  pinMode(LIGHT_SENSOR_PIN, INPUT);
  pinMode(MAGNET_RIGHT_PIN, OUTPUT);
  pinMode(MAGNET_LEFT_PIN, OUTPUT);

  force_service_init();
}

void loop() {
  protocol_io_poll_tx();

  protocol_io_poll_rx(handle_decoded_frame);
  pairing_radio_poll_rx_queue(forward_frame_to_pc);
  pairing_radio_poll_tasks();
  protocol_io_poll_tx();
  force_service_poll_start_pending();
  force_service_poll_events();

  force_service_poll_stream(protocol_io_send_force_data);
  protocol_io_poll_tx();

  pairing_radio_poll_rx_queue(forward_frame_to_pc);
  motor_control_poll();
}
