/*
 * power.c — solar charger + fuel gauge + light-sleep manager
 */
#include "power.h"
#include "driver/gpio.h"
#include "driver/i2c.h"
#include "esp_sleep.h"
#include "esp_log.h"

static const char *TAG = "power";

#define PIN_CHRG_STAT  24
#define PIN_SOL_PG     25
#define MAX17048_ADDR  0x36

static float s_soc = 100.0f;

void power_init(void)
{
    gpio_set_direction(PIN_CHRG_STAT, GPIO_MODE_INPUT);
    gpio_set_direction(PIN_SOL_PG,    GPIO_MODE_INPUT);

    /* MAX17048 quick-start + reset (simplified). */
    uint8_t cmd[] = { 0x06, 0x40, 0x00 };
    i2c_master_write_to_device(I2C_NUM_0, MAX17048_ADDR, cmd, 3, 100);
    ESP_LOGI(TAG, "MAX17048 fuel gauge init");
}

float power_soc(void)
{
    uint8_t reg = 0x04;  /* SoC register */
    uint8_t buf[2];
    esp_err_t e = i2c_master_write_read_device(I2C_NUM_0, MAX17048_ADDR,
                                               &reg, 1, buf, 2, 100);
    if (e == ESP_OK) {
        s_soc = (float)((buf[0] << 8) | buf[1]) / 256.0f;
    }
    return s_soc;
}

int power_solar_present(void)
{
    return gpio_get_level(PIN_SOL_PG) == 1;
}

void power_light_sleep(void)
{
    /* Wake on EXT0 (ADS131M04 DRDY, GPIO4 = low). */
    esp_sleep_enable_ext0_wakeup(GPIO_NUM_4, 0);
    esp_light_sleep_start();
}