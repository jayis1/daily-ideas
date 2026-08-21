/*
 * power.c — MAX17048 fuel gauge + deep-sleep duty-cycle mode
 *
 * The MAX17048 is a LiPo fuel gauge over I²C that reports battery
 * percentage and voltage without needing a characterization table.
 * The deep-sleep mode puts the ESP32 into light-sleep between
 * coincidence interrupts to extend battery life to ~1 week.
 */
#include "power.h"
#include "sky_lens.h"

#ifdef SKY_LENS_SIM
#include "port_sim.h"
#else
#include "driver/i2c.h"
#include "esp_sleep.h"
#include "esp_log.h"
static const char *TAG = "power";
#define I2C_PORT   I2C_NUM_0
#define FG_ADDR    0x36   /* MAX17048 I²C address */
#endif

void power_init(void)
{
#ifdef SKY_LENS_SIM
    port_sim_log("power init (sim)");
#else
    /* MAX17048 is mostly plug-and-play; the reset command (0x4C00 to
     * reg 0x16) followed by a 10 ms wait is needed on first boot. */
    uint8_t reset_cmd[3] = {0x16, 0x4C, 0x00};
    i2c_master_write_to_device(I2C_PORT, FG_ADDR, reset_cmd, 3, pdMS_TO_TICKS(10));
    vTaskDelay(pdMS_TO_TICKS(10));
    ESP_LOGI(TAG, "MAX17048 fuel gauge init");
#endif
}

float power_battery_pct(void)
{
#ifdef SKY_LENS_SIM
    return 85.0f;   /* sim always returns 85% */
#else
    uint8_t buf[2] = {0};
    uint8_t reg = 0x02;   /* SOC register */
    i2c_master_write_read_device(I2C_PORT, FG_ADDR, &reg, 1, buf, 2, pdMS_TO_TICKS(10));
    /* SOC is 16-bit, 1/256% per bit → 0..100% */
    uint16_t raw = (buf[0] << 8) | buf[1];
    return (float)raw / 256.0f;
#endif
}

float power_battery_mv(void)
{
#ifdef SKY_LENS_SIM
    return 3850.0f;
#else
    uint8_t buf[2] = {0};
    uint8_t reg = 0x09;   /* VCELL register */
    i2c_master_write_read_device(I2C_PORT, FG_ADDR, &reg, 1, buf, 2, pdMS_TO_TICKS(10));
    uint16_t raw = (buf[0] << 8) | buf[1];
    /* 78.125 µV per bit → mV = raw * 78.125e-3 */
    return (float)raw * 0.078125f * 1000.0f;
#endif
}

void power_deep_sleep(uint64_t us)
{
#ifdef SKY_LENS_SIM
    port_sim_log("deep sleep %llu us (sim)", (unsigned long long)us);
#else
    esp_sleep_enable_timer_wakeup(us);
    /* Wake also on RTC GPIO (SiPM discriminator edges) */
    esp_light_sleep_start();
#endif
}

#ifndef SKY_LENS_SIM
#include "freertos/FreeRTOS.h"
#endif