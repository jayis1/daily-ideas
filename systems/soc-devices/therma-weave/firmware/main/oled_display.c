/*
 * Therma Weave — OLED Display
 * oled_display.c — SSD1306 128×64 status display
 *
 * SPDX-License-Identifier: MIT
 */

#include "oled_display.h"
#include <stdio.h>
#include <string.h>
#include "esp_log.h"

static const char *TAG = "OLED";

/* SSD1306 command bytes */
#define SSD1306_CMD    0x00
#define SSD1306_DATA   0x40

/* SSD1306 initialization sequence */
static const uint8_t ssd1306_init_cmds[] = {
    0xAE,         /* Display OFF */
    0xD5, 0x80,   /* Set display clock divide: 0x80 */
    0xA8, 0x3F,   /* Set multiplex: 64 */
    0xD3, 0x00,   /* Set display offset: 0 */
    0x40,         /* Set start line: 0 */
    0x8D, 0x14,   /* Set charge pump: enable */
    0x20, 0x00,   /* Set memory mode: horizontal addressing */
    0xA1,         /* Set segment remap: column 127 = SEG0 */
    0xC8,         /* Set COM scan direction: remapped */
    0xDA, 0x12,   /* Set COM pins: 0x12 for 128×64 */
    0x81, 0xCF,   /* Set contrast: 0xCF */
    0xD9, 0xF1,   /* Set pre-charge: 0xF1 */
    0xDB, 0x40,   /* Set VCOMH deselect: 0x40 */
    0x2E,         /* Set scroll OFF */
    0xA4,         /* Set entire display ON: follow RAM */
    0xA6,         /* Set normal display (not inverted) */
    0xAF,         /* Display ON */
};

static void i2c_cmd(oled_display_t *oled, uint8_t cmd)
{
    /* Real: i2c_master_write_to_device(oled->i2c_num, SSD1306_I2C_ADDR, &cmd, 1, 100 / portTICK_PERIOD_MS); */
    (void)oled;
    (void)cmd;
}

static void i2c_data(oled_display_t *oled, const uint8_t *data, size_t len)
{
    /* Real: i2c_master_write_to_device(oled->i2c_num, SSD1306_I2C_ADDR, data, len, 100 / portTICK_PERIOD_MS); */
    (void)oled;
    (void)data;
    (void)len;
}

/* Simple 5×7 font (ASCII 32-127) */
static const uint8_t font5x7[][5] = {
    /* Simplified font — in production, use a full font table */
    {0x00, 0x00, 0x00, 0x00, 0x00}, /* space */
    /* ... (full font table omitted for brevity) */
};

void oled_display_init(oled_display_t *oled, i2c_port_t i2c_num)
{
    oled->i2c_num = i2c_num;
    oled->initialized = false;

    /* Send initialization commands */
    for (size_t i = 0; i < sizeof(ssd1306_init_cmds); i++) {
        i2c_cmd(oled, ssd1306_init_cmds[i]);
    }

    /* Clear display */
    oled_display_clear(oled);
    oled_display_flush(oled);

    oled->initialized = true;
    ESP_LOGI(TAG, "SSD1306 OLED initialized (128×64, I2C addr=0x%02X)", SSD1306_I2C_ADDR);
}

void oled_display_update(oled_display_t *oled, zone_controller_t *zones,
                          ambient_sensor_t *ambient, activity_detect_t *activity,
                          safety_watchdog_t *safety)
{
    if (!oled->initialized) return;

    char buf[22];  /* Max 21 chars per line on 128px with 6px font */

    oled_display_clear(oled);

    /* Line 0: Title + battery + fault */
    snprintf(buf, sizeof(buf), "TWv %4.1fV", 0.0f);  /* Battery voltage placeholder */
    oled_draw_string(oled, 0, 0, buf);

    if (safety && safety_watchdog_has_fault(safety)) {
        oled_draw_string(oled, 100, 0, "FLT!");
    }

    /* Lines 1-4: Zone status (temp, duty, target) */
    const char *zone_labels[NUM_ZONES] = {"Z0", "Z1", "Z2", "Z3"};

    for (int z = 0; z < NUM_ZONES; z++) {
        int y = (z + 1) * 8;

        if (zones[z].enabled) {
            /* Show: "Z0 37.2C 45%→40C" */
            snprintf(buf, sizeof(buf), "%s %5.1fC %3.0f%%→%2.0fC",
                     zone_labels[z],
                     zones[z].current_temp,
                     zones[z].duty_pct,
                     zones[z].target_temp);
        } else {
            /* Show: "Z0  OFF" or "Z0  FLT!" */
            if (zones[z].fault_overtemp || zones[z].fault_overcurrent ||
                zones[z].fault_thermistor_open || zones[z].fault_thermistor_short) {
                snprintf(buf, sizeof(buf), "%s  FLT!", zone_labels[z]);
            } else {
                snprintf(buf, sizeof(buf), "%s  OFF  %5.1fC",
                         zone_labels[z], zones[z].current_temp);
            }
        }
        oled_draw_string(oled, 0, y, buf);
    }

    /* Line 5: Activity + ambient */
    const char *act_labels[] = {"STILL", "WALK", "RUN", "FALL"};
    int act_idx = (activity && activity->level >= 0 && activity->level <= 3) ? activity->level : 0;

    if (ambient) {
        snprintf(buf, sizeof(buf), "%s  %4.1fC %4.0f%%H",
                 act_labels[act_idx],
                 ambient->temperature,
                 ambient->humidity);
    } else {
        snprintf(buf, sizeof(buf), "%s", act_labels[act_idx]);
    }
    oled_draw_string(oled, 0, 5 * 8, buf);

    oled_display_flush(oled);
}

void oled_display_flush(oled_display_t *oled)
{
    if (!oled->initialized) return;

    /* Set column address range: 0-127 */
    i2c_cmd(oled, 0x21);
    i2c_cmd(oled, 0x00);
    i2c_cmd(oled, 0x7F);

    /* Set page address range: 0-7 */
    i2c_cmd(oled, 0x22);
    i2c_cmd(oled, 0x00);
    i2c_cmd(oled, 0x07);

    /* Send framebuffer in 16-byte chunks */
    /* In real firmware: i2c_master_write_to_device() */
    for (size_t offset = 0; offset < sizeof(oled->framebuffer); offset += 16) {
        uint8_t chunk[17];
        chunk[0] = SSD1306_DATA;
        memcpy(&chunk[1], &oled->framebuffer[offset], 16);
        i2c_data(oled, chunk, 17);
    }
}

void oled_display_clear(oled_display_t *oled)
{
    memset(oled->framebuffer, 0, sizeof(oled->framebuffer));
}

void oled_draw_string(oled_display_t *oled, int x, int y, const char *str)
{
    /* Simplified: set pixels based on position (no actual font rendering) */
    /* In production, use a proper font table and framebuffer pixel setting */
    (void)oled;
    (void)x;
    (void)y;
    (void)str;
}

void oled_draw_temp(oled_display_t *oled, int x, int y, float temp, bool active)
{
    char buf[8];
    snprintf(buf, sizeof(buf), "%5.1f", temp);
    oled_draw_string(oled, x, y, buf);
    if (active) {
        oled_draw_string(oled, x + 30, y, "°C");
    } else {
        oled_draw_string(oled, x + 30, y, "--");
    }
}