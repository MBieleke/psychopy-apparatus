#include "pairing_radio.h"

#include <Arduino.h>
#include <Preferences.h>
#include <string.h>

#include "apparatus_config.h"
#include "apparatus_protocol.h"

const uint8_t kPairingBroadcastMacAddress[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

struct EspNowPacket {
  uint8_t data[ESPNOW_MAX_SIZE];
  uint8_t len;
  uint8_t src_mac[6];
};

static const uint8_t ESPNOW_QUEUE_SIZE = 32;

static Preferences pairing_preferences;
static bool client_peer_known = false;
static uint8_t client_peer_mac[6] = {0};
static uint64_t device_uid = 0;
static uint64_t paired_client_uid = 0;
static uint64_t pending_client_uid = 0;
static uint8_t pending_client_mac[6] = {0};
static uint32_t pending_nonce_a = 0;
static uint32_t pending_nonce_b = 0;
static uint32_t last_pair_confirm_nonce_b = 0;
static uint32_t pending_handshake_deadline_ms = 0;
static bool pairing_handshake_active = false;
static uint32_t next_pairing_broadcast_ms = 0;
static const uint32_t PAIRING_HELLO_UNPAIRED_INTERVAL_MS = 500;
static const uint32_t PAIRING_HELLO_PAIRED_INTERVAL_MS = 2000;
static const uint32_t PAIRING_HANDSHAKE_TIMEOUT_MS = 3000;

static volatile uint8_t espnow_queue_head = 0;
static volatile uint8_t espnow_queue_tail = 0;
static EspNowPacket espnow_queue[ESPNOW_QUEUE_SIZE];
static portMUX_TYPE espnow_queue_mutex = portMUX_INITIALIZER_UNLOCKED;

static bool mac_is_broadcast(const uint8_t *mac) {
  for (int i = 0; i < 6; i++) if (mac[i] != 0xFF) return false;
  return true;
}

static bool mac_equals(const uint8_t *a, const uint8_t *b) {
  if (a == NULL || b == NULL) return false;
  return memcmp(a, b, 6) == 0;
}

static void clear_client_peer_runtime(void) {
  client_peer_known = false;
  memset(client_peer_mac, 0, sizeof(client_peer_mac));
}

static bool register_espnow_peer(const uint8_t *mac) {
  if (mac == NULL || mac_is_broadcast(mac)) return false;
  if (esp_now_is_peer_exist(mac)) return true;

  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(peerInfo));
  memcpy(peerInfo.peer_addr, mac, 6);
  peerInfo.channel = ESPNOW_FIXED_CHANNEL;
  peerInfo.encrypt = false;
  esp_err_t add_result = esp_now_add_peer(&peerInfo);
  return (add_result == ESP_OK || add_result == ESP_ERR_ESPNOW_EXIST);
}

static bool ensure_client_peer(const uint8_t *mac) {
  if (!register_espnow_peer(mac)) return false;

  memcpy(client_peer_mac, mac, 6);
  client_peer_known = true;
  return true;
}

static void clear_pending_pairing(void) {
  pairing_handshake_active = false;
  pending_client_uid = 0;
  memset(pending_client_mac, 0, sizeof(pending_client_mac));
  pending_nonce_a = 0;
  pending_nonce_b = 0;
  pending_handshake_deadline_ms = 0;
}

static bool prefs_load_u64(const char *key, uint64_t *value) {
  if (!value) return false;
  if (pairing_preferences.getBytesLength(key) != sizeof(uint64_t)) return false;
  return pairing_preferences.getBytes(key, value, sizeof(uint64_t)) == sizeof(uint64_t);
}

static bool prefs_load_mac(const char *key, uint8_t *mac_out) {
  if (!mac_out) return false;
  if (pairing_preferences.getBytesLength(key) != 6) return false;
  return pairing_preferences.getBytes(key, mac_out, 6) == 6;
}

static uint64_t generate_device_uid(void) {
  uint64_t uid = 0;
  while (uid == 0) {
    uid = ((uint64_t)esp_random() << 32) | (uint64_t)esp_random();
  }
  return uid;
}

bool pairing_radio_is_paired(void) {
  return (paired_client_uid != 0 && client_peer_known);
}

static bool pairing_send_packet(const uint8_t *target_mac, const uint8_t *data, size_t len) {
  if (target_mac == NULL || len == 0 || len > ESPNOW_MAX_SIZE) return false;
  if (!mac_is_broadcast(target_mac) && !register_espnow_peer(target_mac)) return false;
  return esp_now_send(target_mac, data, len) == ESP_OK;
}

static void fill_control_prefix(uint8_t *magic, uint8_t *version, uint8_t *packet_type, uint8_t type) {
  magic[0] = CONTROL_MAGIC_0;
  magic[1] = CONTROL_MAGIC_1;
  magic[2] = CONTROL_MAGIC_2;
  magic[3] = CONTROL_MAGIC_3;
  *version = CONTROL_VERSION;
  *packet_type = type;
}

static void send_pair_hello(void) {
  PairHelloPacket pkt;
  fill_control_prefix(pkt.magic, &pkt.version, &pkt.packet_type, CTRL_HELLO);
  pkt.role = DISCOVERY_ROLE_SERVER;
  pkt.pair_state = pairing_radio_is_paired() ? PAIR_STATE_PAIRED : PAIR_STATE_UNPAIRED;
  pkt.uid = device_uid;
  pairing_send_packet(kPairingBroadcastMacAddress, (const uint8_t *)&pkt, sizeof(pkt));
}

static bool send_pair_offer(const uint8_t *target_mac, uint64_t target_uid, uint32_t nonce_a) {
  PairOfferPacket pkt;
  fill_control_prefix(pkt.magic, &pkt.version, &pkt.packet_type, CTRL_PAIR_OFFER);
  pkt.from_role = DISCOVERY_ROLE_SERVER;
  pkt.from_uid = device_uid;
  pkt.to_uid = target_uid;
  pkt.nonce_a = nonce_a;
  return pairing_send_packet(target_mac, (const uint8_t *)&pkt, sizeof(pkt));
}

static bool send_pair_confirm(const uint8_t *target_mac, uint64_t target_uid, uint32_t nonce_b) {
  PairConfirmPacket pkt;
  fill_control_prefix(pkt.magic, &pkt.version, &pkt.packet_type, CTRL_PAIR_CONFIRM);
  pkt.from_role = DISCOVERY_ROLE_SERVER;
  pkt.from_uid = device_uid;
  pkt.to_uid = target_uid;
  pkt.nonce_b = nonce_b;
  return pairing_send_packet(target_mac, (const uint8_t *)&pkt, sizeof(pkt));
}

static void pairing_commit_client(const uint8_t *mac, uint64_t uid) {
  if (!ensure_client_peer(mac)) return;
  paired_client_uid = uid;
  pairing_preferences.putBytes("peer_uid", &paired_client_uid, sizeof(paired_client_uid));
  pairing_preferences.putBytes("peer_mac", client_peer_mac, sizeof(client_peer_mac));
  pairing_preferences.putUChar("pair_state", PAIR_STATE_PAIRED);
  last_pair_confirm_nonce_b = pending_nonce_b;
  clear_pending_pairing();
  PC_LOG_PRINTF("Paired client uid=%08lX%08lX mac=%02X:%02X:%02X:%02X:%02X:%02X\n",
                (unsigned long)(paired_client_uid >> 32), (unsigned long)(paired_client_uid & 0xFFFFFFFFULL),
                client_peer_mac[0], client_peer_mac[1], client_peer_mac[2],
                client_peer_mac[3], client_peer_mac[4], client_peer_mac[5]);
}

static void pairing_refresh_client_mac(const uint8_t *mac) {
  if (mac == NULL || paired_client_uid == 0) return;
  if (mac_equals(client_peer_mac, mac)) return;
  if (!ensure_client_peer(mac)) return;
  pairing_preferences.putBytes("peer_mac", client_peer_mac, sizeof(client_peer_mac));
  PC_LOG_PRINTF("Updated paired client MAC to %02X:%02X:%02X:%02X:%02X:%02X\n",
                client_peer_mac[0], client_peer_mac[1], client_peer_mac[2],
                client_peer_mac[3], client_peer_mac[4], client_peer_mac[5]);
}

static bool is_control_packet(const uint8_t *data, size_t len) {
  if (data == NULL || len < 6) return false;
  return data[0] == CONTROL_MAGIC_0 &&
         data[1] == CONTROL_MAGIC_1 &&
         data[2] == CONTROL_MAGIC_2 &&
         data[3] == CONTROL_MAGIC_3 &&
         data[4] == CONTROL_VERSION;
}

static bool process_pairing_packet(const uint8_t *data, size_t len, const uint8_t *src_mac) {
  if (!is_control_packet(data, len) || src_mac == NULL) return false;

  uint8_t packet_type = data[5];
  switch (packet_type) {
    case CTRL_HELLO: {
      if (len != sizeof(PairHelloPacket)) return true;
      const PairHelloPacket *pkt = (const PairHelloPacket *)data;
      if (pkt->role != DISCOVERY_ROLE_CLIENT || pkt->uid == 0 || pkt->uid == device_uid) return true;

      if (pairing_radio_is_paired()) {
        if (pkt->uid == paired_client_uid) {
          pairing_refresh_client_mac(src_mac);
          if (pkt->pair_state == PAIR_STATE_UNPAIRED && last_pair_confirm_nonce_b != 0) {
            send_pair_confirm(src_mac, paired_client_uid, last_pair_confirm_nonce_b);
          }
        }
        return true;
      }

      if (pkt->pair_state != PAIR_STATE_UNPAIRED) return true;
      if (pairing_handshake_active) {
        if (pkt->uid == pending_client_uid && mac_equals(src_mac, pending_client_mac)) {
          send_pair_offer(src_mac, pending_client_uid, pending_nonce_a);
        }
        return true;
      }

      if (!register_espnow_peer(src_mac)) return true;
      pending_client_uid = pkt->uid;
      memcpy(pending_client_mac, src_mac, sizeof(pending_client_mac));
      pending_nonce_a = esp_random();
      pending_nonce_b = 0;
      pending_handshake_deadline_ms = millis() + PAIRING_HANDSHAKE_TIMEOUT_MS;
      pairing_handshake_active = true;
      send_pair_offer(src_mac, pending_client_uid, pending_nonce_a);
      return true;
    }
    case CTRL_PAIR_ACCEPT: {
      if (len != sizeof(PairAcceptPacket)) return true;
      const PairAcceptPacket *pkt = (const PairAcceptPacket *)data;
      if (pkt->from_role != DISCOVERY_ROLE_CLIENT) return true;
      if (!pairing_handshake_active) return true;
      if (pkt->to_uid != device_uid || pkt->from_uid != pending_client_uid) return true;
      if (pkt->nonce_a != pending_nonce_a || !mac_equals(src_mac, pending_client_mac)) return true;

      pending_nonce_b = pkt->nonce_b;
      if (send_pair_confirm(src_mac, pending_client_uid, pending_nonce_b)) {
        pairing_commit_client(src_mac, pending_client_uid);
      }
      return true;
    }
    case CTRL_PAIR_OFFER:
    case CTRL_PAIR_CONFIRM:
      return true;
    default:
      return false;
  }
}

void pairing_radio_init(uint32_t now_ms) {
  pairing_preferences.begin("pairing", false);

  if (!prefs_load_u64("device_uid", &device_uid) || device_uid == 0) {
    device_uid = generate_device_uid();
    pairing_preferences.putBytes("device_uid", &device_uid, sizeof(device_uid));
  }

  clear_client_peer_runtime();
  paired_client_uid = 0;
  clear_pending_pairing();

  uint8_t stored_pair_state = pairing_preferences.getUChar("pair_state", PAIR_STATE_UNPAIRED);
  uint8_t stored_mac[6] = {0};
  uint64_t stored_uid = 0;
  if (stored_pair_state == PAIR_STATE_PAIRED &&
      prefs_load_u64("peer_uid", &stored_uid) &&
      prefs_load_mac("peer_mac", stored_mac) &&
      stored_uid != 0 &&
      !mac_is_broadcast(stored_mac)) {
    paired_client_uid = stored_uid;
    ensure_client_peer(stored_mac);
  } else {
    pairing_preferences.putUChar("pair_state", PAIR_STATE_UNPAIRED);
  }

  next_pairing_broadcast_ms = now_ms;

  PC_LOG_PRINTF("Device UID=%08lX%08lX\n",
                (unsigned long)(device_uid >> 32), (unsigned long)(device_uid & 0xFFFFFFFFULL));
  if (pairing_radio_is_paired()) {
    PC_LOG_PRINTLN("Pair state: paired");
  } else {
    PC_LOG_PRINTLN("Pair state: unpaired");
  }
}

void pairing_radio_poll_tasks(void) {
  uint32_t now_ms = millis();
  if (pairing_handshake_active && (int32_t)(now_ms - pending_handshake_deadline_ms) >= 0) {
    clear_pending_pairing();
  }

  uint32_t interval_ms = pairing_radio_is_paired() ? PAIRING_HELLO_PAIRED_INTERVAL_MS : PAIRING_HELLO_UNPAIRED_INTERVAL_MS;
  if ((int32_t)(now_ms - next_pairing_broadcast_ms) >= 0) {
    next_pairing_broadcast_ms = now_ms + interval_ms;
    send_pair_hello();
  }
}

void IRAM_ATTR pairing_radio_on_recv(const esp_now_recv_info_t *recv_info, const uint8_t *incomingData, int len) {
  const uint8_t *src_mac = recv_info ? recv_info->src_addr : NULL;
  if (len <= 0 || len > (int)ESPNOW_MAX_SIZE) return;

  portENTER_CRITICAL_ISR(&espnow_queue_mutex);
  uint8_t next_head = (uint8_t)((espnow_queue_head + 1) % ESPNOW_QUEUE_SIZE);
  if (next_head != espnow_queue_tail) {
    espnow_queue[espnow_queue_head].len = (uint8_t)len;
    memcpy(espnow_queue[espnow_queue_head].data, incomingData, len);
    if (src_mac) memcpy(espnow_queue[espnow_queue_head].src_mac, src_mac, 6);
    else memset(espnow_queue[espnow_queue_head].src_mac, 0, 6);
    espnow_queue_head = next_head;
  }
  portEXIT_CRITICAL_ISR(&espnow_queue_mutex);
}

void pairing_radio_poll_rx_queue(PairingForwardFrameHandler forward_frame) {
  while (true) {
    portENTER_CRITICAL(&espnow_queue_mutex);
    if (espnow_queue_tail == espnow_queue_head) {
      portEXIT_CRITICAL(&espnow_queue_mutex);
      break;
    }
    EspNowPacket packet = espnow_queue[espnow_queue_tail];
    espnow_queue_tail = (uint8_t)((espnow_queue_tail + 1) % ESPNOW_QUEUE_SIZE);
    portEXIT_CRITICAL(&espnow_queue_mutex);

    if (process_pairing_packet(packet.data, packet.len, packet.src_mac)) continue;
    if (!pairing_radio_is_paired() || !mac_equals(packet.src_mac, client_peer_mac)) continue;
    if (forward_frame) forward_frame(packet.data, packet.len);
  }
}

bool pairing_radio_send_to_client(const uint8_t *frame, size_t len) {
  if (!frame || len == 0 || len > ESPNOW_MAX_SIZE) return false;
  if (!client_peer_known) return false;
  return esp_now_send(client_peer_mac, frame, len) == ESP_OK;
}
