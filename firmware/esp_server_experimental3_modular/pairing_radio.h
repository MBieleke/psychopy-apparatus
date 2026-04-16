#pragma once

#include <stddef.h>
#include <stdint.h>

#include <esp_now.h>

typedef void (*PairingForwardFrameHandler)(const uint8_t *data, size_t len);

extern const uint8_t kPairingBroadcastMacAddress[6];

void pairing_radio_init(uint32_t now_ms);
void pairing_radio_poll_tasks(void);
void pairing_radio_poll_rx_queue(PairingForwardFrameHandler forward_frame);
bool pairing_radio_send_to_client(const uint8_t *frame, size_t len);
bool pairing_radio_is_paired(void);
void pairing_radio_on_recv(const esp_now_recv_info_t *recv_info, const uint8_t *incomingData, int len);
