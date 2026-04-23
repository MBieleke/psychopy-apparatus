#pragma once

#include <stddef.h>
#include <stdint.h>

uint8_t calculate_checksum(const uint8_t *header_ptr, size_t header_len, const uint8_t *payload, size_t payload_len);
size_t cobs_encode(const uint8_t *input, size_t length, uint8_t *output);
size_t cobs_decode(const uint8_t *input, size_t length, uint8_t *output, size_t max_output);
