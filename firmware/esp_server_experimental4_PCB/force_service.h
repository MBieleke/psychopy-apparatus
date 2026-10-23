#pragma once

#include <stddef.h>
#include <stdint.h>

typedef void (*ForceDataSender)(uint8_t device, int16_t value, int16_t raw_counts);

void force_service_init(void);
bool force_service_validate_start(uint32_t period_us, uint8_t device);
void force_service_queue_start(uint32_t period_us, uint8_t device);
void force_service_stop(void);
void force_service_poll_start_pending(void);
void force_service_poll_events(void);
void force_service_poll_stream(ForceDataSender send_force_data);
bool force_service_get_latest_mv(uint8_t device, int32_t *mv_out);
