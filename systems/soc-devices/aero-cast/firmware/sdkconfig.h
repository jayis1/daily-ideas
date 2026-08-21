/* sdkconfig.h — build-time configuration for Aero Cast */

#ifndef AERO_CAST_SDKCONFIG_H
#define AERO_CAST_SDKCONFIG_H

/* ---- Sampling ---- */
#define SAMPLE_RATE_HZ          20      /* measurement rate (1-20 Hz) */
#define NUM_PATHS              3       /* sonic paths (tripod geometry) */
#define BURST_CYCLES           16      /* 40 kHz burst length */
#define TIMEOUT_US             1000    /* echo timeout (1 ms) */

/* ---- Geometry (mm) — must match calibration.c ---- */
#define PATH_LENGTH_MM         100.0f  /* nominal path length */
#define FRAME_RADIUS_MM        40.0f   /* bottom ring radius */
#define FRAME_HEIGHT_MM        80.0f   /* top-to-bottom height */

/* ---- Timing ---- */
#define CLOCK_FREQ_HZ          125000000  /* RP2040 system clock */
#define TIMER_RESOLUTION_S     (1.0f / CLOCK_FREQ_HZ)  /* 8 ns */
#define SPEED_OF_SOUND_20C     343.0f   /* m/s at 20°C, dry air */

/* ---- I2C addresses ---- */
#define BME280_I2C_ADDR        0x76
#define SSD1306_I2C_ADDR       0x3C

/* ---- Pin assignments (match README pin table) ---- */
#define PIN_I2C_SDA            0
#define PIN_I2C_SCL            1
#define PIN_UART_TX            2
#define PIN_UART_RX            3
#define PIN_SD_CS              4
#define PIN_SPI_SCK            5
#define PIN_SPI_MOSI           6
#define PIN_SPI_MISO           7
#define PIN_BTN_PWR            8
#define PIN_BTN_MODE           9
#define PIN_BTN_AVG            10
#define PIN_LED_STATUS         11
#define PIN_LED_DATA           12
#define PIN_MUX_A             13
#define PIN_MUX_B             14
#define PIN_HV_EN             15
#define PIN_PIO_TX            16
#define PIN_PIO_RX            17
#define PIN_DAC_CS            19
#define PIN_ADC_BATT          20
#define PIN_CHRG_STATUS       21
#define PIN_ESP_RESET         22

/* ---- Averaging windows (seconds) ---- */
#define AVG_WIN_SHORT         1
#define AVG_WIN_MED           10
#define AVG_WIN_LONG          60
#define AVG_WIN_FLUX          1800   /* 30 min for eddy covariance */

/* ---- SD logging ---- */
#define SD_MAX_FILE_SIZE_MB   50
#define SD_BUFFER_SIZE        4096

/* ---- BLE bridge protocol ---- */
#define BLE_MSG_WIND          0x01  /* wind data packet */
#define BLE_MSG_STATUS        0x02  /* status packet */
#define BLE_MSG_CMD           0x03  /* command from phone */
#define BLE_MSG_ACK           0x04  /* ack from device */
#define BLE_MSG_RAW           0x05  /* raw TOF data */

#endif /* AERO_CAST_SDKCONFIG_H */