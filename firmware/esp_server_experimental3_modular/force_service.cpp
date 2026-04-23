#include "force_service.h"

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <math.h>

#include "apparatus_config.h"

static bool force_stream_enabled = false;
static uint32_t force_sample_period_us = 10000;
static uint32_t next_force_sample_us = 0;
static uint8_t force_sensor_select = 0;
static bool force_start_pending = false;
static uint32_t force_pending_sample_period_us = 10000;
static uint8_t force_pending_sensor_select = 0;

static const float FORCE_CAL_SLOPE_N_PER_V = 176.8325f;
static const int16_t FORCE_VALUE_SCALE = 10;

static inline int32_t median3(int32_t a, int32_t b, int32_t c) {
  if (a > b) { int32_t t = a; a = b; b = t; }
  if (b > c) { int32_t t = b; b = c; c = t; }
  if (a > b) { int32_t t = a; a = b; b = t; }
  return b;
}

static inline bool force_selected_right(void) {
  return (force_sensor_select == 0 || force_sensor_select == 2);
}

static inline bool force_selected_left(void) {
  return (force_sensor_select == 1 || force_sensor_select == 2);
}

static int16_t delta_mv_to_force_payload(int32_t delta_mv) {
  float delta_v = (float)delta_mv / 1000.0f;
  float force_n = FORCE_CAL_SLOPE_N_PER_V * delta_v;
  long scaled = lroundf(force_n * (float)FORCE_VALUE_SCALE);
  if (scaled > 32767L) scaled = 32767L;
  if (scaled < -32768L) scaled = -32768L;
  return (int16_t)scaled;
}

#if FORCE_BACKEND == FORCE_BACKEND_INTERNAL_CONTINUOUS

static bool force_backend_ready = false;
static bool force_tare_in_progress = false;
static uint8_t force_tare_retry_count = 0;
static bool force_tare_valid[2] = {false, false};
static int32_t force_tare_mv[2] = {0, 0};
static uint32_t force_last_adc_update_us = 0;

static const uint16_t FORCE_TARE_WARMUP_CYCLES = 12;
static const uint16_t FORCE_TARE_ACCUM_CYCLES = 96;
static const uint8_t FORCE_TARE_MAX_RETRIES = 2;
static const uint32_t FORCE_TARE_TIMEOUT_US = 1500000;
static const float FORCE_TARE_MAX_RMS_MV = 4.0f;

static const uint32_t FORCE_ADC_SAMPLING_HZ = 40000;
static const uint32_t FORCE_ADC_CONV_PER_PIN = 128;
static const uint8_t FORCE_ADC_PINS[] = { FORCE_SENSOR_RIGHT_PIN, FORCE_SENSOR_LEFT_PIN };
static const size_t FORCE_ADC_PINS_COUNT = sizeof(FORCE_ADC_PINS) / sizeof(FORCE_ADC_PINS[0]);

static volatile bool force_adc_cycle_done = false;
static adc_continuous_result_t *force_adc_result = NULL;
static bool force_have_mv[2] = {false, false};
static int32_t force_mv_filtered[2] = {0, 0};
static int32_t force_mv_hist[2][3] = {{0, 0, 0}, {0, 0, 0}};
static uint8_t force_mv_hist_idx[2] = {0, 0};
static uint16_t force_tare_warmup_done = 0;
static uint16_t force_tare_accum_cycles_done = 0;
static uint32_t force_tare_window_start_us = 0;
static int64_t force_tare_sum_mv[2] = {0, 0};
static int64_t force_tare_sum_sq_mv[2] = {0, 0};
static uint16_t force_tare_samples[2] = {0, 0};

void ARDUINO_ISR_ATTR forceAdcCompleteISR() {
  force_adc_cycle_done = true;
}

static void force_tare_reset_window(void) {
  force_tare_warmup_done = 0;
  force_tare_accum_cycles_done = 0;
  force_tare_sum_mv[0] = 0;
  force_tare_sum_mv[1] = 0;
  force_tare_sum_sq_mv[0] = 0;
  force_tare_sum_sq_mv[1] = 0;
  force_tare_samples[0] = 0;
  force_tare_samples[1] = 0;
  force_tare_window_start_us = micros();
}

static void force_tare_finalize_from_current(void) {
  bool have_all_selected = true;
  if (force_selected_right()) {
    if (force_have_mv[0]) {
      force_tare_mv[0] = force_mv_filtered[0];
      force_tare_valid[0] = true;
    } else {
      force_tare_valid[0] = false;
      have_all_selected = false;
    }
  }
  if (force_selected_left()) {
    if (force_have_mv[1]) {
      force_tare_mv[1] = force_mv_filtered[1];
      force_tare_valid[1] = true;
    } else {
      force_tare_valid[1] = false;
      have_all_selected = false;
    }
  }
  if (!have_all_selected) {
    PC_LOG_PRINTLN("[WARN] Tare fallback incomplete; channel(s) still missing samples.");
  }
  force_tare_in_progress = false;
}

static void force_adc_update_cache(void) {
  if (!force_backend_ready || !force_adc_cycle_done) return;
  force_adc_cycle_done = false;

  if (!analogContinuousRead(&force_adc_result, 0) || force_adc_result == NULL) return;

  force_last_adc_update_us = micros();
  for (size_t i = 0; i < FORCE_ADC_PINS_COUNT; i++) {
    const uint8_t pin = force_adc_result[i].pin;
    const int mv = force_adc_result[i].avg_read_mvolts;

    int idx = -1;
    if (pin == FORCE_SENSOR_RIGHT_PIN) idx = 0;
    else if (pin == FORCE_SENSOR_LEFT_PIN) idx = 1;
    else continue;

    uint8_t w = force_mv_hist_idx[idx] % 3;
    force_mv_hist[idx][w] = (int32_t)mv;
    force_mv_hist_idx[idx] = (uint8_t)((w + 1) % 3);
    force_mv_filtered[idx] = median3(force_mv_hist[idx][0], force_mv_hist[idx][1], force_mv_hist[idx][2]);
    force_have_mv[idx] = true;
  }

  if (!force_tare_in_progress) return;

  if ((uint32_t)(force_last_adc_update_us - force_tare_window_start_us) > FORCE_TARE_TIMEOUT_US) {
    PC_LOG_PRINTLN("[WARN] Tare timeout; using current baseline.");
    force_tare_finalize_from_current();
    return;
  }

  if (force_tare_warmup_done < FORCE_TARE_WARMUP_CYCLES) {
    force_tare_warmup_done++;
    return;
  }

  if (force_selected_right() && force_have_mv[0]) {
    int32_t mv = force_mv_filtered[0];
    force_tare_sum_mv[0] += (int64_t)mv;
    force_tare_sum_sq_mv[0] += (int64_t)mv * (int64_t)mv;
    force_tare_samples[0]++;
  }
  if (force_selected_left() && force_have_mv[1]) {
    int32_t mv = force_mv_filtered[1];
    force_tare_sum_mv[1] += (int64_t)mv;
    force_tare_sum_sq_mv[1] += (int64_t)mv * (int64_t)mv;
    force_tare_samples[1]++;
  }

  force_tare_accum_cycles_done++;
  if (force_tare_accum_cycles_done < FORCE_TARE_ACCUM_CYCLES) return;

  bool stable = true;
  float mean_mv[2] = {0.0f, 0.0f};

  if (force_selected_right()) {
    if (force_tare_samples[0] == 0) {
      stable = false;
    } else {
      float n = (float)force_tare_samples[0];
      mean_mv[0] = (float)force_tare_sum_mv[0] / n;
      float mean_sq = (float)force_tare_sum_sq_mv[0] / n;
      float var = mean_sq - (mean_mv[0] * mean_mv[0]);
      if (var < 0.0f) var = 0.0f;
      if (sqrtf(var) > FORCE_TARE_MAX_RMS_MV) stable = false;
    }
  }
  if (force_selected_left()) {
    if (force_tare_samples[1] == 0) {
      stable = false;
    } else {
      float n = (float)force_tare_samples[1];
      mean_mv[1] = (float)force_tare_sum_mv[1] / n;
      float mean_sq = (float)force_tare_sum_sq_mv[1] / n;
      float var = mean_sq - (mean_mv[1] * mean_mv[1]);
      if (var < 0.0f) var = 0.0f;
      if (sqrtf(var) > FORCE_TARE_MAX_RMS_MV) stable = false;
    }
  }

  if (stable) {
    if (force_selected_right()) {
      force_tare_mv[0] = (int32_t)lroundf(mean_mv[0]);
      force_tare_valid[0] = true;
    }
    if (force_selected_left()) {
      force_tare_mv[1] = (int32_t)lroundf(mean_mv[1]);
      force_tare_valid[1] = true;
    }
    force_tare_in_progress = false;
    force_tare_retry_count = 0;
    return;
  }

  if (force_tare_retry_count < FORCE_TARE_MAX_RETRIES) {
    force_tare_retry_count++;
    force_tare_reset_window();
    return;
  }

  PC_LOG_PRINTLN("[WARN] Tare unstable; using current baseline.");
  force_tare_finalize_from_current();
}

static void force_tare_start(void) {
  force_tare_in_progress = true;
  force_tare_retry_count = 0;

  if (force_selected_right()) {
    force_tare_valid[0] = false;
    force_have_mv[0] = false;
    force_mv_hist[0][0] = 0;
    force_mv_hist[0][1] = 0;
    force_mv_hist[0][2] = 0;
    force_mv_hist_idx[0] = 0;
  }
  if (force_selected_left()) {
    force_tare_valid[1] = false;
    force_have_mv[1] = false;
    force_mv_hist[1][0] = 0;
    force_mv_hist[1][1] = 0;
    force_mv_hist[1][2] = 0;
    force_mv_hist_idx[1] = 0;
  }

  force_tare_reset_window();
}

static void force_stream_start_backend(void) {
}

static void force_adc_backend_setup(void) {
  analogSetAttenuation(ADC_11db);
  analogContinuousSetWidth(12);
  analogContinuousSetAtten(ADC_11db);
  force_backend_ready = analogContinuous(FORCE_ADC_PINS, FORCE_ADC_PINS_COUNT, FORCE_ADC_CONV_PER_PIN, FORCE_ADC_SAMPLING_HZ, &forceAdcCompleteISR);
  if (force_backend_ready) {
    analogContinuousStart();
    PC_LOG_PRINTLN("Force backend: internal continuous ADC");
  } else {
    PC_LOG_PRINTLN("Force backend init failed: internal continuous ADC");
  }
}

#elif FORCE_BACKEND == FORCE_BACKEND_ADS1115

enum ForceWorkerState : uint8_t {
  FORCE_WORKER_IDLE = 0,
  FORCE_WORKER_STARTING = 1,
  FORCE_WORKER_RUNNING = 2,
  FORCE_WORKER_RETRY_WAIT = 3,
};

enum ForceEventFlags : uint32_t {
  FORCE_EVENT_NONE = 0,
  FORCE_EVENT_BACKEND_INIT_OK = 1u << 0,
  FORCE_EVENT_BACKEND_INIT_FAIL = 1u << 1,
  FORCE_EVENT_BACKEND_RETRY_FAIL = 1u << 2,
  FORCE_EVENT_TARE_TIMEOUT = 1u << 3,
  FORCE_EVENT_TARE_FALLBACK_INCOMPLETE = 1u << 4,
  FORCE_EVENT_TARE_UNSTABLE = 1u << 5,
  FORCE_EVENT_TARE_STABLE = 1u << 6,
};

struct ForceSharedChannel {
  bool valid;
  bool tare_valid;
  int16_t raw_latest;
  int16_t raw_filtered;
  int32_t mv_filtered;
  int64_t mv_accum;
  uint16_t mv_accum_count;
  int32_t tare_mv;
  uint32_t updated_us;
};

struct ForceChannelReadout {
  bool valid;
  bool tare_valid;
  int16_t raw_latest;
  int16_t raw_filtered;
  int32_t mv;
  int32_t tare_mv;
  uint32_t updated_us;
};

struct ForceStreamQueuedFrame {
  uint8_t device;
  int16_t value;
  int16_t raw_latest;
};

static Adafruit_ADS1115 force_ads;
static TaskHandle_t force_service_task_handle = NULL;
static portMUX_TYPE force_shared_mutex = portMUX_INITIALIZER_UNLOCKED;

static const uint8_t FORCE_ADC_CHANNEL_RIGHT = 0;
static const uint8_t FORCE_ADC_CHANNEL_LEFT = 1;
static const uint8_t FORCE_ADC_CHANNELS[2] = { FORCE_ADC_CHANNEL_RIGHT, FORCE_ADC_CHANNEL_LEFT };
static const uint8_t FORCE_ADC_I2C_ADDRESS = 0x48;
static const uint8_t FORCE_ADC_SDA_PIN = 25;
static const uint8_t FORCE_ADC_SCL_PIN = 26;
static const adsGain_t FORCE_ADC_GAIN = GAIN_ONE;
static const uint32_t FORCE_ADC_STALE_TIMEOUT_US = 500000;
static const uint16_t FORCE_TARE_WARMUP_CYCLES = 12;
static const uint16_t FORCE_TARE_ACCUM_CYCLES = 96;
static const uint8_t FORCE_TARE_MAX_RETRIES = 2;
static const uint32_t FORCE_TARE_TIMEOUT_US = 1500000;
static const float FORCE_TARE_MAX_RMS_MV = 4.0f;

static ForceSharedChannel force_shared_channels[2] = {};
static uint32_t force_requested_sample_period_us = 10000;
static uint8_t force_requested_sensor_select = 0;
static bool force_requested_retare = false;
static bool force_command_should_run = false;
static uint32_t force_command_generation = 0;
static bool force_backend_ready = false;
static uint8_t force_backend_address = FORCE_ADC_I2C_ADDRESS;
static ForceWorkerState force_worker_state = FORCE_WORKER_IDLE;
static uint32_t force_event_flags = FORCE_EVENT_NONE;
static uint32_t force_stream_started_us = 0;
static const uint16_t FORCE_STREAM_QUEUE_SIZE = 256;
static ForceStreamQueuedFrame force_stream_queue[FORCE_STREAM_QUEUE_SIZE] = {};
static uint16_t force_stream_queue_head = 0;
static uint16_t force_stream_queue_tail = 0;

static inline bool force_selected_right_for(uint8_t sensor_select) {
  return (sensor_select == 0 || sensor_select == 2);
}

static inline bool force_selected_left_for(uint8_t sensor_select) {
  return (sensor_select == 1 || sensor_select == 2);
}

static inline bool force_device_selected(uint8_t sensor_select, uint8_t device) {
  if (device == 0) return force_selected_right_for(sensor_select);
  if (device == 1) return force_selected_left_for(sensor_select);
  return false;
}

static uint8_t force_active_channel_count(uint8_t sensor_select) {
  return (sensor_select == 2) ? 2u : 1u;
}

static uint32_t force_max_hz_per_channel(uint8_t sensor_select) {
  return (force_active_channel_count(sensor_select) == 1u)
    ? (uint32_t)FORCE_MAX_HZ_ONE_CHANNEL
    : (uint32_t)FORCE_MAX_HZ_TWO_CHANNELS_PER_CH;
}

static uint32_t force_target_total_sampling_hz(uint8_t sensor_select) {
  return force_max_hz_per_channel(sensor_select) * (uint32_t)force_active_channel_count(sensor_select);
}

static uint32_t force_conversion_period_us_for(uint8_t sensor_select) {
  uint32_t total_hz = force_target_total_sampling_hz(sensor_select);
  if (total_hz == 0) return 0;
  return 1000000UL / total_hz;
}

static bool force_period_supported_for(uint32_t period_us, uint8_t sensor_select) {
  if (period_us == 0 || sensor_select > 2) return false;
  return ((uint64_t)period_us * (uint64_t)force_target_total_sampling_hz(sensor_select)) >= 1000000ULL;
}

static void force_set_event(uint32_t flags) {
  portENTER_CRITICAL(&force_shared_mutex);
  force_event_flags |= flags;
  portEXIT_CRITICAL(&force_shared_mutex);
}

static void force_set_backend_status(bool ready, uint8_t address) {
  portENTER_CRITICAL(&force_shared_mutex);
  force_backend_ready = ready;
  force_backend_address = address;
  portEXIT_CRITICAL(&force_shared_mutex);
}

static void force_set_worker_state(ForceWorkerState state) {
  portENTER_CRITICAL(&force_shared_mutex);
  force_worker_state = state;
  portEXIT_CRITICAL(&force_shared_mutex);
}

static void force_invalidate_selected_channels(uint8_t sensor_select, bool clear_tare) {
  portENTER_CRITICAL(&force_shared_mutex);
  if (force_selected_right_for(sensor_select)) {
    force_shared_channels[0].valid = false;
    force_shared_channels[0].raw_latest = 0;
    force_shared_channels[0].raw_filtered = 0;
    force_shared_channels[0].mv_filtered = 0;
    force_shared_channels[0].mv_accum = 0;
    force_shared_channels[0].mv_accum_count = 0;
    force_shared_channels[0].updated_us = 0;
    if (clear_tare) {
      force_shared_channels[0].tare_valid = false;
      force_shared_channels[0].tare_mv = 0;
    }
  }
  if (force_selected_left_for(sensor_select)) {
    force_shared_channels[1].valid = false;
    force_shared_channels[1].raw_latest = 0;
    force_shared_channels[1].raw_filtered = 0;
    force_shared_channels[1].mv_filtered = 0;
    force_shared_channels[1].mv_accum = 0;
    force_shared_channels[1].mv_accum_count = 0;
    force_shared_channels[1].updated_us = 0;
    if (clear_tare) {
      force_shared_channels[1].tare_valid = false;
      force_shared_channels[1].tare_mv = 0;
    }
  }
  portEXIT_CRITICAL(&force_shared_mutex);
}

static void force_publish_sample(uint8_t device, int16_t raw_latest, int16_t raw_filtered, int32_t mv_filtered, uint32_t updated_us) {
  portENTER_CRITICAL(&force_shared_mutex);
  force_shared_channels[device].valid = true;
  force_shared_channels[device].raw_latest = raw_latest;
  force_shared_channels[device].raw_filtered = raw_filtered;
  force_shared_channels[device].mv_filtered = mv_filtered;
  force_shared_channels[device].mv_accum += (int64_t)mv_filtered;
  if (force_shared_channels[device].mv_accum_count < 65535u) force_shared_channels[device].mv_accum_count++;
  force_shared_channels[device].updated_us = updated_us;
  portEXIT_CRITICAL(&force_shared_mutex);
}

static void force_publish_tare(uint8_t device, bool tare_valid, int32_t tare_mv) {
  portENTER_CRITICAL(&force_shared_mutex);
  force_shared_channels[device].tare_valid = tare_valid;
  force_shared_channels[device].tare_mv = tare_mv;
  portEXIT_CRITICAL(&force_shared_mutex);
}

static bool force_get_channel_readout(uint8_t device, ForceChannelReadout *out) {
  if (!out || device > 1) return false;

  portENTER_CRITICAL(&force_shared_mutex);
  ForceSharedChannel *channel = &force_shared_channels[device];
  out->valid = channel->valid;
  out->tare_valid = channel->tare_valid;
  out->raw_latest = channel->raw_latest;
  out->raw_filtered = channel->raw_filtered;
  out->tare_mv = channel->tare_mv;
  out->updated_us = channel->updated_us;
  if (channel->mv_accum_count > 0) {
    out->mv = (int32_t)lround((double)channel->mv_accum / (double)channel->mv_accum_count);
    channel->mv_accum = 0;
    channel->mv_accum_count = 0;
  } else {
    out->mv = channel->mv_filtered;
  }
  portEXIT_CRITICAL(&force_shared_mutex);

  return out->valid;
}

static void force_sync_local_tares(uint8_t sensor_select, bool tare_valid[2], int32_t tare_mv[2]) {
  portENTER_CRITICAL(&force_shared_mutex);
  if (force_selected_right_for(sensor_select)) {
    tare_valid[0] = force_shared_channels[0].tare_valid;
    tare_mv[0] = force_shared_channels[0].tare_mv;
  }
  if (force_selected_left_for(sensor_select)) {
    tare_valid[1] = force_shared_channels[1].tare_valid;
    tare_mv[1] = force_shared_channels[1].tare_mv;
  }
  portEXIT_CRITICAL(&force_shared_mutex);
}

static void force_stream_queue_clear(void) {
  portENTER_CRITICAL(&force_shared_mutex);
  force_stream_queue_head = 0;
  force_stream_queue_tail = 0;
  portEXIT_CRITICAL(&force_shared_mutex);
}

static bool force_stream_should_queue_sample(uint8_t device, uint32_t updated_us) {
  if (!force_stream_enabled) return false;
  if (!force_device_selected(force_sensor_select, device)) return false;
  if (updated_us == 0) return false;
  if ((int32_t)(updated_us - force_stream_started_us) < 0) return false;
  return true;
}

static void force_stream_queue_push(uint8_t device, int16_t value, int16_t raw_latest) {
  portENTER_CRITICAL(&force_shared_mutex);
  uint16_t next_head = (uint16_t)((force_stream_queue_head + 1u) % FORCE_STREAM_QUEUE_SIZE);
  if (next_head == force_stream_queue_tail) {
    force_stream_queue_tail = (uint16_t)((force_stream_queue_tail + 1u) % FORCE_STREAM_QUEUE_SIZE);
  }
  force_stream_queue[force_stream_queue_head].device = device;
  force_stream_queue[force_stream_queue_head].value = value;
  force_stream_queue[force_stream_queue_head].raw_latest = raw_latest;
  force_stream_queue_head = next_head;
  portEXIT_CRITICAL(&force_shared_mutex);
}

static bool force_stream_queue_pop(ForceStreamQueuedFrame *frame_out) {
  if (!frame_out) return false;
  portENTER_CRITICAL(&force_shared_mutex);
  if (force_stream_queue_tail == force_stream_queue_head) {
    portEXIT_CRITICAL(&force_shared_mutex);
    return false;
  }
  *frame_out = force_stream_queue[force_stream_queue_tail];
  force_stream_queue_tail = (uint16_t)((force_stream_queue_tail + 1u) % FORCE_STREAM_QUEUE_SIZE);
  portEXIT_CRITICAL(&force_shared_mutex);
  return true;
}

static bool force_service_read_command(bool *should_run_out, uint32_t *generation_out, uint8_t *sensor_select_out, uint32_t *sample_period_us_out, bool *retare_out) {
  if (!should_run_out || !generation_out || !sensor_select_out || !sample_period_us_out || !retare_out) return false;
  portENTER_CRITICAL(&force_shared_mutex);
  *should_run_out = force_command_should_run;
  *generation_out = force_command_generation;
  *sensor_select_out = force_requested_sensor_select;
  *sample_period_us_out = force_requested_sample_period_us;
  *retare_out = force_requested_retare;
  portEXIT_CRITICAL(&force_shared_mutex);
  return true;
}

static void force_tare_reset_window(uint16_t warmup_done[2], uint16_t accum_cycles_done[2], int64_t sum_mv[2], int64_t sum_sq_mv[2], uint16_t samples[2], uint32_t *window_start_us) {
  warmup_done[0] = 0;
  warmup_done[1] = 0;
  accum_cycles_done[0] = 0;
  accum_cycles_done[1] = 0;
  sum_mv[0] = 0;
  sum_mv[1] = 0;
  sum_sq_mv[0] = 0;
  sum_sq_mv[1] = 0;
  samples[0] = 0;
  samples[1] = 0;
  *window_start_us = micros();
}

static void force_worker_finalize_from_current(
  uint8_t sensor_select,
  bool have_mv[2],
  int32_t mv_filtered[2],
  bool *tare_in_progress,
  bool *have_all_selected_out
) {
  bool have_all_selected = true;
  if (force_selected_right_for(sensor_select)) {
    if (have_mv[0]) {
      force_publish_tare(0, true, mv_filtered[0]);
    } else {
      force_publish_tare(0, false, 0);
      have_all_selected = false;
    }
  }
  if (force_selected_left_for(sensor_select)) {
    if (have_mv[1]) {
      force_publish_tare(1, true, mv_filtered[1]);
    } else {
      force_publish_tare(1, false, 0);
      have_all_selected = false;
    }
  }
  if (!have_all_selected) {
    force_set_event(FORCE_EVENT_TARE_FALLBACK_INCOMPLETE);
  }
  *tare_in_progress = false;
  if (have_all_selected_out) *have_all_selected_out = have_all_selected;
}

bool force_service_validate_start(uint32_t period_us, uint8_t device) {
#if FORCE_BACKEND == FORCE_BACKEND_ADS1115
  return force_period_supported_for(period_us, device);
#else
  return (period_us != 0 && device <= 2);
#endif
}

static bool init_force_ads(uint8_t sensor_select) {
  (void)sensor_select;
  force_backend_address = FORCE_ADC_I2C_ADDRESS;
  if (!force_ads.begin(FORCE_ADC_I2C_ADDRESS, &Wire)) return false;
  force_ads.setGain(FORCE_ADC_GAIN);
  // The Adafruit single-ended read path is blocking, so lower ADS data-rate
  // settings do not deliver the requested effective stream rates in practice.
  // Run the converter at its fastest setting and pace reads in the worker.
  force_ads.setDataRate(RATE_ADS1115_475SPS);
  return true;
}

static void force_ads_worker_task(void *arg) {
  (void)arg;

  bool wire_initialized = false;
  bool backend_ready_local = false;
  bool retry_after_failure = false;
  uint32_t seen_generation = 0;
  uint8_t worker_sensor_select = 0;
  uint8_t next_channel_idx = 0;
  bool tare_in_progress = false;
  uint8_t tare_retry_count = 0;
  uint32_t force_last_adc_update_us = 0;
  bool have_raw[2] = {false, false};
  bool have_mv[2] = {false, false};
  bool tare_valid_local[2] = {false, false};
  int32_t tare_mv_local[2] = {0, 0};
  int16_t raw_latest[2] = {0, 0};
  int16_t raw_filtered[2] = {0, 0};
  int32_t mv_filtered[2] = {0, 0};
  int16_t raw_hist[2][3] = {{0, 0, 0}, {0, 0, 0}};
  uint8_t raw_hist_idx[2] = {0, 0};
  int32_t mv_hist[2][3] = {{0, 0, 0}, {0, 0, 0}};
  uint8_t mv_hist_idx[2] = {0, 0};
  uint16_t tare_warmup_done[2] = {0, 0};
  uint16_t tare_accum_cycles_done[2] = {0, 0};
  uint32_t tare_window_start_us = 0;
  int64_t tare_sum_mv[2] = {0, 0};
  int64_t tare_sum_sq_mv[2] = {0, 0};
  uint16_t tare_samples[2] = {0, 0};
  uint32_t next_sample_us = 0;
  uint32_t conversion_period_us = force_conversion_period_us_for(2);
  ForceWorkerState state = FORCE_WORKER_IDLE;
  TickType_t retry_until_tick = 0;

  for (;;) {
    bool should_run = false;
    uint32_t command_generation = 0;
    uint32_t requested_period_us = 0;
    uint8_t requested_sensor_select = 0;
    bool requested_retare = false;
    force_service_read_command(&should_run, &command_generation, &requested_sensor_select, &requested_period_us, &requested_retare);
    (void)requested_period_us;

    if (command_generation != seen_generation) {
      seen_generation = command_generation;
      worker_sensor_select = requested_sensor_select;
      next_channel_idx = 0;
      retry_after_failure = false;

      if (!should_run) {
        tare_in_progress = false;
        tare_retry_count = 0;
        state = FORCE_WORKER_IDLE;
        force_set_worker_state(state);
      } else {
        force_invalidate_selected_channels(worker_sensor_select, requested_retare);
        state = FORCE_WORKER_STARTING;
        force_set_worker_state(state);
      }
    }

    switch (state) {
      case FORCE_WORKER_IDLE:
        vTaskDelay(pdMS_TO_TICKS(FORCE_SERVICE_IDLE_DELAY_MS));
        break;

      case FORCE_WORKER_STARTING: {
        if (!wire_initialized) {
          Wire.begin(FORCE_ADC_SDA_PIN, FORCE_ADC_SCL_PIN);
          wire_initialized = true;
          vTaskDelay(pdMS_TO_TICKS(20));
        }

        backend_ready_local = init_force_ads(worker_sensor_select);
        force_set_backend_status(backend_ready_local, force_backend_address);
        if (!backend_ready_local) {
          force_set_event(retry_after_failure ? FORCE_EVENT_BACKEND_RETRY_FAIL : FORCE_EVENT_BACKEND_INIT_FAIL);
          retry_after_failure = true;
          retry_until_tick = xTaskGetTickCount() + pdMS_TO_TICKS(FORCE_SERVICE_RETRY_DELAY_MS);
          state = FORCE_WORKER_RETRY_WAIT;
          force_set_worker_state(state);
          break;
        }

        force_set_event(FORCE_EVENT_BACKEND_INIT_OK);
        retry_after_failure = false;
        tare_in_progress = (FORCE_TARE_ENABLED && requested_retare) ? true : false;
        tare_retry_count = 0;
        force_last_adc_update_us = 0;
        tare_valid_local[0] = false;
        tare_valid_local[1] = false;
        tare_mv_local[0] = 0;
        tare_mv_local[1] = 0;

        if (force_selected_right_for(worker_sensor_select)) {
          if (requested_retare) force_publish_tare(0, false, 0);
          have_raw[0] = false;
          have_mv[0] = false;
          raw_latest[0] = 0;
          raw_filtered[0] = 0;
          mv_filtered[0] = 0;
          raw_hist[0][0] = 0;
          raw_hist[0][1] = 0;
          raw_hist[0][2] = 0;
          raw_hist_idx[0] = 0;
          mv_hist[0][0] = 0;
          mv_hist[0][1] = 0;
          mv_hist[0][2] = 0;
          mv_hist_idx[0] = 0;
        }
        if (force_selected_left_for(worker_sensor_select)) {
          if (requested_retare) force_publish_tare(1, false, 0);
          have_raw[1] = false;
          have_mv[1] = false;
          raw_latest[1] = 0;
          raw_filtered[1] = 0;
          mv_filtered[1] = 0;
          raw_hist[1][0] = 0;
          raw_hist[1][1] = 0;
          raw_hist[1][2] = 0;
          raw_hist_idx[1] = 0;
          mv_hist[1][0] = 0;
          mv_hist[1][1] = 0;
          mv_hist[1][2] = 0;
          mv_hist_idx[1] = 0;
        }

        if (requested_retare) {
          force_tare_reset_window(tare_warmup_done, tare_accum_cycles_done, tare_sum_mv, tare_sum_sq_mv, tare_samples, &tare_window_start_us);
        } else {
          force_sync_local_tares(worker_sensor_select, tare_valid_local, tare_mv_local);
        }
        conversion_period_us = force_conversion_period_us_for(worker_sensor_select);
        next_sample_us = micros();
        state = FORCE_WORKER_RUNNING;
        force_set_worker_state(state);
        break;
      }

      case FORCE_WORKER_RETRY_WAIT:
        if ((int32_t)(xTaskGetTickCount() - retry_until_tick) >= 0) {
          state = FORCE_WORKER_STARTING;
          force_set_worker_state(state);
        } else {
          vTaskDelay(pdMS_TO_TICKS(FORCE_SERVICE_IDLE_DELAY_MS));
        }
        break;

      case FORCE_WORKER_RUNNING: {
        uint32_t now_us = micros();
        if ((int32_t)(now_us - next_sample_us) < 0) {
          uint32_t wait_us = next_sample_us - now_us;
          if (wait_us > 1000UL) {
            vTaskDelay(pdMS_TO_TICKS(wait_us / 1000UL));
          } else {
            delayMicroseconds(wait_us);
          }
          break;
        }

        uint8_t sample_device = next_channel_idx;
        if (worker_sensor_select == 0) sample_device = 0;
        else if (worker_sensor_select == 1) sample_device = 1;
        else next_channel_idx ^= 1;

        uint8_t ads_channel = FORCE_ADC_CHANNELS[sample_device];
        int16_t raw = force_ads.readADC_SingleEnded(ads_channel);
        float volts = force_ads.computeVolts(raw);
        int32_t mv = (int32_t)lroundf(volts * 1000.0f);
        raw_latest[sample_device] = raw;

        uint8_t rw = raw_hist_idx[sample_device] % 3;
        raw_hist[sample_device][rw] = raw;
        raw_hist_idx[sample_device] = (uint8_t)((rw + 1) % 3);
        int16_t filtered_raw = (int16_t)median3(raw_hist[sample_device][0], raw_hist[sample_device][1], raw_hist[sample_device][2]);
        raw_filtered[sample_device] = filtered_raw;
        have_raw[sample_device] = true;

        force_last_adc_update_us = micros();

        uint8_t w = mv_hist_idx[sample_device] % 3;
        mv_hist[sample_device][w] = mv;
        mv_hist_idx[sample_device] = (uint8_t)((w + 1) % 3);
        int32_t filtered_mv = median3(mv_hist[sample_device][0], mv_hist[sample_device][1], mv_hist[sample_device][2]);
        mv_filtered[sample_device] = filtered_mv;
        have_mv[sample_device] = true;
        force_publish_sample(sample_device, raw_latest[sample_device], filtered_raw, filtered_mv, force_last_adc_update_us);

#if FORCE_TARE_ENABLED
        if (tare_in_progress && force_device_selected(worker_sensor_select, sample_device)) {
          if ((uint32_t)(force_last_adc_update_us - tare_window_start_us) > FORCE_TARE_TIMEOUT_US) {
            force_set_event(FORCE_EVENT_TARE_TIMEOUT);
            force_worker_finalize_from_current(worker_sensor_select, have_mv, mv_filtered, &tare_in_progress, NULL);
            force_sync_local_tares(worker_sensor_select, tare_valid_local, tare_mv_local);
          } else if (tare_warmup_done[sample_device] < FORCE_TARE_WARMUP_CYCLES) {
            tare_warmup_done[sample_device]++;
          } else {
            tare_sum_mv[sample_device] += (int64_t)filtered_mv;
            tare_sum_sq_mv[sample_device] += (int64_t)filtered_mv * (int64_t)filtered_mv;
            tare_samples[sample_device]++;
            tare_accum_cycles_done[sample_device]++;

            bool ready = true;
            for (uint8_t idx = 0; idx < 2; idx++) {
              if (!force_device_selected(worker_sensor_select, idx)) continue;
              if (tare_accum_cycles_done[idx] < FORCE_TARE_ACCUM_CYCLES) {
                ready = false;
                break;
              }
            }

            if (ready) {
              bool stable = true;
              float mean_mv[2] = {0.0f, 0.0f};
              for (uint8_t idx = 0; idx < 2; idx++) {
                if (!force_device_selected(worker_sensor_select, idx)) continue;
                if (tare_samples[idx] == 0) {
                  stable = false;
                  continue;
                }

                float n = (float)tare_samples[idx];
                mean_mv[idx] = (float)tare_sum_mv[idx] / n;
                float mean_sq = (float)tare_sum_sq_mv[idx] / n;
                float var = mean_sq - (mean_mv[idx] * mean_mv[idx]);
                if (var < 0.0f) var = 0.0f;
                if (sqrtf(var) > FORCE_TARE_MAX_RMS_MV) stable = false;
              }

              if (stable) {
                for (uint8_t idx = 0; idx < 2; idx++) {
                  if (!force_device_selected(worker_sensor_select, idx)) continue;
                  tare_valid_local[idx] = true;
                  tare_mv_local[idx] = (int32_t)lroundf(mean_mv[idx]);
                  force_publish_tare(idx, true, tare_mv_local[idx]);
                }
                tare_in_progress = false;
                tare_retry_count = 0;
                force_set_event(FORCE_EVENT_TARE_STABLE);
              } else if (tare_retry_count < FORCE_TARE_MAX_RETRIES) {
                tare_retry_count++;
                force_tare_reset_window(tare_warmup_done, tare_accum_cycles_done, tare_sum_mv, tare_sum_sq_mv, tare_samples, &tare_window_start_us);
              } else {
                force_set_event(FORCE_EVENT_TARE_UNSTABLE);
                force_worker_finalize_from_current(worker_sensor_select, have_mv, mv_filtered, &tare_in_progress, NULL);
                force_sync_local_tares(worker_sensor_select, tare_valid_local, tare_mv_local);
              }
            }
          }
        }
#endif

        if (!tare_in_progress &&
            force_stream_should_queue_sample(sample_device, force_last_adc_update_us)
#if FORCE_TARE_ENABLED
            && tare_valid_local[sample_device]
#endif
        ) {
          int32_t delta_mv = filtered_mv - tare_mv_local[sample_device];
          int16_t value = delta_mv_to_force_payload(delta_mv);
          force_stream_queue_push(sample_device, value, raw_latest[sample_device]);
        }

        uint32_t finish_us = micros();
        next_sample_us += conversion_period_us;
        if ((int32_t)(finish_us - next_sample_us) >= 0) {
          next_sample_us = finish_us + conversion_period_us;
        }
        break;
      }
    }
  }
}

static void force_debug_log_sample(uint8_t device, const ForceChannelReadout &sample, int32_t delta_mv, int16_t payload) {
#if FORCE_DEBUG_LOG
  static uint32_t next_log_us = 0;
  uint32_t now_us = micros();
  if ((int32_t)(now_us - next_log_us) < 0) return;
  next_log_us = now_us + 200000;

  PC_LOG_PRINTF("FORCE d=%u raw=%d rawf=%d mv=%ld tare=%ld dmv=%ld out=%d(0.1N)\n",
                (unsigned int)device, (int)sample.raw_latest, (int)sample.raw_filtered,
                (long)sample.mv, (long)sample.tare_mv, (long)delta_mv, (int)payload);
#else
  (void)device;
  (void)sample;
  (void)delta_mv;
  (void)payload;
#endif
}

#else
#error Unsupported FORCE_BACKEND value
#endif

void force_service_init(void) {
#if FORCE_BACKEND == FORCE_BACKEND_ADS1115
  force_service_task_handle = NULL;
  force_set_backend_status(false, FORCE_ADC_I2C_ADDRESS);
  force_set_worker_state(FORCE_WORKER_IDLE);
  BaseType_t create_result = xTaskCreatePinnedToCore(
    force_ads_worker_task,
    "force_ads",
    FORCE_SERVICE_TASK_STACK_WORDS,
    NULL,
    FORCE_SERVICE_TASK_PRIORITY,
    &force_service_task_handle,
    FORCE_SERVICE_TASK_CORE
  );
  if (create_result != pdPASS) {
    PC_LOG_PRINTLN("Force backend init failed: ADS1115 worker task");
    force_service_task_handle = NULL;
  }
#if FORCE_TARE_ENABLED && FORCE_TARE_AT_BOOT
  force_invalidate_selected_channels(2, true);
  portENTER_CRITICAL(&force_shared_mutex);
  force_requested_sample_period_us = force_sample_period_us;
  force_requested_sensor_select = 2;
  force_requested_retare = true;
  force_command_should_run = true;
  force_command_generation++;
  portEXIT_CRITICAL(&force_shared_mutex);
#endif
#else
  force_adc_backend_setup();
#endif
}

void force_service_queue_start(uint32_t period_us, uint8_t device) {
  force_stream_enabled = false;
  force_pending_sample_period_us = period_us;
  force_pending_sensor_select = device;
  force_start_pending = true;
  force_stream_started_us = 0;
  force_stream_queue_clear();
}

void force_service_stop(void) {
  force_start_pending = false;
  force_stream_enabled = false;
  force_stream_started_us = 0;
  force_stream_queue_clear();

#if FORCE_BACKEND == FORCE_BACKEND_ADS1115
#if !(FORCE_TARE_ENABLED && FORCE_TARE_AT_BOOT && !FORCE_TARE_ON_START)
  portENTER_CRITICAL(&force_shared_mutex);
  force_command_should_run = false;
  force_command_generation++;
  portEXIT_CRITICAL(&force_shared_mutex);
#endif
#endif
}

void force_service_poll_start_pending(void) {
  if (!force_start_pending) return;

  force_sample_period_us = force_pending_sample_period_us;
  force_sensor_select = force_pending_sensor_select;
  force_stream_enabled = true;
  next_force_sample_us = micros();
  force_stream_started_us = next_force_sample_us;
  force_stream_queue_clear();

#if FORCE_BACKEND == FORCE_BACKEND_ADS1115
  force_invalidate_selected_channels(force_sensor_select, FORCE_TARE_ENABLED && FORCE_TARE_ON_START);
  portENTER_CRITICAL(&force_shared_mutex);
  force_requested_sample_period_us = force_sample_period_us;
  force_requested_sensor_select = force_sensor_select;
  force_requested_retare = (FORCE_TARE_ENABLED && FORCE_TARE_ON_START);
  force_command_should_run = true;
  force_command_generation++;
  portEXIT_CRITICAL(&force_shared_mutex);
#else
  if (!force_backend_ready) {
    force_adc_backend_setup();
    if (!force_backend_ready) {
      PC_LOG_PRINTLN("[WARN] Deferred force backend init failed; will retry.");
      return;
    }
  }
  force_stream_start_backend();
#if FORCE_TARE_ENABLED && FORCE_TARE_ON_START
  force_tare_start();
#endif
#endif

  force_start_pending = false;
}

void force_service_poll_events(void) {
#if FORCE_BACKEND == FORCE_BACKEND_ADS1115
  uint32_t events = FORCE_EVENT_NONE;
  bool right_tare_valid = false;
  bool left_tare_valid = false;
  int32_t right_tare_mv = 0;
  int32_t left_tare_mv = 0;
  uint8_t backend_address = FORCE_ADC_I2C_ADDRESS;

  portENTER_CRITICAL(&force_shared_mutex);
  events = force_event_flags;
  force_event_flags = FORCE_EVENT_NONE;
  right_tare_valid = force_shared_channels[0].tare_valid;
  left_tare_valid = force_shared_channels[1].tare_valid;
  right_tare_mv = force_shared_channels[0].tare_mv;
  left_tare_mv = force_shared_channels[1].tare_mv;
  backend_address = force_backend_address;
  portEXIT_CRITICAL(&force_shared_mutex);

  if (events & FORCE_EVENT_BACKEND_INIT_OK) {
    PC_LOG_PRINT("Force backend: ADS1115 @ 0x");
    if (backend_address < 16) PC_LOG_PRINT('0');
    PC_LOG_PRINTLN(backend_address, HEX);
  }
  if (events & FORCE_EVENT_BACKEND_INIT_FAIL) {
    PC_LOG_PRINTLN("Force backend init failed: ADS1115");
  }
  if (events & FORCE_EVENT_BACKEND_RETRY_FAIL) {
    PC_LOG_PRINTLN("[WARN] Deferred force backend init failed; will retry.");
  }
  if (events & FORCE_EVENT_TARE_TIMEOUT) {
    PC_LOG_PRINTLN("[WARN] ADS tare timeout; using current baseline.");
  }
  if (events & FORCE_EVENT_TARE_UNSTABLE) {
    PC_LOG_PRINTLN("[WARN] ADS tare unstable; using current baseline.");
  }
  if (events & FORCE_EVENT_TARE_FALLBACK_INCOMPLETE) {
    PC_LOG_PRINTLN("[WARN] ADS tare fallback incomplete; channel(s) still missing samples.");
    PC_LOG_PRINTF("ADS tare fallback: right_valid=%u right_tare_mv=%ld left_valid=%u left_tare_mv=%ld\n",
                  right_tare_valid ? 1u : 0u, (long)right_tare_mv,
                  left_tare_valid ? 1u : 0u, (long)left_tare_mv);
  }
  if (events & FORCE_EVENT_TARE_STABLE) {
    PC_LOG_PRINTF("ADS tare stable: right_valid=%u right_tare_mv=%ld left_valid=%u left_tare_mv=%ld\n",
                  right_tare_valid ? 1u : 0u, (long)right_tare_mv,
                  left_tare_valid ? 1u : 0u, (long)left_tare_mv);
  }
#endif
}

void force_service_poll_stream(ForceDataSender send_force_data) {
  if (!force_stream_enabled || !send_force_data) return;

#if FORCE_BACKEND == FORCE_BACKEND_ADS1115
  ForceStreamQueuedFrame frame = {};
  while (force_stream_queue_pop(&frame)) {
    send_force_data(frame.device, frame.value, frame.raw_latest);
  }
  return;
#else

  uint32_t now = micros();
  if ((int32_t)(now - next_force_sample_us) < 0) return;

  next_force_sample_us += force_sample_period_us;
  if ((int32_t)(now - next_force_sample_us) >= 0) next_force_sample_us = now + force_sample_period_us;

  bool do_right = (force_sensor_select == 0 || force_sensor_select == 2);
  bool do_left = (force_sensor_select == 1 || force_sensor_select == 2);

  if (do_right) {
#if FORCE_TARE_ENABLED
    if (force_tare_valid[0])
#endif
    {
      int32_t mv = 0;
      if (force_service_get_latest_mv(0, &mv)) {
        int32_t delta_mv = mv - force_tare_mv[0];
        int16_t value = delta_mv_to_force_payload(delta_mv);
        send_force_data(0, value, 0);
      }
    }
  }

  if (do_left) {
#if FORCE_TARE_ENABLED
    if (force_tare_valid[1])
#endif
    {
      int32_t mv = 0;
      if (force_service_get_latest_mv(1, &mv)) {
        int32_t delta_mv = mv - force_tare_mv[1];
        int16_t value = delta_mv_to_force_payload(delta_mv);
        send_force_data(1, value, 0);
      }
    }
  }
#endif
}

bool force_service_get_latest_mv(uint8_t device, int32_t *mv_out) {
#if FORCE_BACKEND == FORCE_BACKEND_ADS1115
  ForceChannelReadout sample = {};
  if (!mv_out) return false;
  if (!force_get_channel_readout(device, &sample)) return false;
  if (sample.updated_us == 0 || (uint32_t)(micros() - sample.updated_us) > FORCE_ADC_STALE_TIMEOUT_US) return false;
  *mv_out = sample.mv;
  return true;
#else
  if (!mv_out || device > 1 || !force_have_mv[device]) return false;
  *mv_out = force_mv_filtered[device];
  return true;
#endif
}
