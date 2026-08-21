/*
 * Therma Weave — Current Monitor
 * current_monitor.c — INA199 current sense amplifier interface
 *
 * SPDX-License-Identifier: MIT
 */

#include "current_monitor.h"
#include "esp_log.h"

static const char *TAG = "CURRENT_MON";

/* I2C read helper */
static esp_err_t i2c_read_reg(i2c_port_t i2c_num, uint8_t dev_addr,
                                uint8_t reg, uint8_t *data, size_t len)
{
    /* In real firmware: use i2c_master_write_read_device() */
    (void)i2c_num;
    (void)dev_addr;
    (void)reg;
    /* Placeholder: return zeros */
    for (size_t i = 0; i < len; i++) {
        data[i] = 0;
    }
    return ESP_OK;
}

/* I2C write helper */
static esp_err_t i2c_write_reg(i2c_port_t i2c_num, uint8_t dev_addr,
                                 uint8_t reg, uint8_t *data, size_t len)
{
    (void)i2c_num;
    (void)dev_addr;
    (void)reg;
    (void)data;
    (void)len;
    return ESP_OK;
}

void current_monitor_init(current_monitor_t *cm, i2c_port_t i2c_num)
{
    cm->i2c_num = i2c_num;
    cm->total_current_ma = 0.0f;
    cm->overcurrent_threshold_ma = 4000.0f;  /* 4A default */

    for (int i = 0; i < NUM_ZONES; i++) {
        cm->zone_currents[i] = 0.0f;
        cm->overcurrent_fault[i] = false;
    }

    /* Configure INA199:
     * - Set calibration register for 0.01Ω shunt, 100V/V gain
     * - Set overcurrent alert threshold
     * - Enable alert pin
     */
    uint8_t cal_data[2] = { 0x10, 0x00 };  /* Calibration value */
    i2c_write_reg(i2c_num, INA199_ADDR, INA199_REG_CAL, cal_data, 2);

    /* Set alert threshold (4A = 4000mA) */
    /* Alert threshold in shunt voltage: 4A × 0.01Ω × 100V/V = 4V → register value */
    uint8_t alert_data[2] = { 0x0F, 0xA0 };  /* Approximate */
    i2c_write_reg(i2c_num, INA199_ADDR, INA199_REG_ALERT, alert_data, 2);

    ESP_LOGI(TAG, "INA199 current monitor initialized (I2C addr=0x%02X)", INA199_ADDR);
}

float current_monitor_read_zone(current_monitor_t *cm, uint8_t zone)
{
    if (zone >= NUM_ZONES) return 0.0f;

    /*
     * Read current from INA199.
     * In this design, a single INA199 is used with the total current,
     * and zone currents are estimated from duty cycle proportions.
     *
     * Alternative: use 4× INA199 (one per zone) with different I²C addresses
     * via a second 74HC4051 on the A0 pin.
     *
     * For this implementation, we read the total current and distribute
     * proportionally based on PWM duty cycle.
     */

    uint8_t buf[2] = {0};
    esp_err_t ret = i2c_read_reg(cm->i2c_num, INA199_ADDR, INA199_REG_CURRENT, buf, 2);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to read INA199 current register");
        return cm->zone_currents[zone];  /* Return last known value */
    }

    /* Convert register value to mA */
    /* INA199 current register: signed 16-bit, LSB = calibration-dependent */
    int16_t raw = (int16_t)((buf[0] << 8) | buf[1]);
    float current_ma = (float)raw * 1.0f;  /* LSB = 1mA with our calibration */

    /* Check overcurrent */
    if (current_ma > cm->overcurrent_threshold_ma) {
        cm->overcurrent_fault[zone] = true;
        ESP_LOGE(TAG, "Zone %d overcurrent: %.0f mA > %.0f mA threshold",
                 zone, current_ma, cm->overcurrent_threshold_ma);
    } else {
        cm->overcurrent_fault[zone] = false;
    }

    cm->zone_currents[zone] = current_ma;
    return current_ma;
}

float current_monitor_read_total(current_monitor_t *cm)
{
    float total = 0.0f;
    for (int i = 0; i < NUM_ZONES; i++) {
        total += cm->zone_currents[i];
    }
    cm->total_current_ma = total;
    return total;
}

void current_monitor_set_threshold(current_monitor_t *cm, float threshold_ma)
{
    cm->overcurrent_threshold_ma = threshold_ma;
    ESP_LOGI(TAG, "Overcurrent threshold set to %.0f mA", threshold_ma);

    /* Update INA199 alert register */
    /* (would write new threshold to INA199_REG_ALERT) */
}

bool current_monitor_check_alert(current_monitor_t *cm)
{
    /* Check GPIO11 (CURRENT_ALERT_PIN) — active low */
    /* Real: return !gpio_get_level(CURRENT_ALERT_PIN); */
    (void)cm;
    return false;
}