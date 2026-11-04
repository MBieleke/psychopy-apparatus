# Replacement LED calibration

Default: `FAULTY_LED_CALIBRATION true` in faulty_led_calibration.h. It corrects only hole 6 on the main eight-LED strip. Set it to `false` for normal units, or override it through build flags. The secondary strip and every other hole always receive the requested RGB unchanged.

There is no RGB-sum brightness limiter. Each output channel remains within the normal 0..255 byte range. The lookup was measured only with input RGB sums up to 384 and contains legacy constrained values outside that domain. Therefore hole 6 passes commands with sums above 384 through unchanged, rather than silently dimming bright whites/mixes using those entries. For example requested white (255,255,255) remains (255,255,255). This bypass is a calibration-domain guard, not a brightness cap. A new unrestricted calibration would be required to correct that unmeasured domain.

Within the measured domain, lookup corrections can still increase or decrease individual channel values. Calibration validation was camera/cutout-specific: 16 colors, mean relative camera mismatch 1.73%, p95 3.87%; human visual matching is not guaranteed. Do not apply the comparator's software correction and firmware correction simultaneously.

No firmware was flashed by this change.
