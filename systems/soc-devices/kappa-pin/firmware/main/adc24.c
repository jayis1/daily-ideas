/*
 * kappa-pin / firmware / main / adc24.c
 * ADS122U04 24-bit delta-sigma ADC driver (SPI)
 *
 * Configured for ratiometric 4-wire PT1000 RTD measurement:
 *   IDAC1/IDAC2 → excitation leads (1 mA each, parallel = 2 mA total through RTD)
 *   AINp/AINn   → sense leads (differential, ratiometric vs. reference resistor)
 *   PGA gain = 1, data rate = 120 SPS turbo
 *
 * MIT License.
 */
#include "adc24.h"
#include "esp_log.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include <string.h>
#include <math.h>

static const char *TAG = "adc24";

static spi_device_handle_t adc_spi;
static bool initialized = false;

/* ---- SPI command helpers ---- */

static esp_err_t adc_spi_write(uint8_t *data, int len)
{
    spi_transaction_t t = {0};
    t.length = len * 8;
    t.tx_buffer = data;
    t.flags = SPI_TRANS_USE_RXDATA;
    return spi_device_polling_transmit(adc_spi, &t);
}

static esp_err_t adc_spi_read(uint8_t *cmd, int cmd_len, uint8_t *rx, int rx_len)
{
    spi_transaction_t t = {0};
    t.length = (cmd_len + rx_len) * 8;
    t.tx_buffer = cmd;
    t.rxlength = rx_len * 8;
    t.rx_buffer = rx;
    t.flags = 0;
    return spi_device_polling_transmit(adc_spi, &t);
}

/* Write to ADS122U04 register */
static adc_err_t adc_write_reg(uint8_t reg, uint8_t value)
{
    uint8_t cmd[2];
    cmd[0] = 0x40 | (reg & 0x0F);   /* WREG command */
    cmd[1] = value;
    esp_err_t ret = adc_spi_write(cmd, 2);
    return (ret == ESP_OK) ? ADC_OK : ADC_ERR_SPI;
}

/* Read from ADS122U04 register */
static adc_err_t adc_read_reg(uint8_t reg, uint8_t *value)
{
    uint8_t cmd[1] = { 0x20 | (reg & 0x0F) };  /* RREG command */
    uint8_t rx[1];
    esp_err_t ret = adc_spi_read(cmd, 1, rx, 1);
    if (ret != ESP_OK) return ADC_ERR_SPI;
    *value = rx[0];
    return ADC_OK;
}

/* Send command byte */
static adc_err_t adc_send_cmd(uint8_t cmd)
{
    esp_err_t ret = adc_spi_write(&cmd, 1);
    return (ret == ESP_OK) ? ADC_OK : ADC_ERR_SPI;
}

/* ---- Public API ---- */

adc_err_t adc24_init(void)
{
    if (initialized) return ADC_OK;

    /* Configure DRDY pin as input */
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << ADC24_DRDY_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);

    /* Configure CS pin */
    gpio_config_t cs_conf = {
        .pin_bit_mask = (1ULL << ADC24_CS_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
    };
    gpio_config(&cs_conf);
    gpio_set_level(ADC24_CS_PIN, 1);

    /* Add device to SPI bus */
    spi_device_interface_config_t dev_cfg = {
        .clock_speed_hz = 2000000,   /* 2 MHz — ADS122U04 max is 4 MHz */
        .mode = 1,                    /* CPOL=0, CPHA=1 (ADS122U04 uses mode 1) */
        .spics_io_num = ADC24_CS_PIN,
        .queue_size = 4,
        .flags = SPI_DEVICE_HALFDUPLEX,
    };
    esp_err_t ret = spi_bus_add_device(SPI_HOST, &dev_cfg, &adc_spi);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI add device failed: %s", esp_err_to_name(ret));
        return ADC_ERR_SPI;
    }

    /* Reset ADC */
    vTaskDelay(pdMS_TO_TICKS(10));
    adc_send_cmd(0x06);  /* RESET */
    vTaskDelay(pdMS_TO_TICKS(5));

    /* Configure registers for 4-wire RTD:
     * Config0: input mux = AIN2-AIN3, gain = 1, PGA enabled, bypass = 0
     * Config1: data rate = 175 SPS, normal mode, conv mode = continuous
     * Config2: Vref = external (ref resistor), IDAC mux routing
     * Config3: IDAC current = 1 mA, IDAC1→AIN0, IDAC2→AIN1
     */

    /* Config0: MUX[3:0]=0100 (AIN2-AIN3), GAIN[2:0]=000 (1x), PGA_BYPASS=0 */
    adc_write_reg(ADC_REG_CONFIG0, 0x40);  /* AIN2-AIN3, gain 1 */

    /* Config1: DR[2:0]=011 (175 SPS), MODE[1:0]=00 (normal), CM=1 (continuous),
     *          TEMP=0, BCS=0 */
    adc_write_reg(ADC_REG_CONFIG1, 0x0C);  /* 175 SPS, continuous */

    /* Config2: VREF[1:0]=10 (external ref on REFP0/REFN0),
     *          FIRM[1:0]=00 (50/60Hz reject), PSW=0 */
    adc_write_reg(ADC_REG_CONFIG2, 0x20);  /* external ref, 50/60 reject */

    /* Config3: IDAC[3:0]=0111 (1 mA) on I1MUX and I2MUX */
    /* IDAC_MAG[3:0] in upper nibble, I1MUX[2:0]+I2MUX in lower
     * For ADS122U04: IDAC current in config3 upper nibble
     *   0111 = 1 mA
     * Routing in separate config (IDAC routing reg)
     */
    adc_write_reg(ADC_REG_CONFIG3, 0x70);  /* IDAC = 1 mA */

    /* IDAC routing: IDAC1 → AIN0, IDAC2 → AIN1
     * The ADS122U04 uses dedicated IDAC mux registers.
     * I1MUX = AIN0 (000), I2MUX = AIN1 (001)
     */
    adc_write_reg(ADC_REG_IDAC, 0x01);  /* IDAC1→AIN0, IDAC2→AIN1 */

    /* Start continuous conversions */
    adc_send_cmd(0x08);  /* START/SYNC */

    initialized = true;
    ESP_LOGI(TAG, "ADS122U04 initialized: 4-wire RTD, 1mA IDAC, 175 SPS");
    return ADC_OK;
}

adc_err_t adc24_start_sync(void)
{
    return adc_send_cmd(0x08);
}

adc_err_t adc24_set_data_rate(uint8_t rate)
{
    uint8_t cfg1;
    adc_err_t err = adc_read_reg(ADC_REG_CONFIG1, &cfg1);
    if (err != ADC_OK) return err;
    cfg1 = (cfg1 & 0x8F) | ((rate & 0x07) << 4);
    return adc_write_reg(ADC_REG_CONFIG1, cfg1);
}

adc_err_t adc24_read_raw(int32_t *raw)
{
    /* Wait for DRDY (active low) with timeout */
    int timeout_us = 50000;  /* 50 ms */
    int64_t t0 = esp_timer_get_time();
    while (gpio_get_level(ADC24_DRDY_PIN) == 1) {
        if ((esp_timer_get_time() - t0) > timeout_us)
            return ADC_ERR_TIMEOUT;
        vTaskDelay(pdMS_TO_TICKS(1));
    }

    /* Read 3 bytes (24-bit data) using RDATA command */
    uint8_t cmd[1] = { 0x10 };  /* RDATA */
    uint8_t rx[3];
    esp_err_t ret = adc_spi_read(cmd, 1, rx, 3);
    if (ret != ESP_OK) return ADC_ERR_SPI;

    /* Convert to signed 24-bit */
    uint32_t val = ((uint32_t)rx[0] << 16) | ((uint32_t)rx[1] << 8) | rx[2];
    if (val & 0x800000) val |= 0xFF000000;  /* sign extend */
    *raw = (int32_t)val;

    return ADC_OK;
}

adc_err_t adc24_read_resistance(float *r_ohm)
{
    int32_t raw;
    adc_err_t err = adc24_read_raw(&raw);
    if (err != ADC_OK) return err;

    /* Ratiometric: R_RTD = (raw / 2^23) * R_ref * (PGA_gain_factor)
     * With external reference = R_ref (8.2 kΩ), gain = 1:
     * R_RTD = (raw / 2^23) * 8200
     *
     * The ADS122U04 is 24-bit signed, so full scale = 2^23
     * With IDAC = 1mA through RTD and reference resistor,
     * V_RTD / V_ref = R_RTD / R_ref
     */
    *r_ohm = ((float)raw / 8388608.0f) * RTD_REF_RESISTOR;
    return ADC_OK;
}

adc_err_t adc24_read_temperature(float *temp_c)
{
    float r;
    adc_err_t err = adc24_read_resistance(&r);
    if (err != ADC_OK) return err;

    /* Callendar-Van Dusen equation for PT1000:
     * For T >= 0: R(T) = R0 * (1 + A*T + B*T²)
     *   Solve: T = (-A + sqrt(A² - 4*B*(1 - R/R0))) / (2*B)
     * For T < 0: use full CVD with C coefficient (iterative)
     */
    float ratio = r / PT1000_R0;

    if (ratio >= 1.0f) {
        /* T >= 0°C — quadratic formula */
        float discrim = PT1000_A * PT1000_A - 4.0f * PT1000_B * (1.0f - ratio);
        if (discrim < 0) discrim = 0;
        *temp_c = (-PT1000_A + sqrtf(discrim)) / (2.0f * PT1000_B);
    } else {
        /* T < 0°C — use CVD with C coefficient, Newton-Raphson iteration */
        float t = -10.0f;  /* initial guess */
        for (int i = 0; i < 20; i++) {
            float r_pred = PT1000_R0 * (1.0f + PT1000_A * t +
                            PT1000_B * t * t +
                            PT1000_C * (t - 100.0f) * t * t * t);
            float dr_dt = PT1000_R0 * (PT1000_A + 2.0f * PT1000_B * t +
                            PT1000_C * (4.0f * t * t * t - 300.0f * t * t));
            if (fabsf(dr_dt) < 1e-10f) break;
            float dt = (r - r_pred) / dr_dt;
            t += dt;
            if (fabsf(dt) < 0.001f) break;
        }
        *temp_c = t;
    }

    return ADC_OK;
}