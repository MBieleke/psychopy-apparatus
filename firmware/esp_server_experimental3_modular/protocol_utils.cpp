#include "protocol_utils.h"

uint8_t calculate_checksum(const uint8_t *header_ptr, size_t header_len, const uint8_t *payload, size_t payload_len) {
  uint8_t checksum = 0;
  for (size_t i = 0; i < header_len && i < 10; i++) checksum ^= header_ptr[i];
  for (size_t i = 0; i < payload_len; i++) checksum ^= payload[i];
  return checksum;
}

size_t cobs_encode(const uint8_t *input, size_t length, uint8_t *output) {
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

size_t cobs_decode(const uint8_t *input, size_t length, uint8_t *output, size_t max_output) {
  size_t read_index = 0;
  size_t write_index = 0;

  while (read_index < length) {
    uint8_t code = input[read_index++];
    if (code == 0 || (read_index + code - 1) > length) return 0;
    for (uint8_t i = 1; i < code; i++) {
      if (write_index >= max_output) return 0;
      output[write_index++] = input[read_index++];
    }
    if (code != 0xFF && read_index < length) {
      if (write_index >= max_output) return 0;
      output[write_index++] = 0;
    }
  }

  return write_index;
}
