# ESP32-S3 (ESP-IDF) build for Sky Lens.
# This is the idf.py component definition; the build is driven from the
# top-level firmware/esp32 directory with `idf.py build`.
idf_component_register(
    SRCS
        "main/main.c"
        "main/coincidence.c"
        "main/adc.c"
        "main/sipm_bias.c"
        "main/imu.c"
        "main/pressure.c"
        "main/skymap.c"
        "main/zenith.c"
        "main/lifetime.c"
        "main/sdlog.c"
        "main/display.c"
        "main/ble.c"
        "main/wifi.c"
        "main/proto.c"
        "main/power.c"
    INCLUDE_DIRS
        "main"
    REQUIRES
        driver
        esp_timer
        nvs_flash
        fatfs
        bt
        esp_wifi
)