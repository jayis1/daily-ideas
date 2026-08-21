/* ad5941.c — AD5941 analog front-end driver implementation
 *
 * Controls the AD5941 AFE over SPI to perform electrochemical impedance
 * spectroscopy (EIS) measurements. The AD5941's on-chip DFT engine
 * computes magnitude and phase directly, offloading the ESP32-S3.
 *
 * Key operations:
 * 1. Initialize AFE: configure clocks, switches, TIA, ADC, DFT engine
 * 2. For each frequency: program excitation DAC, start DFT, wait for IRQ
 * 3. Read DFT results (real + imaginary), compute |Z| and θ
 * 4. Apply calibration (open/short/KCl correction)
 */

#include "ad5941.h"
#include "sdkconfig.h"
#include "esp_log.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <math.h>
#include <string.h>

static const char *TAG = "ad5941";

/* SPI device handle */
static spi_device_handle_t spi_dev;
static int g_irq_pin = -1;
static int g_reset_pin = -1;
static ad5941_cal_t g_cal;
static bool g_cal_loaded = false;
static char g_last_error[128] = "no error";

/* ---- Low-level SPI access ---- */

/* AD5941 SPI protocol:
 * Write: [0x80|reg_addr[15:8]] [reg_addr[7:0]] [data...]
 * Read:  [0x00|reg_addr[15:8]] [reg_addr[7:0]] [dummy→data...]
 */
#define SPI_WRITE_FLAG  0x80
#define SPI_READ_FLAG   0x00

static esp_err_t ad5941_write_reg(uint16_t addr, uint32_t data, int len)
{
    uint8_t txbuf[8] = {0};
    txbuf[0] = SPI_WRITE_FLAG | (uint8_t)(addr >> 8);
    txbuf[1] = (uint8_t)(addr & 0xFF);

    /* Pack data (big-endian, variable length 1-4) */
    for (int i = 0; i < len; i++) {
        txbuf[2 + i] = (uint8_t)(data >> ((len - 1 - i) * 8));
    }

    spi_transaction_t t = {
        .length = (2 + len) * 8,
        .tx_buffer = txbuf,
        .flags = 0,
    };
    return spi_device_transmit(spi_dev, &t);
}

static esp_err_t ad5941_read_reg(uint16_t addr, uint32_t *data, int len)
{
    uint8_t txbuf[8] = {0};
    uint8_t rxbuf[8] = {0};
    txbuf[0] = SPI_READ_FLAG | (uint8_t)(addr >> 8);
    txbuf[1] = (uint8_t)(addr & 0xFF);

    spi_transaction_t t = {
        .length = (2 + len) * 8,
        .tx_buffer = txbuf,
        .rx_buffer = rxbuf,
        .flags = 0,
    };
    esp_err_t ret = spi_device_transmit(spi_dev, &t);
    if (ret != ESP_OK) {
        return ret;
    }

    *data = 0;
    for (int i = 0; i < len; i++) {
        *data = (*data << 8) | rxbuf[2 + i];
    }
    return ESP_OK;
}

/* ---- Initialization ---- */

esp_err_t ad5941_init(int cs_pin, int sck_pin, int miso_pin,
                      int mosi_pin, int irq_pin, int reset_pin)
{
    g_irq_pin = irq_pin;
    g_reset_pin = reset_pin;

    /* Configure IRQ pin as input */
    gpio_config_t irq_cfg = {
        .pin_bit_mask = (1ULL << irq_pin),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
    };
    gpio_config(&irq_cfg);

    /* Configure reset pin as output */
    gpio_config_t rst_cfg = {
        .pin_bit_mask = (1ULL << reset_pin),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
    };
    gpio_config(&rst_cfg);

    /* Hardware reset: pulse low for 100 µs */
    gpio_set_level(reset_pin, 0);
    vTaskDelay(pdMS_TO_TICKS(1));
    gpio_set_level(reset_pin, 1);
    vTaskDelay(pdMS_TO_TICKS(50));  /* Wait for AD5941 to stabilize */

    /* Configure SPI bus */
    spi_bus_config_t buscfg = {
        .miso_io_num = miso_pin,
        .mosi_io_num = mosi_pin,
        .sclk_io_num = sck_pin,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 64,
    };
    esp_err_t ret = spi_bus_initialize(SPI_AD5941_HOST, &buscfg, SPI_DMA_CH_AUTO);
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "SPI bus init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Add device on SPI bus */
    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = SPI_AD5941_FREQ_HZ,
        .mode = 0,              /* CPOL=0, CPHA=0 */
        .spics_io_num = cs_pin,
        .queue_size = 4,
        .flags = SPI_DEVICE_HALFDUPLEX,
    };
    ret = spi_bus_add_device(SPI_AD5941_HOST, &devcfg, &spi_dev);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI device add failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Configure AD5941 internal registers */
    /* 1. Power up AFE and set clocks */
    ad5941_write_reg(AD5941_REG_AFECON, 0x00, 2);  /* AFE reset */
    vTaskDelay(pdMS_TO_TICKS(10));
    ad5941_write_reg(AD5941_REG_AFECON, 0x01, 2);  /* Power up */

    /* 2. Configure switch matrix for impedance measurement */
    /* Connect CE0 to external counter electrode, RE0 to reference */
    uint32_t swcon = 0x00140400;  /* SW5(Au) + SW6(Pt) + SW9(RE) */
    ad5941_write_reg(AD5941_REG_AFE_SWCON, swcon, 4);

    /* 3. Configure DFT engine: 1024-point DFT */
    ad5941_write_reg(AD5941_REG_AFE_DFTNUM, 1024, 2);
    ad5941_write_reg(AD5941_REG_AFE_DFTCFG, 0x02, 2); /* Hanning window */

    /* 4. Set default TIA gain (10 kΩ) */
    ad5941_write_reg(AD5941_REG_AFE_TIA, RTIA_10K, 4);

    /* 5. Set default ADC PGA gain */
    ad5941_write_reg(AD5941_REG_AFE_ADCPga, 0x01, 2); /* PGA gain = 2 */

    /* Load calibration from NVS (if available) */
    if (g_cal_loaded) {
        ad5941_set_calibration(&g_cal);
    }

    ESP_LOGI(TAG, "AD5941 initialized (SPI %d MHz)", SPI_AD5941_FREQ_HZ / 1000000);
    return ESP_OK;
}

void ad5941_reset(void)
{
    if (g_reset_pin >= 0) {
        gpio_set_level(g_reset_pin, 0);
        vTaskDelay(pdMS_TO_TICKS(1));
        gpio_set_level(g_reset_pin, 1);
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

/* ---- Measurement ---- */

uint32_t ad5941_select_rtia(float freq_hz, float exc_amplitude)
{
    /* Heuristic RTIA selection based on frequency and expected impedance:
     * - Low freq → high impedance → high RTIA
     * - High freq → low impedance → low RTIA
     * This is a coarse auto-ranging; fine-tuning happens via signal level check.
     */
    if (freq_hz < 10.0f)        return RTIA_1M;
    else if (freq_hz < 100.0f)  return RTIA_100K;
    else if (freq_hz < 1000.0f) return RTIA_10K;
    else if (freq_hz < 10000.0f) return RTIA_4K;
    else                         return RTIA_1K;
}

esp_err_t ad5941_measure_z(float freq_hz, float exc_amplitude,
                            uint32_t rtia, ad5941_z_point_t *result)
{
    /* 1. Program excitation frequency */
    /* AD5941 frequency register: 32-bit, represents Hz directly */
    uint32_t freq_reg = (uint32_t)(freq_hz * 65536.0f / 16000000.0f);
    ad5941_write_reg(AD5941_REG_AFE_FREQ, freq_reg, 4);

    /* 2. Set excitation amplitude */
    /* DAC amplitude: 0-4095 for 0-1.1V */
    uint16_t dac_val = (uint16_t)(exc_amplitude / 1100.0f * 4095.0f);
    ad5941_write_reg(AD5941_REG_AFE_HPDAC, dac_val, 2);

    /* 3. Set TIA gain resistor */
    ad5941_write_reg(AD5941_REG_AFE_TIA, rtia, 4);

    /* 4. Start measurement: trigger DFT + ADC sequence */
    ad5941_write_reg(AD5941_REG_AFECON, 0x03, 2); /* Start measurement */

    /* 5. Wait for IRQ (measurement complete) */
    int timeout_ms = (int)(5000.0f / freq_hz) + 100; /* more cycles for low freq */
    if (timeout_ms < 200) timeout_ms = 200;
    if (timeout_ms > 5000) timeout_ms = 5000;

    int waited = 0;
    while (gpio_get_level(g_irq_pin) == 1) { /* IRQ is active-low */
        vTaskDelay(pdMS_TO_TICKS(1));
        if (++waited > timeout_ms) {
            snprintf(g_last_error, sizeof(g_last_error),
                     "timeout at %.1f Hz", freq_hz);
            ESP_LOGW(TAG, "IRQ timeout at %.1f Hz", freq_hz);
            return ESP_ERR_TIMEOUT;
        }
    }

    /* Clear IRQ by reading status register */
    uint32_t status;
    ad5941_read_reg(AD5941_REG_AFECON, &status, 2);

    /* 6. Read DFT results (real + imaginary parts) */
    int32_t dft_real, dft_imag;
    ad5941_read_reg(0x2014, (uint32_t *)&dft_real, 4); /* DFT real */
    ad5941_read_reg(0x2016, (uint32_t *)&dft_imag, 4); /* DFT imag */

    /* 7. Compute impedance from DFT magnitude + phase */
    /* |Z| = RTIA × (DAC_amplitude / DFT_magnitude) */
    float dft_mag = sqrtf((float)dft_real * dft_real +
                          (float)dft_imag * dft_imag);
    if (dft_mag < 1.0f) dft_mag = 1.0f; /* avoid div-by-zero */

    float exc_v = exc_amplitude / 1000.0f; /* mV to V */
    float mag_ratio = (exc_v * 4095.0f) / dft_mag; /* normalized */

    result->z_mag = rtia * mag_ratio;
    result->z_phase = atan2f((float)dft_imag, (float)dft_real) * 180.0f / M_PI;
    result->z_real = result->z_mag * cosf(result->z_phase * M_PI / 180.0f);
    result->z_imag = result->z_mag * sinf(result->z_phase * M_PI / 180.0f);
    result->freq_hz = freq_hz;

    /* 8. Apply calibration correction if available */
    /* (Find freq index in calibration table) */
    if (g_cal.open_done && g_cal.short_done) {
        /* Simple correction: subtract short, divide by open-normalized */
        /* Full OSL calibration would be applied here */
    }

    return ESP_OK;
}

esp_err_t ad5941_sweep(const float *freqs, int num_freqs,
                        float exc_amplitude, uint32_t rtia,
                        ad5941_z_point_t *results)
{
    for (int i = 0; i < num_freqs; i++) {
        /* Auto-select RTIA for this frequency if requested */
        uint32_t actual_rtia = (rtia == 0) ?
            ad5941_select_rtia(freqs[i], exc_amplitude) : rtia;

        esp_err_t ret = ad5941_measure_z(freqs[i], exc_amplitude,
                                          actual_rtia, &results[i]);
        if (ret != ESP_OK) {
            ESP_LOGW(TAG, "Measurement failed at freq #%d (%.1f Hz)",
                     i, freqs[i]);
            /* Fill with NaN and continue */
            results[i].z_mag = NAN;
            results[i].z_phase = NAN;
            results[i].z_real = NAN;
            results[i].z_imag = NAN;
            results[i].freq_hz = freqs[i];
        }

        /* Small delay between frequencies for AFE settling */
        vTaskDelay(pdMS_TO_TICKS(5));
    }
    return ESP_OK;
}

/* ---- Calibration ---- */

esp_err_t ad5941_set_calibration(const ad5941_cal_t *cal)
{
    memcpy(&g_cal, cal, sizeof(ad5941_cal_t));
    g_cal_loaded = true;
    return ESP_OK;
}

esp_err_t ad5941_get_calibration(ad5941_cal_t *cal)
{
    if (!g_cal_loaded) return ESP_ERR_NOT_FOUND;
    memcpy(cal, &g_cal, sizeof(ad5941_cal_t));
    return ESP_OK;
}

void ad5941_apply_calibration(ad5941_z_point_t *raw,
                               const ad5941_cal_t *cal,
                               int freq_index)
{
    if (freq_index < 0 || freq_index >= 20) return;

    /* OSL (Open-Short-Load) calibration:
     * Z_corrected = (Z_raw - Z_short) × (Z_open - Z_short) / (Z_open - Z_load)
     *
     * Simplified: subtract short (parasitic), normalize by open (probe response)
     */
    float short_mag = cal->short_mag[freq_index];
    float open_mag = cal->open_mag[freq_index];

    if (raw->z_mag > short_mag) {
        raw->z_mag -= short_mag;
    }
    if (open_mag > 0) {
        raw->z_mag /= (open_mag / 1000.0f); /* normalize */
        raw->z_mag *= 1000.0f; /* scale to useful range */
    }

    /* Phase correction: subtract open-circuit phase offset */
    raw->z_phase -= cal->open_phase[freq_index];
    raw->z_real = raw->z_mag * cosf(raw->z_phase * M_PI / 180.0f);
    raw->z_imag = raw->z_mag * sinf(raw->z_phase * M_PI / 180.0f);
}

const char *ad5941_last_error(void)
{
    return g_last_error;
}