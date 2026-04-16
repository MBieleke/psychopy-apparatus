#pragma once

#include <stddef.h>
#include <stdint.h>

typedef void (*ProtocolFrameHandler)(const uint8_t *frame, size_t len);

void protocol_io_poll_tx(void);
void protocol_io_poll_rx(ProtocolFrameHandler frame_handler);
void protocol_io_send_frame(const uint8_t *data, size_t len);
void protocol_io_send_message_to_pc(uint8_t msg_type, uint32_t seq, const uint8_t *payload, uint16_t payload_len);
void protocol_io_send_ack(uint32_t seq, const uint8_t *payload, uint16_t payload_len);
void protocol_io_send_nack(uint32_t seq, uint8_t error_code);
void protocol_io_send_force_data(uint8_t device, int16_t value, int16_t raw_counts);
uint32_t protocol_io_get_drop_frames(void);
