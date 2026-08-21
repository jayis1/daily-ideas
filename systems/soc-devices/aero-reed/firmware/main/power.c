/*
 * power.c — MAX17048 fuel gauge + ADC battery divider + TP4056 charge detect
 */
#include "power.h"
#include "synth.h"
#include "driver/i2c.h"
#include "driver/gpio.h"
#include "esp_log.h"

static const char *TAG = "power";

#define FG_ADDR       0x36
#define FG_REG_VCELL  0x02
#define FG_REG_SOC    0x04
#define FG_REG_MODE   0x06
#define CHARGE_STAT_PIN 4   /* TP4056 STAT pin (low=charging, high=full) */

static bool charging = false;
static uint8_t battery_pct = 100;

static uint16_t fg_read16(uint8_t reg)
{
    uint8_t buf[2] = {0};
    i2c_master_write_read_device(I2C_NUM_0, FG_ADDR, &reg, 1, buf, 2, pdMS_TO_TICKS(100));
    return ((uint16_t)buf[0] << 8) | buf[1];
}

void power_init(void)
{
    gpio_config_t io = {
        .pin_bit_mask = (1ULL << CHARGE_STAT_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
    };
    gpio_config(&io);
    ESP_LOGI(TAG, "Power init: MAX17048 fuel gauge + TP4056 charge status");
}

void power_task(void *arg)
{
    (void)arg;
    const TickType_t period = pdMS_TO_TICKS(1000);  /* 1 Hz */
    TickType_t last = xTaskGetTickCount();
    while (1) {
        /* Read fuel gauge state-of-charge */
        uint16_t soc_raw = fg_read16(FG_REG_SOC);
        battery_pct = (uint8_t)(soc_raw / 256);  /* MSB = integer % */
        if (battery_pct > 100) battery_pct = 100;

        /* Read TP4056 STAT pin (active-low = charging) */
        charging = (gpio_get_level(CHARGE_STAT_PIN) == 0);

        g_state.battery_pct = battery_pct;
        g_state.charging = charging;

        ESP_LOGD(TAG, "Battery: %d%% %s", battery_pct, charging ? "CHG" : "");
        vTaskDelayUntil(&last, period);
    }
}

uint8_t power_get_battery_pct(void) { return battery_pct; }
bool power_is_charging(void) { return charging; }