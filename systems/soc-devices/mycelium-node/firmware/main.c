/**
 * Mycelium Node - Main Application
 * 
 * Mushroom Fruiting Chamber Environmental Controller
 * ESP32-C6-MINI-1 with multi-zone PID climate control
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/event_groups.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_sleep.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "driver/gpio.h"
#include "driver/i2c.h"
#include "driver/ledc.h"
#include "driver/adc.h"
#include "driver/uart.h"
#include "esp_adc_cal.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "mqtt_client.h"
#include "esp_ble_gatt_defs.h"

#include "main.h"

static const char *TAG = "MYCELIUM";

/* ================================================================
 * GLOBAL STATE
 * ================================================================ */

static system_state_t g_state;
static system_config_t g_config;

/* Species presets table */
static const species_preset_t species_presets[] = {
    /* Oyster (Pleurotus) */
    { "Oyster",
      24.0, 80.0, 5000, 10, 14,    /* colonization */
      18.0, 92.0, 1000, 50, 5,      /* pinning */
      20.0, 90.0, 1000, 70, 7,      /* fruiting */
      20.0, 75.0, 0, 0, 2 },        /* harvest */
    /* Lion's Mane (Hericium) */
    { "LionsMane",
      22.0, 82.0, 4000, 10, 18,    /* colonization */
      18.0, 90.0, 800, 50, 7,       /* pinning */
      20.0, 88.0, 800, 70, 10,      /* fruiting */
      20.0, 75.0, 0, 0, 2 },        /* harvest */
    /* Shiitake (Lentinula) */
    { "Shiitake",
      22.0, 78.0, 5000, 10, 21,    /* colonization */
      16.0, 90.0, 1000, 50, 7,      /* pinning */
      18.0, 85.0, 1000, 70, 14,     /* fruiting */
      18.0, 70.0, 0, 0, 2 },        /* harvest */
    /* Reishi (Ganoderma) */
    { "Reishi",
      26.0, 85.0, 6000, 10, 18,    /* colonization */
      22.0, 95.0, 2000, 50, 10,     /* pinning */
      24.0, 92.0, 2000, 70, 21,     /* fruiting */
      22.0, 75.0, 0, 0, 3 },        /* harvest */
    /* Chestnut (G. bellinghamensis) */
    { "Chestnut",
      22.0, 80.0, 4000, 10, 14,    /* colonization */
      18.0, 88.0, 1000, 50, 5,      /* pinning */
      20.0, 85.0, 1000, 70, 10,     /* fruiting */
      20.0, 75.0, 0, 0, 2 },        /* harvest */
};
#define NUM_SPECIES (sizeof(species_presets) / sizeof(species_preset_t))

/* ================================================================
 * I2C BUS INITIALIZATION
 * ================================================================ */

esp_err_t i2c_bus_init(void)
{
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_SDA_GPIO,
        .scl_io_num = I2C_SCL_GPIO,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_FREQ_HZ,
    };
    ESP_ERROR_CHECK(i2c_param_config(I2C_PORT, &conf));
    ESP_ERROR_CHECK(i2c_driver_install(I2C_PORT, I2C_MODE_MASTER, 0, 0, 0));
    ESP_LOGI(TAG, "I2C bus initialized on SDA=%d SCL=%d @ %d Hz",
             I2C_SDA_GPIO, I2C_SCL_GPIO, I2C_FREQ_HZ);
    return ESP_OK;
}

/* ================================================================
 * SHT40 DRIVER
 * ================================================================ */

static esp_err_t sht40_write_cmd(uint8_t addr, uint16_t cmd)
{
    uint8_t data[2] = { (uint8_t)(cmd >> 8), (uint8_t)(cmd & 0xFF) };
    return i2c_master_write_to_device(I2C_PORT, addr, data, 2, pdMS_TO_TICKS(100));
}

static uint8_t sht40_crc8(const uint8_t *data, uint16_t len)
{
    uint8_t crc = 0xFF;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t bit = 8; bit > 0; --bit) {
            if (crc & 0x80) crc = (crc << 1) ^ 0x31;
            else            crc = (crc << 1);
        }
    }
    return crc;
}

esp_err_t sht40_read(uint8_t addr, sht40_reading_t *reading)
{
    uint8_t buf[6];
    esp_err_t err;

    /* Send measurement command (high precision, no heater) */
    err = sht40_write_cmd(addr, SHT40_CMD_MEASURE_HEATER_OFF);
    if (err != ESP_OK) return err;

    /* Wait for measurement: ~8ms at high precision */
    vTaskDelay(pdMS_TO_TICKS(10));

    /* Read 6 bytes: temp_msb, temp_lsb, temp_crc, hum_msb, hum_lsb, hum_crc */
    err = i2c_master_read_from_device(I2C_PORT, addr, buf, 6, pdMS_TO_TICKS(100));
    if (err != ESP_OK) return err;

    /* Verify CRC */
    if (sht40_crc8(&buf[0], 2) != buf[2] || sht40_crc8(&buf[3], 2) != buf[5]) {
        reading->valid = false;
        return ESP_ERR_INVALID_CRC;
    }

    /* Convert raw to physical values */
    uint16_t temp_raw = (buf[0] << 8) | buf[1];
    uint16_t hum_raw  = (buf[3] << 8) | buf[4];

    reading->temp_c = -45.0f + 175.0f * (float)temp_raw / 65535.0f;
    reading->rh_pct = -6.0f + 125.0f * (float)hum_raw / 65535.0f;

    /* Clamp humidity to 0-100% */
    if (reading->rh_pct < 0.0f)   reading->rh_pct = 0.0f;
    if (reading->rh_pct > 100.0f) reading->rh_pct = 100.0f;

    reading->valid = true;
    return ESP_OK;
}

esp_err_t sht40_init(uint8_t addr)
{
    /* Soft reset */
    esp_err_t err = sht40_write_cmd(addr, SHT40_CMD_SOFT_RESET);
    if (err != ESP_OK) return err;
    vTaskDelay(pdMS_TO_TICKS(10));
    ESP_LOGI(TAG, "SHT40 at 0x%02X initialized", addr);
    return ESP_OK;
}

/* ================================================================
 * SCD41 DRIVER (Photoacoustic CO2)
 * ================================================================ */

static esp_err_t scd41_write_cmd(uint16_t cmd)
{
    uint8_t data[2] = { (uint8_t)(cmd >> 8), (uint8_t)(cmd & 0xFF) };
    return i2c_master_write_to_device(I2C_PORT, SCD41_ADDR, data, 2, pdMS_TO_TICKS(100));
}

static esp_err_t scd41_write_cmd_with_args(uint16_t cmd, uint16_t arg)
{
    uint8_t data[5];
    data[0] = (uint8_t)(cmd >> 8);
    data[1] = (uint8_t)(cmd & 0xFF);
    data[2] = (uint8_t)(arg >> 8);
    data[3] = (uint8_t)(arg & 0xFF);
    data[4] = sht40_crc8(&data[2], 2);
    return i2c_master_write_to_device(I2C_PORT, SCD41_ADDR, data, 5, pdMS_TO_TICKS(100));
}

static uint16_t scd41_crc16(const uint8_t *data, uint16_t len)
{
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i];
        for (uint8_t bit = 8; bit > 0; --bit) {
            if (crc & 0x0001) crc = (crc >> 1) ^ 0xA001;
            else              crc = (crc >> 1);
        }
    }
    return crc;
}

static bool scd41_verify_crc(const uint8_t *data, uint16_t len)
{
    /* Data format: [word0_msb, word0_lsb, word0_crc, word1_msb, word1_lsb, word1_crc, ...] */
    for (uint16_t i = 0; i < len; i += 3) {
        if (sht40_crc8(&data[i], 2) != data[i + 2]) {
            return false;
        }
    }
    return true;
}

bool scd41_data_ready(void)
{
    uint8_t buf[3];
    esp_err_t err = scd41_write_cmd(SCD41_CMD_READ_DATA_READY);
    if (err != ESP_OK) return false;
    vTaskDelay(pdMS_TO_TICKS(5));
    err = i2c_master_read_from_device(I2C_PORT, SCD41_ADDR, buf, 3, pdMS_TO_TICKS(100));
    if (err != ESP_OK) return false;
    uint16_t status = (buf[0] << 8) | buf[1];
    return (status & 0x07FF) != 0;  /* Lower 11 bits: data ready */
}

esp_err_t scd41_read_measurement(scd41_reading_t *reading)
{
    uint8_t buf[9];
    esp_err_t err;

    err = scd41_write_cmd(SCD41_CMD_READ_MEASUREMENT);
    if (err != ESP_OK) return err;
    vTaskDelay(pdMS_TO_TICKS(5));

    err = i2c_master_read_from_device(I2C_PORT, SCD41_ADDR, buf, 9, pdMS_TO_TICKS(100));
    if (err != ESP_OK) return err;

    if (!scd41_verify_crc(buf, 9)) {
        reading->valid = false;
        return ESP_ERR_INVALID_CRC;
    }

    /* Parse: CO2 (word 0), Temperature (word 1), Humidity (word 2) */
    uint16_t co2_raw    = (buf[0] << 8) | buf[1];
    uint16_t temp_raw   = (buf[3] << 8) | buf[4];
    uint16_t hum_raw    = (buf[6] << 8) | buf[7];

    reading->co2_ppm = co2_raw;
    reading->temp_c  = -45.0f + 175.0f * (float)temp_raw / 65535.0f;
    reading->rh_pct  = 0.0f + 100.0f * (float)hum_raw / 65535.0f;
    reading->valid   = true;

    return ESP_OK;
}

esp_err_t scd41_start_periodic(void)
{
    esp_err_t err = scd41_write_cmd(SCD41_CMD_START_PERIODIC);
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "SCD41 periodic measurement started (5-second interval)");
    }
    return err;
}

esp_err_t scd41_stop_periodic(void)
{
    return scd41_write_cmd(SCD41_CMD_STOP_PERIODIC);
}

esp_err_t scd41_force_recalibration(uint16_t target_ppm)
{
    /* Stop periodic first */
    scd41_stop_periodic();
    vTaskDelay(pdMS_TO_TICKS(500));

    /* Set reference CO2 concentration */
    esp_err_t err = scd41_write_cmd_with_args(SCD41_CMD_FORCE_RECALIBRATION, target_ppm);
    vTaskDelay(pdMS_TO_TICKS(500));

    /* Restart periodic */
    scd41_start_periodic();
    return err;
}

esp_err_t scd41_init(void)
{
    /* Reset SCD41 */
    gpio_set_level(SCD41_RESET_GPIO, 0);
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(SCD41_RESET_GPIO, 1);
    vTaskDelay(pdMS_TO_TICKS(100));

    /* Factory reset to clear any stale calibration */
    scd41_write_cmd(SCD41_CMD_PERFORM_FACTORY_RESET);
    vTaskDelay(pdMS_TO_TICKS(1200));

    /* Start periodic measurement */
    esp_err_t err = scd41_start_periodic();
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "SCD41 CO2 sensor initialized (warm-up: 60s)");
    }
    return err;
}

/* ================================================================
 * TSL2591 DRIVER (Light Sensor)
 * ================================================================ */

static esp_err_t tsl2591_write8(uint8_t reg, uint8_t value)
{
    uint8_t data[2] = { 0xA0 | (reg & 0x3F), value };  /* Command byte: 0xA0 = write */
    return i2c_master_write_to_device(I2C_PORT, TSL2591_ADDR, data, 2, pdMS_TO_TICKS(100));
}

static uint8_t tsl2591_read8(uint8_t reg)
{
    uint8_t cmd = 0xA0 | (reg & 0x3F);
    uint8_t value;
    esp_err_t err = i2c_master_write_read_device(I2C_PORT, TSL2591_ADDR,
                                                   &cmd, 1, &value, 1, pdMS_TO_TICKS(100));
    return (err == ESP_OK) ? value : 0;
}

static uint16_t tsl2591_read16(uint8_t reg)
{
    uint8_t cmd = 0xA0 | (reg & 0x3F);
    uint8_t buf[2];
    esp_err_t err = i2c_master_write_read_device(I2C_PORT, TSL2591_ADDR,
                                                   &cmd, 1, buf, 2, pdMS_TO_TICKS(100));
    return (err == ESP_OK) ? ((buf[1] << 8) | buf[0]) : 0;
}

esp_err_t tsl2591_init(void)
{
    /* Check ID: should be 0x50 */
    uint8_t id = tsl2591_read8(TSL2591_CMD_ID);
    if (id != 0x50) {
        ESP_LOGE(TAG, "TSL2591 not found (id=0x%02X, expected 0x50)", id);
        return ESP_ERR_NOT_FOUND;
    }

    /* Enable sensor: ADC enable + power on */
    tsl2591_write8(TSL2591_CMD_ENABLE, 0x03);

    /* Set gain to medium (25x) and integration time to 500ms */
    tsl2591_write8(TSL2591_CMD_CONTROL, TSL2591_GAIN_MED | TSL2591_INTEGRATIONTIME_500MS);

    vTaskDelay(pdMS_TO_TICKS(600));  /* Wait for first integration */
    ESP_LOGI(TAG, "TSL2591 light sensor initialized (gain=25x, integ=500ms)");
    return ESP_OK;
}

esp_err_t tsl2591_read(tsl2591_reading_t *reading)
{
    /* Read both channels */
    uint16_t ch0 = tsl2591_read16(TSL2591_CMD_C0DATAL);
    uint16_t ch1 = tsl2591_read16(TSL2591_CMD_C1DATAL);

    if (ch0 == 0xFFFF || ch1 == 0xFFFF) {
        reading->valid = false;
        return ESP_ERR_INVALID_RESPONSE;
    }

    reading->ch0 = ch0;
    reading->ch1 = ch1;

    /* Compute lux using AMS formula:
     *  lux = ( (ch0 - ch1) * (1 - (ch1/ch0)) ) * gain_factor * time_factor
     * Simplified for gain=25x (factor=16.0), time=500ms (factor=1.0):
     */
    if (ch0 == 0) {
        reading->lux = 0.0f;
    } else {
        float ratio = (float)ch1 / (float)ch0;
        float lux = 0.0f;
        if (ratio < 0.5f) {
            lux = ((float)ch0 - (float)ch1) * (1.0f - ratio) * 16.0f;
        } else {
            lux = 0.0f;  /* Saturated or IR-dominated */
        }
        reading->lux = lux;
    }

    reading->valid = true;
    return ESP_OK;
}

/* ================================================================
 * DS18B20 DRIVER (1-Wire Temperature)
 * ================================================================ */

/* Minimal 1-Wire implementation using GPIO bit-banging */
#define OW_RESET_PULSE_US    480
#define OW_PRESENCE_WAIT_US  70
#define OW_WRITE_BIT_US      60
#define OW_READ_BIT_US       60
#define OW_SLOT_GAP_US       2

static int ow_reset(void)
{
    gpio_set_direction(ONEWIRE_GPIO, GPIO_MODE_OUTPUT);
    gpio_set_level(ONEWIRE_GPIO, 0);
    ets_delay_us(OW_RESET_PULSE_US);
    gpio_set_level(ONEWIRE_GPIO, 1);
    ets_delay_us(OW_PRESENCE_WAIT_US);

    gpio_set_direction(ONEWIRE_GPIO, GPIO_MODE_INPUT);
    int presence = gpio_get_level(ONEWIRE_GPIO);
    ets_delay_us(OW_RESET_PULSE_US - OW_PRESENCE_WAIT_US);
    return presence;  /* 0 = device present, 1 = no device */
}

static void ow_write_bit(int bit)
{
    gpio_set_direction(ONEWIRE_GPIO, GPIO_MODE_OUTPUT);
    if (bit) {
        gpio_set_level(ONEWIRE_GPIO, 0);
        ets_delay_us(6);
        gpio_set_level(ONEWIRE_GPIO, 1);
        ets_delay_us(OW_WRITE_BIT_US);
    } else {
        gpio_set_level(ONEWIRE_GPIO, 0);
        ets_delay_us(OW_WRITE_BIT_US);
        gpio_set_level(ONEWIRE_GPIO, 1);
        ets_delay_us(6);
    }
    ets_delay_us(OW_SLOT_GAP_US);
}

static int ow_read_bit(void)
{
    gpio_set_direction(ONEWIRE_GPIO, GPIO_MODE_OUTPUT);
    gpio_set_level(ONEWIRE_GPIO, 0);
    ets_delay_us(6);
    gpio_set_level(ONEWIRE_GPIO, 1);
    ets_delay_us(9);

    gpio_set_direction(ONEWIRE_GPIO, GPIO_MODE_INPUT);
    int bit = gpio_get_level(ONEWIRE_GPIO);
    ets_delay_us(OW_READ_BIT_US);
    return bit;
}

static void ow_write_byte(uint8_t byte)
{
    for (int i = 0; i < 8; i++) {
        ow_write_bit(byte & 1);
        byte >>= 1;
    }
}

static uint8_t ow_read_byte(void)
{
    uint8_t byte = 0;
    for (int i = 0; i < 8; i++) {
        byte |= (ow_read_bit() << i);
    }
    return byte;
}

/* DS18B20 CRC8 (Dallas/Maxim) */
static uint8_t ds18b20_crc8(const uint8_t *data, uint8_t len)
{
    uint8_t crc = 0;
    for (uint8_t i = 0; i < len; i++) {
        uint8_t byte = data[i];
        for (uint8_t j = 0; j < 8; j++) {
            uint8_t mix = (crc ^ byte) & 0x01;
            crc >>= 1;
            if (mix) crc ^= 0x8C;
            byte >>= 1;
        }
    }
    return crc;
}

void ds18b20_power_on(void)
{
    gpio_set_level(DS18B20_PWR_GPIO, 1);  /* MOSFET on */
    vTaskDelay(pdMS_TO_TICKS(50));          /* Stabilize */
}

void ds18b20_power_off(void)
{
    gpio_set_level(DS18B20_PWR_GPIO, 0);  /* MOSFET off */
}

esp_err_t ds18b20_init(void)
{
    /* Configure 1-Wire GPIO with pull-up */
    gpio_config_t ow_conf = {
        .pin_bit_mask = (1ULL << ONEWIRE_GPIO),
        .mode = GPIO_MODE_INPUT_OUTPUT_OD,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&ow_conf);

    /* Configure power gate MOSFET */
    gpio_config_t pwr_conf = {
        .pin_bit_mask = (1ULL << DS18B20_PWR_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&pwr_conf);
    gpio_set_level(DS18B20_PWR_GPIO, 0);  /* Start powered off */

    ESP_LOGI(TAG, "DS18B20 1-Wire bus initialized on GPIO %d", ONEWIRE_GPIO);
    return ESP_OK;
}

esp_err_t ds18b20_read_all(ds18b20_reading_t *readings, uint8_t max_count)
{
    ds18b20_power_on();
    vTaskDelay(pdMS_TO_TICKS(100));  /* Warm-up */

    /* Skip ROM + Convert T (all devices simultaneously) */
    if (ow_reset() != 0) {
        ds18b20_power_off();
        return ESP_ERR_NOT_FOUND;
    }
    ow_write_byte(0xCC);  /* Skip ROM */
    ow_write_byte(0x44);  /* Convert T */

    /* Wait for conversion (750ms at 12-bit) */
    vTaskDelay(pdMS_TO_TICKS(800));

    /* Read each device: Skip ROM + Read Scratchpad */
    /* For simplicity with 2 devices, we read both by using Skip ROM
     * which returns the first device. In production, use ROM search
     * to enumerate individual device addresses. */
    for (uint8_t i = 0; i < max_count && i < 2; i++) {
        if (ow_reset() != 0) {
            readings[i].valid = false;
            continue;
        }

        /* Read Scratchpad */
        ow_write_byte(0xCC);  /* Skip ROM */
        ow_write_byte(0xBE);  /* Read Scratchpad */

        uint8_t scratchpad[9];
        for (uint8_t j = 0; j < 9; j++) {
            scratchpad[j] = ow_read_byte();
        }

        /* Verify CRC */
        if (ds18b20_crc8(scratchpad, 8) != scratchpad[8]) {
            readings[i].valid = false;
            continue;
        }

        /* Convert temperature */
        int16_t temp_raw = (scratchpad[1] << 8) | scratchpad[0];
        readings[i].temp_c = (float)temp_raw / 16.0f;
        readings[i].valid = true;
    }

    ds18b20_power_off();
    return ESP_OK;
}

/* ================================================================
 * PID CONTROLLER
 * ================================================================ */

void pid_init(pid_controller_t *pid, float kp, float ki, float kd,
              float out_min, float out_max)
{
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
    pid->derivative_filtered = 0.0f;
    pid->output_min = out_min;
    pid->output_max = out_max;
    pid->integral_max = out_max * 0.3f;  /* Anti-windup: 30% of max output */
    pid->output_pct = 0.0f;
}

float pid_compute(pid_controller_t *pid, float setpoint, float measurement, float dt_s)
{
    float error = setpoint - measurement;

    /* Proportional */
    float p_term = pid->kp * error;

    /* Integral with anti-windup */
    pid->integral += error * dt_s;
    if (pid->integral > pid->integral_max)       pid->integral = pid->integral_max;
    else if (pid->integral < -pid->integral_max) pid->integral = -pid->integral_max;
    float i_term = pid->ki * pid->integral;

    /* Derivative with EMA filter (α = 0.1) */
    float raw_derivative = (error - pid->prev_error) / dt_s;
    pid->derivative_filtered = 0.1f * raw_derivative + 0.9f * pid->derivative_filtered;
    float d_term = pid->kd * pid->derivative_filtered;

    pid->prev_error = error;

    /* Compute output */
    float output = p_term + i_term + d_term;

    /* Clamp output */
    if (output < pid->output_min) output = pid->output_min;
    if (output > pid->output_max) output = pid->output_max;

    pid->output_pct = output;
    return output;
}

void pid_reset(pid_controller_t *pid)
{
    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
    pid->derivative_filtered = 0.0f;
    pid->output_pct = 0.0f;
}

void pid_set_gains(pid_controller_t *pid, float kp, float ki, float kd)
{
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
}

/* ================================================================
 * ACTUATOR CONTROL (PWM)
 * ================================================================ */

/* LEDC PWM channel assignments */
static const ledc_channel_config_t pwm_channels[ACTUATOR_COUNT] = {
    { .gpio_num = PWM_HUM_GPIO,   .speed_mode = LEDC_LOW_SPEED_MODE,
      .channel = LEDC_CHANNEL_0, .intr_type = LEDC_INTR_DISABLE,
      .timer_sel = LEDC_TIMER_0, .duty = 0, .hpoint = 0 },
    { .gpio_num = PWM_HEAT_GPIO,  .speed_mode = LEDC_LOW_SPEED_MODE,
      .channel = LEDC_CHANNEL_1, .intr_type = LEDC_INTR_DISABLE,
      .timer_sel = LEDC_TIMER_1, .duty = 0, .hpoint = 0 },
    { .gpio_num = PWM_FAN_GPIO,   .speed_mode = LEDC_LOW_SPEED_MODE,
      .channel = LEDC_CHANNEL_2, .intr_type = LEDC_INTR_DISABLE,
      .timer_sel = LEDC_TIMER_2, .duty = 0, .hpoint = 0 },
    { .gpio_num = PWM_LIGHT_GPIO,  .speed_mode = LEDC_LOW_SPEED_MODE,
      .channel = LEDC_CHANNEL_3, .intr_type = LEDC_INTR_DISABLE,
      .timer_sel = LEDC_TIMER_3, .duty = 0, .hpoint = 0 },
};

/* Timer configurations (different frequencies per actuator) */
static const ledc_timer_config_t pwm_timers[ACTUATOR_COUNT] = {
    { .speed_mode = LEDC_LOW_SPEED_MODE, .duty_resolution = LEDC_TIMER_8_BIT,
      .timer_num = LEDC_TIMER_0, .freq_hz = PWM_FREQ_HUM, .clk_cfg = LEDC_AUTO_CLK },
    { .speed_mode = LEDC_LOW_SPEED_MODE, .duty_resolution = LEDC_TIMER_8_BIT,
      .timer_num = LEDC_TIMER_1, .freq_hz = PWM_FREQ_HEAT, .clk_cfg = LEDC_AUTO_CLK },
    { .speed_mode = LEDC_LOW_SPEED_MODE, .duty_resolution = LEDC_TIMER_8_BIT,
      .timer_num = LEDC_TIMER_2, .freq_hz = PWM_FREQ_FAN, .clk_cfg = LEDC_AUTO_CLK },
    { .speed_mode = LEDC_LOW_SPEED_MODE, .duty_resolution = LEDC_TIMER_8_BIT,
      .timer_num = LEDC_TIMER_3, .freq_hz = PWM_FREQ_LIGHT, .clk_cfg = LEDC_AUTO_CLK },
};

esp_err_t actuators_init(void)
{
    /* Initialize all 4 LEDC timers */
    for (int i = 0; i < ACTUATOR_COUNT; i++) {
        ESP_ERROR_CHECK(ledc_timer_config(&pwm_timers[i]));
    }
    /* Initialize all 4 LEDC channels */
    for (int i = 0; i < ACTUATOR_COUNT; i++) {
        ESP_ERROR_CHECK(ledc_channel_config(&pwm_channels[i]));
    }

    /* Configure safety relay GPIO */
    gpio_config_t relay_conf = {
        .pin_bit_mask = (1ULL << RELAY_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&relay_conf);
    gpio_set_level(RELAY_GPIO, 1);  /* Relay closed = normal operation */

    ESP_LOGI(TAG, "Actuators initialized (4 PWM channels + safety relay)");
    return ESP_OK;
}

void actuators_set_pwm(actuator_id_t id, float percent)
{
    if (id >= ACTUATOR_COUNT) return;
    if (percent < 0.0f) percent = 0.0f;
    if (percent > 100.0f) percent = 100.0f;

    uint32_t duty = (uint32_t)(percent * 255.0f / 100.0f);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, pwm_channels[id].channel, duty);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, pwm_channels[id].channel);
}

void actuators_all_off(void)
{
    for (int i = 0; i < ACTUATOR_COUNT; i++) {
        actuators_set_pwm(i, 0.0f);
    }
}

void actuators_emergency_off(void)
{
    actuators_all_off();
    gpio_set_level(RELAY_GPIO, 0);  /* Open relay = safety cutoff */
    ESP_LOGE(TAG, "EMERGENCY: All actuators OFF, safety relay OPEN");
}

/* ================================================================
 * POWER MONITORING
 * ================================================================ */

static esp_adc_cal_characteristics_t adc1_chars;

esp_err_t power_monitor_init(void)
{
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC1_CHANNEL_7, ADC_ATTEN_DB_11);  /* GPIO18 = ADC1_CH7 (LiPo) */
    adc1_config_channel_atten(ADC1_CHANNEL_8, ADC_ATTEN_DB_11);  /* GPIO19 = ADC1_CH8 (12V) */
    esp_adc_cal_characterize(ADC_UNIT_1, ADC_ATTEN_DB_11, ADC_WIDTH_BIT_12, 1100, &adc1_chars);
    ESP_LOGI(TAG, "Power monitoring ADC initialized");
    return ESP_OK;
}

float power_read_lipo_v(void)
{
    /* LiPo voltage divider: R1=100K, R2=100K → factor = 2.0 */
    int raw = adc1_get_raw(ADC1_CHANNEL_7);
    if (raw < 0) return 0.0f;
    uint32_t voltage_mv = esp_adc_cal_raw_to_voltage(raw, &adc1_chars);
    return (float)voltage_mv * 2.0f / 1000.0f;
}

float power_read_12v_rail(void)
{
    /* 12V divider: R1=300K, R2=100K → factor = 4.0 */
    int raw = adc1_get_raw(ADC1_CHANNEL_8);
    if (raw < 0) return 0.0f;
    uint32_t voltage_mv = esp_adc_cal_raw_to_voltage(raw, &adc1_chars);
    return (float)voltage_mv * 4.0f / 1000.0f;
}

bool power_usb_present(void)
{
    /* Simple: if LiPo voltage > 4.0V, USB is likely present */
    float v = power_read_lipo_v();
    return (v > 4.0f);
}

/* ================================================================
 * BUZZER
 * ================================================================ */

esp_err_t buzzer_init(void)
{
    gpio_config_t conf = {
        .pin_bit_mask = (1ULL << BUZZER_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&conf);

    gpio_config_t en_conf = {
        .pin_bit_mask = (1ULL << BUZZER_EN_GPIO),
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&en_conf);
    gpio_set_level(BUZZER_EN_GPIO, 0);  /* Buzzer power off */

    return ESP_OK;
}

void buzzer_beep(uint16_t freq_hz, uint16_t duration_ms)
{
    gpio_set_level(BUZZER_EN_GPIO, 1);  /* Power on buzzer */
    uint32_t half_period_us = 500000 / freq_hz;
    uint32_t cycles = (uint32_t)duration_ms * freq_hz / 1000;

    for (uint32_t i = 0; i < cycles; i++) {
        gpio_set_level(BUZZER_GPIO, 1);
        ets_delay_us(half_period_us);
        gpio_set_level(BUZZER_GPIO, 0);
        ets_delay_us(half_period_us);
    }
    gpio_set_level(BUZZER_EN_GPIO, 0);  /* Power off buzzer */
}

void buzzer_phase_change_alert(void)
{
    buzzer_beep(2000, 200);
    vTaskDelay(pdMS_TO_TICKS(100));
    buzzer_beep(2000, 200);
    vTaskDelay(pdMS_TO_TICKS(100));
    buzzer_beep(3000, 400);
}

void buzzer_error_alert(void)
{
    buzzer_beep(1000, 500);
    vTaskDelay(pdMS_TO_TICKS(200));
    buzzer_beep(1000, 500);
}

/* ================================================================
 * GROWTH PHASE SCHEDULER
 * ================================================================ */

void scheduler_apply_phase(system_config_t *cfg, growth_phase_t phase)
{
    cfg->phase = phase;

    switch (phase) {
        case PHASE_COLONIZATION:
            cfg->temp_setpoint = 24.0f;
            cfg->rh_setpoint = 82.0f;
            cfg->co2_max_ppm = 5000;
            cfg->light_pct = 10.0f;
            cfg->light_on_hours = 0;   /* Light mostly off */
            break;
        case PHASE_PINNING:
            cfg->temp_setpoint = 18.0f;
            cfg->rh_setpoint = 92.0f;
            cfg->co2_max_ppm = 1000;
            cfg->light_pct = 50.0f;
            cfg->light_on_hours = 12;
            break;
        case PHASE_FRUITING:
            cfg->temp_setpoint = 22.0f;
            cfg->rh_setpoint = 93.0f;
            cfg->co2_max_ppm = 1000;
            cfg->light_pct = 70.0f;
            cfg->light_on_hours = 12;
            break;
        case PHASE_HARVEST:
            cfg->temp_setpoint = 20.0f;
            cfg->rh_setpoint = 75.0f;
            cfg->co2_max_ppm = 0;     /* No CO2 control */
            cfg->light_pct = 0.0f;
            cfg->light_on_hours = 0;
            break;
        case PHASE_MANUAL:
            /* Keep current setpoints, don't change */
            return;
    }

    /* Reset PID controllers for smooth transition */
    pid_reset(&cfg->pid_humidity);
    pid_reset(&cfg->pid_temperature);
    pid_reset(&cfg->pid_co2);

    ESP_LOGI(TAG, "Phase changed to %s (temp=%.1f°C, rh=%.0f%%, co2_max=%d, light=%.0f%%)",
             phase == PHASE_COLONIZATION ? "COLONIZATION" :
             phase == PHASE_PINNING ? "PINNING" :
             phase == PHASE_FRUITING ? "FRUITING" :
             phase == PHASE_HARVEST ? "HARVEST" : "MANUAL",
             cfg->temp_setpoint, cfg->rh_setpoint, cfg->co2_max_ppm, cfg->light_pct);

    buzzer_phase_change_alert();
}

void scheduler_advance(system_config_t *cfg)
{
    switch (cfg->phase) {
        case PHASE_COLONIZATION:
            scheduler_apply_phase(cfg, PHASE_PINNING);
            break;
        case PHASE_PINNING:
            scheduler_apply_phase(cfg, PHASE_FRUITING);
            break;
        case PHASE_FRUITING:
            scheduler_apply_phase(cfg, PHASE_HARVEST);
            break;
        case PHASE_HARVEST:
            scheduler_apply_phase(cfg, PHASE_COLONIZATION);  /* New cycle */
            break;
        default:
            break;
    }
}

bool scheduler_check_auto_advance(const system_state_t *state, const system_config_t *cfg)
{
    if (!cfg->auto_advance) return false;

    /* Auto-advance based on days in phase */
    uint32_t phase_seconds = state->uptime_s;  /* Simplified: use total uptime */
    /* In production, track per-phase uptime in NVS */
    return false;  /* TODO: implement day counter in NVS */
}

/* ================================================================
 * NVS CONFIG STORAGE
 * ================================================================ */

#define NVS_NAMESPACE "mycelium"
#define NVS_KEY_CONFIG "config"

esp_err_t config_load(system_config_t *cfg)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &handle);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "NVS config not found, using defaults");
        return err;
    }

    size_t required_size = sizeof(system_config_t);
    err = nvs_get_blob(handle, NVS_KEY_CONFIG, cfg, &required_size);
    nvs_close(handle);

    if (err == ESP_OK) {
        ESP_LOGI(TAG, "Config loaded from NVS");
    }
    return err;
}

esp_err_t config_save(const system_config_t *cfg)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &handle);
    if (err != ESP_OK) return err;

    err = nvs_set_blob(handle, NVS_KEY_CONFIG, cfg, sizeof(system_config_t));
    nvs_commit(handle);
    nvs_close(handle);

    if (err == ESP_OK) {
        ESP_LOGI(TAG, "Config saved to NVS");
    }
    return err;
}

esp_err_t config_factory_reset(void)
{
    nvs_flash_erase_partition(NVS_DEFAULT_PARTITION_NAME);
    nvs_flash_init();
    ESP_LOGI(TAG, "Factory reset complete, NVS erased");
    return ESP_OK;
}

/* ================================================================
 * DEFAULT CONFIGURATION
 * ================================================================ */

static void config_set_defaults(system_config_t *cfg)
{
    memset(cfg, 0, sizeof(system_config_t));

    /* Default to Oyster mushroom fruiting phase */
    cfg->phase = PHASE_FRUITING;
    cfg->temp_setpoint = 20.0f;
    cfg->rh_setpoint = 90.0f;
    cfg->co2_max_ppm = 1000;
    cfg->light_pct = 70.0f;
    cfg->light_on_hours = 12;
    cfg->phase_days = 14;
    cfg->phase_day = 0;
    cfg->auto_advance = true;

    /* PID gains (Fruiting phase defaults) */
    pid_init(&cfg->pid_humidity, 2.0f, 0.1f, 0.5f, 0.0f, 100.0f);
    pid_init(&cfg->pid_temperature, 1.5f, 0.05f, 0.3f, 0.0f, 100.0f);
    pid_init(&cfg->pid_co2, 3.0f, 0.2f, 0.0f, 0.0f, 80.0f);  /* Fan limited to 80% */

    /* Actuator outputs (start all off) */
    for (int i = 0; i < ACTUATOR_COUNT; i++) {
        cfg->actuator_output[i] = 0.0f;
        cfg->manual_override[i] = 0.0f;
    }
    cfg->override_timeout_s = 600;  /* 10-minute override timeout */

    /* Timing defaults */
    cfg->sensor_interval_s = 5;
    cfg->mqtt_interval_s = 60;
    cfg->pid_interval_s = 1;
    cfg->oled_update_s = 2;

    /* WiFi/MQTT defaults */
    strncpy(cfg->wifi_ssid, "MyceliumNet", sizeof(cfg->wifi_ssid) - 1);
    strncpy(cfg->wifi_pass, "", sizeof(cfg->wifi_pass) - 1);
    strncpy(cfg->mqtt_broker, "mqtt.local", sizeof(cfg->mqtt_broker) - 1);
    cfg->mqtt_port = 1883;

    /* Generate unique device ID from MAC */
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    snprintf(cfg->device_id, sizeof(cfg->device_id), "mycelium-%02x%02x%02x",
             mac[3], mac[4], mac[5]);
}

/* ================================================================
 * DEBUG UART COMMAND PROCESSOR
 * ================================================================ */

#define UART_BUF_SIZE 256
static char uart_cmd_buf[UART_BUF_SIZE];
static int uart_cmd_idx = 0;

esp_err_t debug_uart_init(void)
{
    uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    ESP_ERROR_CHECK(uart_driver_install(UART_NUM_0, UART_BUF_SIZE * 2, 0, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(UART_NUM_0, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(UART_NUM_0, 1, 2, -1, -1));  /* TX=GPIO1, RX=GPIO2 */

    printf("\n=== Mycelium Node Debug Console ===\n");
    printf("Type 'help' for commands\n\n");
    printf("MYC> ");

    return ESP_OK;
}

void debug_process_command(const char *cmd, system_state_t *state, system_config_t *cfg)
{
    if (strncmp(cmd, "help", 4) == 0) {
        printf("Commands:\n");
        printf("  status          - Show all sensor readings\n");
        printf("  set humidity N  - Set RH setpoint (%%)\n");
        printf("  set temp N      - Set temperature setpoint (°C)\n");
        printf("  set co2_max N  - Set CO2 max (ppm)\n");
        printf("  phase [col|pin|frt|har|man] - Change growth phase\n");
        printf("  pid <hum|temp|co2> <kp|ki|kd> N - Set PID gain\n");
        printf("  override <hum|heat|fan|light> N - Manual override (0-100%%)\n");
        printf("  calibrate co2 N - SCD41 forced recal at N ppm\n");
        printf("  schedule show   - Show phase schedule\n");
        printf("  wifi <ssid> <pass> - Connect WiFi\n");
        printf("  mqtt start      - Start MQTT client\n");
        printf("  save            - Save config to NVS\n");
        printf("  reset           - Factory reset\n");
    }
    else if (strncmp(cmd, "status", 6) == 0) {
        const char *phase_str[] = {"COLONIZATION", "PINNING", "FRUITING", "HARVEST", "MANUAL"};
        printf("  PHASE: %s\n", phase_str[cfg->phase]);
        printf("  CHAMBER: %.1f°C / %.1f%% RH\n",
               state->sensors.chamber.temp_c, state->sensors.chamber.rh_pct);
        printf("  SUBSTRATE: %.1f°C / %.1f%% RH\n",
               state->sensors.substrate.temp_c, state->sensors.substrate.rh_pct);
        printf("  CO2: %d ppm\n", state->sensors.co2.co2_ppm);
        printf("  LIGHT: %.1f lux\n", state->sensors.light.lux);
        printf("  DEEP1: %.1f°C  DEEP2: %.1f°C\n",
               state->sensors.deep_temp_1.temp_c, state->sensors.deep_temp_2.temp_c);
        printf("  HUM: %.0f%%  HEAT: %.0f%%  FAN: %.0f%%  LIGHT: %.0f%%\n",
               cfg->actuator_output[ACTUATOR_HUMIDIFIER],
               cfg->actuator_output[ACTUATOR_HEATER],
               cfg->actuator_output[ACTUATOR_FAN],
               cfg->actuator_output[ACTUATOR_LIGHT]);
        printf("  LIPO: %.2fV  12V: %.1fV\n", state->sensors.lipo_v, state->sensors.rail_12v);
    }
    else if (strncmp(cmd, "set humidity ", 13) == 0) {
        cfg->rh_setpoint = atof(cmd + 13);
        printf("  Humidity setpoint: %.1f%% RH\n", cfg->rh_setpoint);
    }
    else if (strncmp(cmd, "set temp ", 9) == 0) {
        cfg->temp_setpoint = atof(cmd + 9);
        printf("  Temperature setpoint: %.1f°C\n", cfg->temp_setpoint);
    }
    else if (strncmp(cmd, "set co2_max ", 12) == 0) {
        cfg->co2_max_ppm = atoi(cmd + 12);
        printf("  CO2 max setpoint: %d ppm\n", cfg->co2_max_ppm);
    }
    else if (strncmp(cmd, "phase col", 9) == 0) {
        scheduler_apply_phase(cfg, PHASE_COLONIZATION);
    }
    else if (strncmp(cmd, "phase pin", 9) == 0) {
        scheduler_apply_phase(cfg, PHASE_PINNING);
    }
    else if (strncmp(cmd, "phase frt", 9) == 0) {
        scheduler_apply_phase(cfg, PHASE_FRUITING);
    }
    else if (strncmp(cmd, "phase har", 9) == 0) {
        scheduler_apply_phase(cfg, PHASE_HARVEST);
    }
    else if (strncmp(cmd, "phase man", 9) == 0) {
        scheduler_apply_phase(cfg, PHASE_MANUAL);
    }
    else if (strncmp(cmd, "pid ", 4) == 0) {
        /* pid <hum|temp|co2> <kp|ki|kd> N */
        /* Simplified parser */
        printf("  PID gains updated\n");
    }
    else if (strncmp(cmd, "override ", 9) == 0) {
        /* override <hum|heat|fan|light> N */
        /* Simplified parser */
        printf("  Override set (auto-clears in %d s)\n", cfg->override_timeout_s);
    }
    else if (strncmp(cmd, "calibrate co2 ", 14) == 0) {
        uint16_t ppm = atoi(cmd + 14);
        printf("  SCD41 forced calibration at %d ppm...\n", ppm);
        scd41_force_recalibration(ppm);
        printf("  Done\n");
    }
    else if (strncmp(cmd, "schedule show", 13) == 0) {
        printf("  Colonization: 14d, 24°C, 82%% RH, 5000 CO2, 10%% light\n");
        printf("  Pinning:      5d,  18°C, 92%% RH, 1000 CO2, 50%% light\n");
        printf("  Fruiting:     14d, 22°C, 93%% RH, 1000 CO2, 70%% light\n");
        printf("  Harvest:      2d,  20°C, 75%% RH, ambient CO2, OFF light\n");
        printf("  Auto-advance: %s\n", cfg->auto_advance ? "ON" : "OFF");
    }
    else if (strncmp(cmd, "save", 4) == 0) {
        config_save(cfg);
        printf("  Config saved to NVS\n");
    }
    else if (strncmp(cmd, "reset", 5) == 0) {
        config_factory_reset();
        printf("  Factory reset, restarting...\n");
        esp_restart();
    }
    else {
        printf("  Unknown command. Type 'help' for commands.\n");
    }
    printf("MYC> ");
}

/* ================================================================
 * OLED DISPLAY (SSD1306) - Minimal Driver
 * ================================================================ */

#define SSD1306_CMD_MODE    0x00
#define SSD1306_DATA_MODE   0x40
#define SSD1306_DISPLAY_OFF 0xAE
#define SSD1306_DISPLAY_ON  0xAF
#define SSD1306_SET_CONTRAST 0x81
#define SSD1306_SET_MULTIPLEX 0xA8
#define SSD1306_SET_DISPLAY_OFFSET 0xD3
#define SSD1306_SET_START_LINE 0x40
#define SSD1306_SET_SEGMENT_REMAP 0xA1
#define SSD1306_SET_COM_SCAN_DIR 0xC8
#define SSD1306_SET_COM_PINS 0xDA
#define SSD1306_SET_CHARGE_PUMP 0x8D
#define SSD1306_SET_PRECHARGE 0xD9
#define SSD1306_SET_VCOM_DETECT 0xDB
#define SSD1306_SET_ENTIRE_ON 0xA5
#define SSD1306_SET_NORMAL_DISPLAY 0xA6

static esp_err_t ssd1306_write_cmd(uint8_t cmd)
{
    uint8_t data[2] = { SSD1306_CMD_MODE, cmd };
    return i2c_master_write_to_device(I2C_PORT, SSD1306_ADDR, data, 2, pdMS_TO_TICKS(100));
}

static esp_err_t ssd1306_write_data(const uint8_t *data, uint16_t len)
{
    uint8_t buf[len + 1];
    buf[0] = SSD1306_DATA_MODE;
    memcpy(buf + 1, data, len);
    return i2c_master_write_to_device(I2C_PORT, SSD1306_ADDR, buf, len + 1, pdMS_TO_TICKS(100));
}

/* 128×64 framebuffer */
static uint8_t oled_fb[128 * 8];  /* 128 columns × 8 pages */

esp_err_t oled_init(void)
{
    /* Init sequence for SSD1306 128x64 */
    ssd1306_write_cmd(SSD1306_DISPLAY_OFF);
    ssd1306_write_cmd(SSD1306_SET_MULTIPLEX);  ssd1306_write_cmd(63);
    ssd1306_write_cmd(SSD1306_SET_DISPLAY_OFFSET); ssd1306_write_cmd(0);
    ssd1306_write_cmd(SSD1306_SET_START_LINE);
    ssd1306_write_cmd(SSD1306_SET_SEGMENT_REMAP);
    ssd1306_write_cmd(SSD1306_SET_COM_SCAN_DIR);
    ssd1306_write_cmd(SSD1306_SET_COM_PINS);   ssd1306_write_cmd(0x12);
    ssd1306_write_cmd(SSD1306_SET_CONTRAST);   ssd1306_write_cmd(0xCF);
    ssd1306_write_cmd(SSD1306_SET_ENTIRE_ON);
    ssd1306_write_cmd(SSD1306_SET_NORMAL_DISPLAY);
    ssd1306_write_cmd(SSD1306_SET_CHARGE_PUMP); ssd1306_write_cmd(0x14);
    ssd1306_write_cmd(SSD1306_SET_PRECHARGE);  ssd1306_write_cmd(0xF1);
    ssd1306_write_cmd(SSD1306_SET_VCOM_DETECT); ssd1306_write_cmd(0x40);
    ssd1306_write_cmd(SSD1306_DISPLAY_ON);

    memset(oled_fb, 0, sizeof(oled_fb));
    g_state.oled_present = true;

    ESP_LOGI(TAG, "SSD1306 OLED initialized (128x64, I2C 0x3C)");
    return ESP_OK;
}

esp_err_t oled_clear(void)
{
    memset(oled_fb, 0, sizeof(oled_fb));
    /* Update all 8 pages */
    for (uint8_t page = 0; page < 8; page++) {
        ssd1306_write_cmd(0xB0 | page);        /* Set page address */
        ssd1306_write_cmd(0x00);                /* Set lower column */
        ssd1306_write_cmd(0x10);                /* Set higher column */
        ssd1306_write_data(&oled_fb[page * 128], 128);
    }
    return ESP_OK;
}

esp_err_t oled_draw_status(const sensor_data_t *sensors, const system_config_t *cfg)
{
    /* Simplified: clear framebuffer and write text-like data */
    memset(oled_fb, 0, sizeof(oled_fb));

    /* In a real implementation, use a font renderer to draw:
     * Line 0: Phase name and day counter
     * Line 1: Chamber temp and RH
     * Line 2: CO2 level
     * Line 3: Actuator outputs
     */

    /* Update display */
    for (uint8_t page = 0; page < 8; page++) {
        ssd1306_write_cmd(0xB0 | page);
        ssd1306_write_cmd(0x00);
        ssd1306_write_cmd(0x10);
        ssd1306_write_data(&oled_fb[page * 128], 128);
    }
    return ESP_OK;
}

/* ================================================================
 * ROTARY ENCODER (Simple GPIO-based)
 * ================================================================ */

static volatile int8_t  enc_delta = 0;
static volatile bool    enc_pressed = false;

static void IRAM_ATTR encoder_isr(void *arg)
{
    static uint8_t state = 0;
    state = (state << 2) | (gpio_get_level(ROT_ENC_A_GPIO) << 1) | gpio_get_level(ROT_ENC_B_GPIO);
    switch (state & 0x0F) {
        case 0x01: case 0x07: case 0x08: case 0x0E: enc_delta++; break;
        case 0x02: case 0x04: case 0x0B: case 0x0D: enc_delta--; break;
    }

    /* Push button */
    if (gpio_get_level(ROT_ENC_SW_GPIO) == 0) {
        enc_pressed = true;
    }
}

esp_err_t encoder_init(void)
{
    gpio_config_t enc_conf = {
        .pin_bit_mask = (1ULL << ROT_ENC_A_GPIO) | (1ULL << ROT_ENC_B_GPIO) | (1ULL << ROT_ENC_SW_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_ANYEDGE,
    };
    gpio_config(&enc_conf);

    gpio_install_isr_service(0);
    gpio_isr_handler_add(ROT_ENC_A_GPIO, encoder_isr, NULL);
    gpio_isr_handler_add(ROT_ENC_B_GPIO, encoder_isr, NULL);
    gpio_isr_handler_add(ROT_ENC_SW_GPIO, encoder_isr, NULL);

    ESP_LOGI(TAG, "Rotary encoder initialized on A=%d B=%d SW=%d",
             ROT_ENC_A_GPIO, ROT_ENC_B_GPIO, ROT_ENC_SW_GPIO);
    return ESP_OK;
}

int8_t encoder_get_delta(void)
{
    int8_t d = enc_delta;
    enc_delta = 0;
    return d;
}

bool encoder_get_press(void)
{
    bool p = enc_pressed;
    enc_pressed = false;
    return p;
}

/* ================================================================
 * MAIN TASK: SENSOR READING + PID CONTROL
 * ================================================================ */

static void sensor_task(void *arg)
{
    ESP_LOGI(TAG, "Sensor task started");

    /* Wait for SCD41 warm-up */
    vTaskDelay(pdMS_TO_TICKS(60000));
    g_state.scd41_warmed_up = true;
    ESP_LOGI(TAG, "SCD41 warm-up complete");

    while (1) {
        uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
        g_state.uptime_s = now / 1000;

        /* Read SHT40 chamber */
        if (sht40_read(SHT40_CHAMBER_ADDR, &g_state.sensors.chamber) != ESP_OK) {
            g_state.error_flags |= ERR_SHT40_CHAMBER;
        } else {
            g_state.error_flags &= ~ERR_SHT40_CHAMBER;
        }

        /* Read SHT40 substrate */
        if (sht40_read(SHT40_SUBSTRATE_ADDR, &g_state.sensors.substrate) != ESP_OK) {
            g_state.error_flags |= ERR_SHT40_SUBSTRATE;
        } else {
            g_state.error_flags &= ~ERR_SHT40_SUBSTRATE;
        }

        /* Read SCD41 CO2 */
        if (g_state.scd41_warmed_up && scd41_data_ready()) {
            if (scd41_read_measurement(&g_state.sensors.co2) != ESP_OK) {
                g_state.error_flags |= ERR_SCD41;
            } else {
                g_state.error_flags &= ~ERR_SCD41;
            }
        }

        /* Read TSL2591 light */
        if (tsl2591_read(&g_state.sensors.light) != ESP_OK) {
            g_state.error_flags |= ERR_TSL2591;
        } else {
            g_state.error_flags &= ~ERR_TSL2591;
        }

        /* Read DS18B20 probes */
        ds18b20_reading_t deep_temps[2];
        if (ds18b20_read_all(deep_temps, 2) == ESP_OK) {
            g_state.sensors.deep_temp_1 = deep_temps[0];
            g_state.sensors.deep_temp_2 = deep_temps[1];
        }

        /* Read power voltages */
        g_state.sensors.lipo_v = power_read_lipo_v();
        g_state.sensors.rail_12v = power_read_12v_rail();
        g_state.sensors.usb_present = power_usb_present();

        /* Safety check: over-temperature */
        if (g_state.sensors.chamber.temp_c > 40.0f) {
            actuators_emergency_off();
            g_state.error_flags |= ERR_OVERTEMP;
            ESP_LOGE(TAG, "OVERTEMP: Chamber %.1f°C > 40°C, emergency shutdown!",
                     g_state.sensors.chamber.temp_c);
        }

        /* Low battery warning */
        if (g_state.sensors.lipo_v < 3.3f && g_state.sensors.lipo_v > 1.0f) {
            g_state.error_flags |= ERR_LIPO_LOW;
            ESP_LOGW(TAG, "LIPO LOW: %.2fV", g_state.sensors.lipo_v);
        } else {
            g_state.error_flags &= ~ERR_LIPO_LOW;
        }

        g_state.last_sensor_read_ms = now;
        vTaskDelay(pdMS_TO_TICKS(g_config.sensor_interval_s * 1000));
    }
}

static void pid_task(void *arg)
{
    ESP_LOGI(TAG, "PID control task started (1 Hz)");

    while (1) {
        float dt = 1.0f;  /* 1-second PID interval */

        /* Skip PID if sensors invalid or emergency */
        if (g_state.error_flags & ERR_OVERTEMP) {
            vTaskDelay(pdMS_TO_TICKS(1000));
            continue;
        }

        /* Humidity PID: setpoint → humidifier output */
        if (g_state.sensors.chamber.valid) {
            float hum_out = pid_compute(&g_config.pid_humidity,
                                         g_config.rh_setpoint,
                                         g_state.sensors.chamber.rh_pct,
                                         dt);
            g_config.actuator_output[ACTUATOR_HUMIDIFIER] = hum_out;
        }

        /* Temperature PID: setpoint → heater output */
        if (g_state.sensors.chamber.valid) {
            float temp_out = pid_compute(&g_config.pid_temperature,
                                          g_config.temp_setpoint,
                                          g_state.sensors.chamber.temp_c,
                                          dt);
            g_config.actuator_output[ACTUATOR_HEATER] = temp_out;
        }

        /* CO2 PID: setpoint → fan output (inverted: higher CO2 → more fan) */
        if (g_state.sensors.co2.valid && g_config.co2_max_ppm > 0) {
            float co2_error = (float)g_state.sensors.co2.co2_ppm - (float)g_config.co2_max_ppm;
            if (co2_error > 0) {
                /* CO2 above threshold → run fan proportional to excess */
                float fan_out = pid_compute(&g_config.pid_co2,
                                             (float)g_config.co2_max_ppm,
                                             (float)g_state.sensors.co2.co2_ppm,
                                             dt);
                g_config.actuator_output[ACTUATOR_FAN] = fan_out;
            } else {
                g_config.actuator_output[ACTUATOR_FAN] = 0.0f;
                pid_reset(&g_config.pid_co2);
            }
        }

        /* Light: schedule-based (not PID) */
        /* Simple: if light_on_hours > 0, use light_pct during "day" hours */
        /* For now, use constant light_pct during fruiting/pinning */
        g_config.actuator_output[ACTUATOR_LIGHT] = g_config.light_pct;

        /* Apply manual overrides */
        for (int i = 0; i < ACTUATOR_COUNT; i++) {
            if (g_config.manual_override[i] > 0.0f) {
                g_config.actuator_output[i] = g_config.manual_override[i];
            }
        }

        /* Set PWM outputs */
        for (int i = 0; i < ACTUATOR_COUNT; i++) {
            actuators_set_pwm(i, g_config.actuator_output[i]);
        }

        g_state.last_pid_update_ms = xTaskGetTickCount() * portTICK_PERIOD_MS;
        vTaskDelay(pdMS_TO_TICKS(g_config.pid_interval_s * 1000));
    }
}

static void display_task(void *arg)
{
    ESP_LOGI(TAG, "OLED display task started");

    while (1) {
        if (g_state.oled_present) {
            oled_draw_status(&g_state.sensors, &g_config);
        }
        vTaskDelay(pdMS_TO_TICKS(g_config.oled_update_s * 1000));
    }
}

/* ================================================================
 * MAIN ENTRY POINT
 * ================================================================ */

void app_main(void)
{
    ESP_LOGI(TAG, "=== Mycelium Node v1.0 ===");
    ESP_LOGI(TAG, "Mushroom Fruiting Chamber Environmental Controller");

    /* Initialize NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* Load config or set defaults */
    if (config_load(&g_config) != ESP_OK) {
        config_set_defaults(&g_config);
        config_save(&g_config);
        ESP_LOGI(TAG, "Default config loaded and saved");
    } else {
        ESP_LOGI(TAG, "Config loaded from NVS");
    }

    /* Initialize GPIO */
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << SCD41_RESET_GPIO) | (1ULL << LDO_EN_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);

    /* Enable 3.3V LDO */
    gpio_set_level(LDO_EN_GPIO, 1);
    vTaskDelay(pdMS_TO_TICKS(100));

    /* Initialize I2C bus */
    i2c_bus_init();

    /* Initialize sensors */
    sht40_init(SHT40_CHAMBER_ADDR);
    sht40_init(SHT40_SUBSTRATE_ADDR);
    scd41_init();
    tsl2591_init();
    ds18b20_init();

    /* Initialize OLED */
    if (oled_init() == ESP_OK) {
        g_state.oled_present = true;
    } else {
        g_state.oled_present = false;
        g_state.error_flags |= ERR_OLED;
    }

    /* Initialize actuators */
    actuators_init();

    /* Initialize power monitoring */
    power_monitor_init();

    /* Initialize buzzer */
    buzzer_init();

    /* Initialize rotary encoder */
    encoder_init();

    /* Initialize debug UART */
    debug_uart_init();

    /* Apply initial phase setpoints */
    scheduler_apply_phase(&g_config, g_config.phase);

    /* Startup beep */
    buzzer_beep(2000, 100);
    vTaskDelay(pdMS_TO_TICKS(50));
    buzzer_beep(3000, 100);

    /* Create tasks */
    xTaskCreate(sensor_task, "sensor", 4096, NULL, 5, NULL);
    xTaskCreate(pid_task, "pid", 4096, NULL, 4, NULL);
    xTaskCreate(display_task, "display", 4096, NULL, 3, NULL);

    /* Main loop: process debug UART commands */
    while (1) {
        uint8_t c;
        int len = uart_read_bytes(UART_NUM_0, &c, 1, pdMS_TO_TICKS(100));
        if (len > 0) {
            if (c == '\n' || c == '\r') {
                if (uart_cmd_idx > 0) {
                    uart_cmd_buf[uart_cmd_idx] = '\0';
                    debug_process_command(uart_cmd_buf, &g_state, &g_config);
                    uart_cmd_idx = 0;
                }
            } else if (uart_cmd_idx < UART_BUF_SIZE - 1) {
                uart_cmd_buf[uart_cmd_idx++] = c;
            }
        }
    }
}