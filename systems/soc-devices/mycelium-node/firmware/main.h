/**
 * Mycelium Node - Mushroom Fruiting Chamber Environmental Controller
 * 
 * ESP32-C6-MINI-1 based multi-zone sensor platform with PID-controlled
 * humidifier, heater, exhaust fan, and grow light actuators.
 * 
 * Hardware: ESP32-C6-MINI-1, SHT40 x2, SCD41, TSL2591, DS18B20 x2,
 *           SSD1306 OLED, rotary encoder, 4x IRLML6344 MOSFET drivers
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef MAIN_H
#define MAIN_H

#include <stdint.h>
#include <stdbool.h>

/* ======================== PIN DEFINITIONS ======================== */

/* I2C Bus */
#define I2C_SDA_GPIO        GPIO_NUM_3
#define I2C_SCL_GPIO        GPIO_NUM_4
#define I2C_PORT            I2C_NUM_0
#define I2C_FREQ_HZ         400000  /* 400 kHz Fast Mode */

/* PWM Actuator Outputs */
#define PWM_HUM_GPIO        GPIO_NUM_5   /* Humidifier MOSFET */
#define PWM_HEAT_GPIO       GPIO_NUM_6   /* Heater MOSFET */
#define PWM_FAN_GPIO        GPIO_NUM_7   /* Exhaust fan MOSFET */
#define PWM_LIGHT_GPIO      GPIO_NUM_8   /* Grow light MOSFET */

/* PWM Configuration */
#define PWM_FREQ_HUM        25000    /* 25 kHz (ultrasonic mister) */
#define PWM_FREQ_HEAT       1        /* 1 Hz (slow thermal) */
#define PWM_FREQ_FAN        25000    /* 25 kHz (PC fan standard) */
#define PWM_FREQ_LIGHT      1000     /* 1 kHz (flicker-free LED) */
#define PWM_RESOLUTION      8        /* 8-bit: 0-255 maps to 0-100% */

/* 1-Wire Bus (DS18B20) */
#define ONEWIRE_GPIO        GPIO_NUM_9
#define DS18B20_PWR_GPIO    GPIO_NUM_16  /* Power gate MOSFET */

/* Rotary Encoder */
#define ROT_ENC_A_GPIO      GPIO_NUM_10
#define ROT_ENC_B_GPIO      GPIO_NUM_11
#define ROT_ENC_SW_GPIO     GPIO_NUM_12

/* Miscellaneous */
#define BUZZER_GPIO         GPIO_NUM_13
#define RELAY_GPIO          GPIO_NUM_14   /* Safety thermal cutoff relay */
#define SCD41_RESET_GPIO    GPIO_NUM_15   /* SCD41 active-low reset */
#define WS2812_GPIO         GPIO_NUM_17   /* Status LED */
#define ADC_LIPO_GPIO       GPIO_NUM_18   /* LiPo voltage monitor */
#define ADC_12V_GPIO        GPIO_NUM_19   /* 12V rail voltage monitor */
#define LDO_EN_GPIO         GPIO_NUM_27   /* 3.3V LDO enable (power gating) */
#define BUZZER_EN_GPIO      GPIO_NUM_28   /* Buzzer power gate */

/* ======================== SENSOR I2C ADDRESSES ======================== */

#define SHT40_CHAMBER_ADDR  0x44    /* Chamber SHT40 (default addr) */
#define SHT40_SUBSTRATE_ADDR 0x45   /* Substrate SHT40 (alt addr) */
#define SCD41_ADDR           0x62   /* CO2 sensor */
#define TSL2591_ADDR         0x29   /* Light sensor */
#define SSD1306_ADDR         0x3C   /* OLED display */

/* ======================== SHT40 COMMANDS ======================== */

#define SHT40_CMD_MEASURE_HEATER_OFF   0xFD   /* High-precision, no heater */
#define SHT40_CMD_MEASURE_HEATER_LOW   0x39   /* Measure with heater 200mW @1s */
#define SHT40_CMD_MEASURE_HEATER_MED   0x32   /* Measure with heater 200mW @0.1s */
#define SHT40_CMD_MEASURE_HEATER_HIGH  0x2F   /* Measure with heater 110mW @1s */
#define SHT40_CMD_SOFT_RESET           0x94

/* ======================== SCD41 COMMANDS ======================== */

#define SCD41_CMD_START_PERIODIC        0x21B1
#define SCD41_CMD_READ_MEASUREMENT      0xEC05
#define SCD41_CMD_STOP_PERIODIC          0x3F86
#define SCD41_CMD_PERFORM_FACTORY_RESET 0x3632
#define SCD41_CMD_FORCE_RECALIBRATION   0x362F
#define SCD41_CMD_SET_TEMPERATURE_OFFSET 0x241D
#define SCD41_CMD_SET_PRESSURE           0xE000
#define SCD41_CMD_PERFORM_SELF_TEST     0x3639
#define SCD41_CMD_GET_SERIAL             0x3682
#define SCD41_CMD_READ_DATA_READY        0xE4B8

/* ======================== TSL2591 COMMANDS ======================== */

#define TSL2591_CMD_ENABLE           0x00
#define TSL2591_CMD_CONTROL         0x01
#define TSL2591_CMD_THRESHHOLDL     0x04
#define TSL2591_CMD_THRESHHOLDH     0x05
#define TSL2591_CMD_CLEAR_INT       0xE7
#define TSL2591_CMD_TEST            0x07
#define TSL2591_CMD_ID              0x12
#define TSL2591_CMD_C0DATAL        0x14
#define TSL2591_CMD_C0DATAH        0x15
#define TSL2591_CMD_C1DATAL        0x16
#define TSL2591_CMD_C1DATAH        0x17

/* TSL2591 Gain Values */
#define TSL2591_GAIN_LOW            0x00    /* 1x */
#define TSL2591_GAIN_MED           0x10    /* 25x */
#define TSL2591_GAIN_HIGH           0x20    /* 428x */
#define TSL2591_GAIN_MAX            0x30    /* 9876x */

/* TSL2591 Integration Time */
#define TSL2591_INTEGRATIONTIME_100MS  0x00
#define TSL2591_INTEGRATIONTIME_200MS  0x01
#define TSL2591_INTEGRATIONTIME_300MS  0x02
#define TSL2591_INTEGRATIONTIME_400MS  0x03
#define TSL2591_INTEGRATIONTIME_500MS  0x04
#define TSL2591_INTEGRATIONTIME_600MS  0x05

/* ======================== GROWTH PHASES ======================== */

typedef enum {
    PHASE_COLONIZATION = 0,
    PHASE_PINNING      = 1,
    PHASE_FRUITING     = 2,
    PHASE_HARVEST      = 3,
    PHASE_MANUAL       = 4,  /* User override, no auto-advance */
    PHASE_COUNT        = 5
} growth_phase_t;

typedef enum {
    ACTUATOR_HUMIDIFIER = 0,
    ACTUATOR_HEATER     = 1,
    ACTUATOR_FAN        = 2,
    ACTUATOR_LIGHT      = 3,
    ACTUATOR_COUNT      = 4
} actuator_id_t;

/* ======================== DATA STRUCTURES ======================== */

typedef struct {
    float temp_c;           /* Temperature in °C */
    float rh_pct;           /* Relative humidity in % */
    bool  valid;            /* CRC passed */
    bool  heater_active;    /* Internal heater status */
} sht40_reading_t;

typedef struct {
    uint16_t co2_ppm;       /* CO2 in ppm */
    float    temp_c;        /* Temperature in °C */
    float    rh_pct;        /* Relative humidity in % */
    bool     valid;         /* Data ready flag */
} scd41_reading_t;

typedef struct {
    float    lux;           /* Computed lux value */
    uint16_t ch0;           /* Channel 0 raw (visible + IR) */
    uint16_t ch1;           /* Channel 1 raw (IR) */
    bool     valid;         /* Sensor ID verified */
} tsl2591_reading_t;

typedef struct {
    float temp_c;           /* Temperature in °C */
    bool  valid;            /* CRC passed */
} ds18b20_reading_t;

typedef struct {
    /* PID gains */
    float kp;
    float ki;
    float kd;
    /* State */
    float integral;
    float prev_error;
    float derivative_filtered;
    /* Limits */
    float output_min;       /* 0% */
    float output_max;       /* 100% (or 80% for fan safety) */
    float integral_max;     /* Anti-windup limit */
    /* Output */
    float output_pct;       /* Current PID output 0-100% */
} pid_controller_t;

typedef struct {
    /* Chamber sensors */
    sht40_reading_t  chamber;       /* Chamber air (SHT40 0x44) */
    sht40_reading_t  substrate;     /* Substrate surface (SHT40 0x45) */
    scd41_reading_t  co2;           /* CO2 sensor (SCD41) */
    tsl2591_reading_t light;        /* Light sensor (TSL2591) */
    ds18b20_reading_t deep_temp_1;  /* Substrate deep 3cm (DS18B20) */
    ds18b20_reading_t deep_temp_2;  /* Substrate deep 7cm (DS18B20) */

    /* Power monitoring */
    float lipo_v;                   /* LiPo voltage */
    float usb_v;                    /* USB voltage */
    float rail_12v;                 /* 12V rail voltage */

    /* Computed values */
    float dew_point_c;             /* Calculated dew point */
    float absolute_humidity_gm3;   /* g/m³ */
    bool  usb_present;              /* USB-C connected */
    bool  lipo_charging;            /* TP4056 charging */
} sensor_data_t;

typedef struct {
    /* Phase parameters */
    growth_phase_t phase;
    float temp_setpoint;        /* °C */
    float rh_setpoint;          /* %RH */
    float co2_max_ppm;          /* ppm */
    float light_pct;            /* 0-100% */
    uint16_t light_on_hours;    /* Hours of light per day */
    uint16_t phase_days;         /* Configured duration in days */
    uint16_t phase_day;          /* Current day in phase */
    bool    auto_advance;        /* Auto-transition to next phase */

    /* PID controllers */
    pid_controller_t pid_humidity;
    pid_controller_t pid_temperature;
    pid_controller_t pid_co2;

    /* Actuator outputs (0-100%) */
    float actuator_output[ACTUATOR_COUNT];

    /* Manual overrides (0 = no override) */
    float manual_override[ACTUATOR_COUNT];
    int   override_timeout_s;     /* Auto-clear override after N seconds */

    /* Timing */
    uint32_t sensor_interval_s;   /* How often to read sensors */
    uint32_t mqtt_interval_s;     /* How often to publish MQTT */
    uint32_t pid_interval_s;      /* PID update rate */
    uint32_t oled_update_s;       /* OLED refresh rate */

    /* WiFi/MQTT */
    char    wifi_ssid[64];
    char    wifi_pass[64];
    char    mqtt_broker[128];
    uint16_t mqtt_port;
    char    device_id[32];
} system_config_t;

typedef struct {
    /* Sensor readings */
    sensor_data_t sensors;

    /* System config */
    system_config_t config;

    /* Runtime state */
    uint32_t uptime_s;               /* Seconds since boot */
    uint32_t last_sensor_read_ms;    /* Last sensor read timestamp */
    uint32_t last_mqtt_publish_ms;   /* Last MQTT publish timestamp */
    uint32_t last_pid_update_ms;     /* Last PID update timestamp */
    uint32_t last_oled_update_ms;    /* Last OLED update timestamp */
    bool     scd41_warmed_up;        /* SCD41 requires 60s warm-up */
    bool     wifi_connected;
    bool     mqtt_connected;
    bool     oled_present;
    uint16_t error_flags;            /* Bitmask of errors */
} system_state_t;

/* Error flags */
#define ERR_SHT40_CHAMBER       (1 << 0)
#define ERR_SHT40_SUBSTRATE     (1 << 1)
#define ERR_SCD41               (1 << 2)
#define ERR_TSL2591             (1 << 3)
#define ERR_DS18B20_1           (1 << 4)
#define ERR_DS18B20_2           (1 << 5)
#define ERR_OLED                (1 << 6)
#define ERR_WIFI                (1 << 7)
#define ERR_MQTT               (1 << 8)
#define ERR_OVERTEMP            (1 << 9)  /* Chamber > 40°C safety cutoff */
#define ERR_LIPO_LOW            (1 << 10) /* LiPo < 3.3V */

/* ======================== SPECIES PRESETS ======================== */

typedef struct {
    const char *name;          /* Species common name */
    /* Colonization phase */
    float col_temp;
    float col_rh;
    uint16_t col_co2_max;
    uint8_t col_light_pct;
    uint16_t col_days;
    /* Pinning phase */
    float pin_temp;
    float pin_rh;
    uint16_t pin_co2_max;
    uint8_t pin_light_pct;
    uint16_t pin_days;
    /* Fruiting phase */
    float frt_temp;
    float frt_rh;
    uint16_t frt_co2_max;
    uint8_t frt_light_pct;
    uint16_t frt_days;
    /* Harvest phase */
    float hrv_temp;
    float hrv_rh;
    uint16_t hrv_co2_max;
    uint8_t hrv_light_pct;
    uint16_t hrv_days;
} species_preset_t;

/* ======================== FUNCTION PROTOTYPES ======================== */

/* I2C bus */
esp_err_t i2c_bus_init(void);

/* SHT40 driver */
esp_err_t sht40_init(uint8_t addr);
esp_err_t sht40_read(uint8_t addr, sht40_reading_t *reading);
esp_err_t sht40_heater(uint8_t addr, bool enable);

/* SCD41 driver */
esp_err_t scd41_init(void);
esp_err_t scd41_start_periodic(void);
esp_err_t scd41_stop_periodic(void);
esp_err_t scd41_read_measurement(scd41_reading_t *reading);
esp_err_t scd41_force_recalibration(uint16_t target_ppm);
esp_err_t scd41_factory_reset(void);
bool       scd41_data_ready(void);

/* TSL2591 driver */
esp_err_t tsl2591_init(void);
esp_err_t tsl2591_read(tsl2591_reading_t *reading);
esp_err_t tsl2591_set_gain(uint8_t gain);
esp_err_t tsl2591_set_integration(uint8_t integration);

/* DS18B20 driver */
esp_err_t ds18b20_init(void);
esp_err_t ds18b20_read_all(ds18b20_reading_t *readings, uint8_t max_count);
void      ds18b20_power_on(void);
void      ds18b20_power_off(void);

/* SSD1306 OLED driver */
esp_err_t oled_init(void);
esp_err_t oled_clear(void);
esp_err_t oled_draw_status(const sensor_data_t *sensors, const system_config_t *cfg);
esp_err_t oled_draw_menu(const char *title, const char **items, uint8_t count, uint8_t selected);
esp_err_t oled_draw_phase(const char *phase_name, uint16_t day, uint16_t total);

/* PID controller */
void     pid_init(pid_controller_t *pid, float kp, float ki, float kd, float out_min, float out_max);
float    pid_compute(pid_controller_t *pid, float setpoint, float measurement, float dt_s);
void     pid_reset(pid_controller_t *pid);
void     pid_set_gains(pid_controller_t *pid, float kp, float ki, float kd);

/* Actuator control */
esp_err_t actuators_init(void);
void      actuators_set_pwm(actuator_id_t id, float percent);
void      actuators_all_off(void);
void      actuators_emergency_off(void);  /* Safety: all off + relay open */

/* Rotary encoder */
esp_err_t encoder_init(void);
int8_t    encoder_get_delta(void);    /* Returns +1, -1, or 0 */
bool      encoder_get_press(void);    /* Returns true on button press */

/* WS2812 status LED */
esp_err_t status_led_init(void);
void      status_led_set_color(uint8_t r, uint8_t g, uint8_t b);
void      status_led_phase_indicator(growth_phase_t phase);

/* Power monitoring */
esp_err_t power_monitor_init(void);
float     power_read_lipo_v(void);
float     power_read_12v_rail(void);
bool      power_usb_present(void);

/* Buzzer */
esp_err_t buzzer_init(void);
void      buzzer_beep(uint16_t freq_hz, uint16_t duration_ms);
void      buzzer_phase_change_alert(void);
void      buzzer_error_alert(void);

/* Growth phase scheduler */
void     scheduler_init(void);
void     scheduler_apply_phase(system_config_t *cfg, growth_phase_t phase);
void     scheduler_advance(system_config_t *cfg);
bool     scheduler_check_auto_advance(const system_state_t *state, const system_config_t *cfg);

/* WiFi + MQTT */
esp_err_t wifi_init(const char *ssid, const char *pass);
esp_err_t mqtt_init(const char *broker, uint16_t port, const char *device_id);
esp_err_t mqtt_publish_sensors(const sensor_data_t *sensors, const system_config_t *cfg);
esp_err_t mqtt_publish_status(const system_state_t *state, const system_config_t *cfg);
void      mqtt_subscribe_commands(system_config_t *cfg);

/* BLE dashboard */
esp_err_t ble_init(const char *device_name);
void      ble_update_sensors(const sensor_data_t *sensors);
void      ble_update_actuators(const system_config_t *cfg);

/* NVS storage */
esp_err_t config_load(system_config_t *cfg);
esp_err_t config_save(const system_config_t *cfg);
esp_err_t config_factory_reset(void);

/* Debug serial interface */
esp_err_t debug_uart_init(void);
void      debug_process_command(const char *cmd, system_state_t *state, system_config_t *cfg);

#endif /* MAIN_H */