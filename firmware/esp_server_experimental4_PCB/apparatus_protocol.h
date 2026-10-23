#pragma once

#include <stddef.h>
#include <stdint.h>

static const size_t MAX_MSG_SIZE = 256;
static const size_t MAX_COBS_SIZE = 300;
static const size_t ESPNOW_MAX_SIZE = 250;
static const uint8_t ESPNOW_FIXED_CHANNEL = 1;

#define CONTROL_VERSION 1
#define CONTROL_MAGIC_0 0x41
#define CONTROL_MAGIC_1 0x50
#define CONTROL_MAGIC_2 0x50
#define CONTROL_MAGIC_3 0x31

enum { ADDR_PC = 1, ADDR_SERVER = 2, ADDR_CLIENT = 3 };
enum { FLAG_ACK_REQUIRED = 0x01 };

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

enum { ERR_BAD_LEN = 1, ERR_BAD_MSG = 2, ERR_BAD_PAYLOAD = 3 };

struct __attribute__((packed)) MessageHeader {
  uint8_t  msg_type;
  uint32_t seq;
  uint16_t payload_len;
  uint8_t  src;
  uint8_t  dst;
  uint8_t  flags;
  uint8_t  checksum;
};

enum { DISCOVERY_ROLE_SERVER = 1, DISCOVERY_ROLE_CLIENT = 2 };
enum { PAIR_STATE_UNPAIRED = 0, PAIR_STATE_PAIRED = 1 };
enum {
  CTRL_HELLO = 1,
  CTRL_PAIR_OFFER = 2,
  CTRL_PAIR_ACCEPT = 3,
  CTRL_PAIR_CONFIRM = 4
};

struct __attribute__((packed)) PairHelloPacket {
  uint8_t magic[4];
  uint8_t version;
  uint8_t packet_type;
  uint8_t role;
  uint8_t pair_state;
  uint64_t uid;
};

struct __attribute__((packed)) PairOfferPacket {
  uint8_t magic[4];
  uint8_t version;
  uint8_t packet_type;
  uint8_t from_role;
  uint64_t from_uid;
  uint64_t to_uid;
  uint32_t nonce_a;
};

struct __attribute__((packed)) PairAcceptPacket {
  uint8_t magic[4];
  uint8_t version;
  uint8_t packet_type;
  uint8_t from_role;
  uint64_t from_uid;
  uint64_t to_uid;
  uint32_t nonce_a;
  uint32_t nonce_b;
};

struct __attribute__((packed)) PairConfirmPacket {
  uint8_t magic[4];
  uint8_t version;
  uint8_t packet_type;
  uint8_t from_role;
  uint64_t from_uid;
  uint64_t to_uid;
  uint32_t nonce_b;
};
