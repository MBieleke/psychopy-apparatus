# Replacement LED calibration

Default: `FAULTY_LED_CALIBRATION false` in faulty_led_calibration.h. Healthy units bypass all calibration code and tables at compile time.

For the faulty (main Apparatus with new LED strip) unit set `FAULTY_LED_CALIBRATION true` (or define it in build flags). This applies the 17x17x17 trilinear RGB lookup only to main-strip hole 6. The secondary LED remains uncorrected. All holes receive the common RGB-sum ceiling of 384 used during calibration, keeping reference and corrected outputs consistent. Pure primaries can still reach 255; combined white is limited.

Current-camera/cutout validation: 16 colors, mean relative camera mismatch 1.73%, p95 3.87%; Human vision potentially not perfectly aligning with this preliminary cal

No firmware was flashed by this change.
