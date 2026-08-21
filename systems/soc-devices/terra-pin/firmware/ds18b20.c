/**
 * terra_pin/ds18b20.c — DS18B20 1-Wire waterproof temperature sensor
 *
 * Minimal 1-Wire bit-bang driver on GPIO12. The DS18B20 is in a
 * waterproof TO-92 package potted in the probe shaft wall.
 *
 * 1-Wire timing (standard speed):
 *   Reset: pull low 480 µs, release, wait 480 µs
 *   Write 1: pull low 6 µs, release 64 µs
 *   Write 0: pull low 60 µs, release 10 µs
 *   Read:   pull low 6 µs, release, sample at 15 µs
 */

#include "ds18b20.h"
#include "esp_log.h"
#include "rom/gpio.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>

static const char *TAG = "DS18B20";

#define DS18B20_PIN        PIN_ONEWIRE
#define OW_RESET_US        480
#define OW_WRITE1_LOW_US   6
#define OW_WRITE1_REL_US   64
#define OW_WRITE0_LOW_US   60
#define OW_WRITE0_REL_US   10
#define OW_READ_LOW_US     6
#define OW_READ_SAMPLE_US  15
#define OW_READ_REL_US     55
#define OW_SLOT_US         70

/* DS18B20 ROM commands */
#define OW_CMD_SKIP_ROM    0xCC
#define OW_CMD_CONVERT_T   0x44
#define OW_CMD_READ_SCRATCH 0xBE

/* ── 1-Wire low-level ─────────────────────────────────────────────── */

static void ow_set_pin_output(void)
{
    gpio_set_direction(DS18B20_PIN, GPIO_MODE_OUTPUT);
}

static void ow_set_pin_input(void)
{
    gpio_set_direction(DS18B20_PIN, GPIO_MODE_INPUT);
    gpio_set_pull_mode(DS18B20_PIN, GPIO_PULLUP_ONLY);
}

static inline void ow_delay_us(uint32_t us)
{
    esp_rom_delay_us(us);
}

static bool ow_reset(void)
{
    ow_set_pin_output();
    gpio_set_level(DS18B20_PIN, 0);
    ow_delay_us(OW_RESET_US);
    ow_set_pin_input();
    ow_delay_us(70);  /* wait for presence pulse */
    bool presence = (gpio_get_level(DS18B20_PIN) == 0);
    ow_delay_us(OW_RESET_US - 70);  /* finish reset slot */
    return presence;
}

static void ow_write_bit(uint8_t bit)
{
    ow_set_pin_output();
    gpio_set_level(DS18B20_PIN, 0);
    if (bit) {
        ow_delay_us(OW_WRITE1_LOW_US);
        ow_set_pin_input();
        ow_delay_us(OW_WRITE1_REL_US);
    } else {
        ow_delay_us(OW_WRITE0_LOW_US);
        ow_set_pin_input();
        ow_delay_us(OW_WRITE0_REL_US);
    }
}

static uint8_t ow_read_bit(void)
{
    ow_set_pin_output();
    gpio_set_level(DS18B20_PIN, 0);
    ow_delay_us(OW_READ_LOW_US);
    ow_set_pin_input();
    ow_delay_us(OW_READ_SAMPLE_US - OW_READ_LOW_US);
    uint8_t bit = gpio_get_level(DS18B20_PIN);
    ow_delay_us(OW_READ_REL_US);
    return bit;
}

static void ow_write_byte(uint8_t byte)
{
    for (int i = 0; i < 8; i++) {
        ow_write_bit(byte & 0x01);
        byte >>= 1;
    }
}

static uint8_t ow_read_byte(void)
{
    uint8_t val = 0;
    for (int i = 0; i < 8; i++) {
        val >>= 1;
        if (ow_read_bit())
            val |= 0x80;
    }
    return val;
}

/* ── DS18B20 public API ───────────────────────────────────────────── */

esp_err_t ds18b20_init(void)
{
    ESP_LOGI(TAG, "Initializing DS18B20 on GPIO%d", DS18B20_PIN);
    gpio_set_direction(DS18B20_PIN, GPIO_MODE_INPUT_OUTPUT_OD);
    gpio_set_pull_mode(DS18B20_PIN, GPIO_PULLUP_ONLY);

    /* Check presence */
    if (!ow_reset()) {
        ESP_LOGE(TAG, "No DS18B20 detected on 1-Wire bus");
        return ESP_ERR_NOT_FOUND;
    }

    ESP_LOGI(TAG, "DS18B20 detected");
    return ESP_OK;
}

esp_err_t ds18b20_read(float *temp_c)
{
    /* Issue temperature conversion */
    if (!ow_reset()) {
        ESP_LOGE(TAG, "1-Wire reset failed");
        return ESP_ERR_TIMEOUT;
    }
    ow_write_byte(OW_CMD_SKIP_ROM);
    ow_write_byte(OW_CMD_CONVERT_T);

    /* Wait for conversion (12-bit default = 750 ms) */
    vTaskDelay(pdMS_TO_TICKS(750));

    /* Read scratchpad */
    if (!ow_reset()) {
        ESP_LOGE(TAG, "1-Wire reset failed (read)");
        return ESP_ERR_TIMEOUT;
    }
    ow_write_byte(OW_CMD_SKIP_ROM);
    ow_write_byte(OW_CMD_READ_SCRATCH);

    /* Read 9 bytes: 2 temp + 7 config/CRC */
    uint8_t scratch[9];
    for (int i = 0; i < 9; i++)
        scratch[i] = ow_read_byte();

    /* Temperature: 16-bit signed, 2^(-4) resolution */
    int16_t raw = (scratch[1] << 8) | scratch[0];
    *temp_c = (float)raw / 16.0f;

    ESP_LOGI(TAG, "Soil temp: %.2f °C", *temp_c);
    return ESP_OK;
}