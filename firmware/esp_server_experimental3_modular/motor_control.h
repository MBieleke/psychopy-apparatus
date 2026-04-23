#pragma once

#include <stdint.h>

void motor_control_init(void);
void motor_control_queue_start(uint8_t dir, uint16_t speed_us);
void motor_control_queue_stop(void);
void motor_control_poll(void);
