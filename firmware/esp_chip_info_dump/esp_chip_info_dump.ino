#include <Arduino.h>

#if __has_include(<esp_system.h>)
#include <esp_system.h>
#define HAS_ESP_SYSTEM 1
#else
#define HAS_ESP_SYSTEM 0
#endif

namespace {

constexpr uint32_t kBaudRate = 115200;

void printDivider() {
  Serial.println(F("--------------------------------------------------"));
}

void printYesNoLine(const __FlashStringHelper* label, bool value) {
  Serial.print(label);
  Serial.println(value ? F("Yes") : F("No"));
}

void printBytesLine(const __FlashStringHelper* label, uint32_t bytes) {
  Serial.print(label);
  Serial.print(bytes);
  Serial.print(F(" bytes ("));
  Serial.print(bytes / 1024.0f, 2);
  Serial.println(F(" KB)"));
}

void printChipFeatures() {
  Serial.println(F("Chip features:"));
  printYesNoLine(F("  Wi-Fi: "), true);
  printYesNoLine(F("  BLE: "), true);
  printYesNoLine(F("  Classic BT: "), true);
  Serial.println(F("  Embedded flash: Unknown from Arduino API"));
  printYesNoLine(F("  PSRAM present: "), ESP.getPsramSize() > 0);
}

void printPsramInfo() {
  const uint32_t psramSize = ESP.getPsramSize();

  printBytesLine(F("PSRAM size: "), psramSize);
  if (psramSize == 0) {
    Serial.println(F("PSRAM free: Not available"));
    Serial.println(F("PSRAM largest free block: Not available"));
    return;
  }

  printBytesLine(F("PSRAM free: "), ESP.getFreePsram());
  printBytesLine(F("PSRAM largest free block: "), ESP.getMaxAllocPsram());
}

void printFlashMode() {
  Serial.print(F("Flash mode: "));
  switch (ESP.getFlashChipMode()) {
    case FM_QIO:
      Serial.println(F("QIO"));
      break;
    case FM_QOUT:
      Serial.println(F("QOUT"));
      break;
    case FM_DIO:
      Serial.println(F("DIO"));
      break;
    case FM_DOUT:
      Serial.println(F("DOUT"));
      break;
    case FM_FAST_READ:
      Serial.println(F("FAST_READ"));
      break;
    case FM_SLOW_READ:
      Serial.println(F("SLOW_READ"));
      break;
    default:
      Serial.println(F("Unknown"));
      break;
  }
}

void printMacAddress() {
  const uint64_t chipid = ESP.getEfuseMac();
  char macString[18];
  snprintf(
      macString,
      sizeof(macString),
      "%02X:%02X:%02X:%02X:%02X:%02X",
      static_cast<uint8_t>(chipid >> 40),
      static_cast<uint8_t>(chipid >> 32),
      static_cast<uint8_t>(chipid >> 24),
      static_cast<uint8_t>(chipid >> 16),
      static_cast<uint8_t>(chipid >> 8),
      static_cast<uint8_t>(chipid));

  Serial.print(F("Base MAC address: "));
  Serial.println(macString);
}

#if HAS_ESP_SYSTEM
const __FlashStringHelper* resetReasonToString(esp_reset_reason_t reason) {
  switch (reason) {
    case ESP_RST_UNKNOWN:
      return F("Unknown");
    case ESP_RST_POWERON:
      return F("Power-on");
    case ESP_RST_EXT:
      return F("External pin");
    case ESP_RST_SW:
      return F("Software");
    case ESP_RST_PANIC:
      return F("Exception/Panic");
    case ESP_RST_INT_WDT:
      return F("Interrupt watchdog");
    case ESP_RST_TASK_WDT:
      return F("Task watchdog");
    case ESP_RST_WDT:
      return F("Other watchdog");
    case ESP_RST_DEEPSLEEP:
      return F("Deep sleep wake");
    case ESP_RST_BROWNOUT:
      return F("Brownout");
    case ESP_RST_SDIO:
      return F("SDIO");
    default:
      return F("Unmapped");
  }
}
#endif

void printResetReason() {
#if HAS_ESP_SYSTEM
  const esp_reset_reason_t reason = esp_reset_reason();
  Serial.print(F("Reset reason: "));
  Serial.print(resetReasonToString(reason));
  Serial.print(F(" ("));
  Serial.print(static_cast<int>(reason));
  Serial.println(F(")"));
#else
  Serial.println(F("Reset reason: Unknown"));
#endif
}

void printChipReport() {
  printDivider();
  Serial.println(F("ESP32 Chip Report"));
  printDivider();

  Serial.print(F("Chip model: "));
  Serial.println(ESP.getChipModel());

  Serial.print(F("Chip revision: "));
  Serial.println(ESP.getChipRevision());

  Serial.print(F("Chip cores: "));
  Serial.println(ESP.getChipCores());

  Serial.print(F("CPU frequency: "));
  Serial.print(ESP.getCpuFreqMHz());
  Serial.println(F(" MHz"));

  Serial.print(F("XTAL frequency: "));
  Serial.print(getXtalFrequencyMhz());
  Serial.println(F(" MHz"));

  Serial.print(F("APB frequency: "));
  Serial.print(getApbFrequency() / 1000000UL);
  Serial.println(F(" MHz"));

  printChipFeatures();
  printDivider();

  printBytesLine(F("Flash chip size: "), ESP.getFlashChipSize());

  Serial.print(F("Flash chip speed: "));
  Serial.print(ESP.getFlashChipSpeed() / 1000000UL);
  Serial.println(F(" MHz"));

  printFlashMode();

  printBytesLine(F("Sketch size: "), ESP.getSketchSize());
  printBytesLine(F("Free sketch space: "), ESP.getFreeSketchSpace());
  printDivider();

  printBytesLine(F("Heap size: "), ESP.getHeapSize());
  printBytesLine(F("Free heap: "), ESP.getFreeHeap());
  printBytesLine(F("Minimum free heap: "), ESP.getMinFreeHeap());
  printBytesLine(F("Largest free heap block: "), ESP.getMaxAllocHeap());
  printPsramInfo();
  printDivider();

  printMacAddress();

  Serial.print(F("SDK version: "));
  Serial.println(ESP.getSdkVersion());

  printResetReason();
  printDivider();
  Serial.println(F("Send 'r' in Serial Monitor to print this report again."));
  printDivider();
}

}  // namespace

void setup() {
  Serial.begin(kBaudRate);
  delay(1500);

  while (!Serial && millis() < 4000) {
    delay(10);
  }

  printChipReport();
}

void loop() {
  while (Serial.available() > 0) {
    const char incoming = static_cast<char>(Serial.read());
    if (incoming == 'r' || incoming == 'R') {
      printChipReport();
    }
  }
}
