/* tcd.c — ADS122U04 24-bit ADC driver + TCD bridge sampling
 *
 * SPI register map (ADS122U04):
 *   Reg 0: Config   — input mux (AINp=AIN0, AINn=AIN1), gain=1, PGA bypass
 *   Reg 1: Config1  — data rate 50 SPS, conversion mode continuous,
 *                      temperature sensor off, voltage ref = external (1.8V)
 *   Reg 2: Config2  — IDAC current = 50 µA on AIN0/AIN1 (excitation)
 *   Reg 3: Config3  — DRDY pin on DOUT/DRDY
 *
 * The MEMS TCD bridge is excited by the IDAC (50 µA) through the two
 * filaments. The differential output (AIN0 – AIN1) is digitized at 50 Hz.
 * A running-minimum baseline over a 5 s window subtracts slow drift.
 */
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_timer.h"

#include "sdkconfig.h"
#include "tcd.h"

static const char *TAG = "tcd";

/* ---- Pin map (SPI1 = ADS122U04) ---- */
#define TCD_SPI_HOST    SPI2_HOST
#define TCD_PIN_CS      8
#define TCD_PIN_SCLK    9
#define TCD_PIN_MISO    10
#define TCD_PIN_MOSI    18
#define TCD_PIN_DRDY    19

/* ADS122U04 commands */
#define ADS_CMD_RESET    0x06
#define ADS_CMD_START    0x08
#define ADS_CMD_POWERDN  0x02
#define ADS_CMD_RDATA    0x10
#define ADS_CMD_RREG     0x20   /* + reg<<2 */
#define ADS_CMD_WREG     0x40   /* + reg<<2 */

/* Ring buffer for samples */
#define TCD_RING_SIZE    256
static tcd_sample_t s_ring[TCD_RING_SIZE];
static volatile int s_ring_head = 0;
static volatile int s_ring_tail = 0;
static QueueHandle_t s_drdy_queue;

/* Baseline tracker */
#define BASELINE_WINDOW_S    5
#define BASELINE_WINDOW_LEN  (BASELINE_WINDOW_S * PLUME_TCD_SAMPLE_HZ)
static int32_t s_baseline_buf[BASELINE_WINDOW_LEN];
static int     s_baseline_idx = 0;
static int     s_baseline_filled = 0;
static float   s_current_baseline = 0.0f;
static float   s_noise_sigma = 5.0f;  /* µV, initial estimate */

static spi_device_handle_t s_spi;

/* ---- SPI transaction helpers ---- */
static void ads_write_reg(uint8_t reg, uint8_t val)
{
    uint8_t cmd[2] = { ADS_CMD_WREG | (reg << 2), val };
    spi_transaction_t t = { 0 };
    t.length = 16;
    t.tx_buffer = cmd;
    spi_device_polling_transmit(s_spi, &t);
}

static uint8_t ads_read_reg(uint8_t reg)
{
    uint8_t cmd[2] = { ADS_CMD_RREG | (reg << 2), 0 };
    uint8_t rx[2] = { 0 };
    spi_transaction_t t = { 0 };
    t.length = 16;
    t.tx_buffer = cmd;
    t.rx_buffer = rx;
    spi_device_polling_transmit(s_spi, &t);
    vTaskDelay(1);
    /* Second read returns the register value */
    t.tx_buffer = NULL;
    uint8_t dummy = 0;
    t.tx_buffer = &dummy;
    t.length = 8;
    t.rx_buffer = rx;
    spi_device_polling_transmit(s_spi, &t);
    return rx[0];
}

static int32_t ads_read_data(void)
{
    /* 24-bit signed conversion result */
    uint8_t cmd = ADS_CMD_RDATA;
    spi_transaction_t t = { 0 };
    t.length = 8;
    t.tx_buffer = &cmd;
    spi_device_polling_transmit(s_spi, &t);
    vTaskDelay(1);

    uint8_t rx[3] = { 0 };
    t.length = 24;
    t.tx_buffer = NULL;
    t.rx_buffer = rx;
    spi_device_polling_transmit(s_spi, &t);

    int32_t raw = ((int32_t)rx[0] << 16) | ((int32_t)rx[1] << 8) | rx[2];
    if (raw & 0x800000) raw |= 0xFF000000;  /* sign-extend */
    return raw;
}

/* ---- DRDY ISR ---- */
static void IRAM_ATTR drdy_isr(void *arg)
{
    int dummy = 1;
    BaseType_t hp = pdFALSE;
    xQueueSendFromISR(s_drdy_queue, &dummy, &hp);
    if (hp) portYIELD_FROM_ISR();
}

/* ---- Sampling task ---- */
static void tcd_sample_task(void *arg)
{
    ESP_LOGI(TAG, "TCD sample task started");
    int sigma_count = 0;
    float sigma_acc = 0.0f;

    while (1) {
        int dummy;
        if (xQueueReceive(s_drdy_queue, &dummy, portMAX_DELAY) != pdPASS)
            continue;

        int32_t raw = ads_read_data();
        /* Convert to µV: Vref=1.8V, gain=1, 24-bit → LSB = 1.8V / 2^23 = 0.2148 µV */
        float uv = (float)raw * 0.2148f;
        int32_t uv_i = (int32_t)uv;

        /* Update baseline (running minimum over window) */
        s_baseline_buf[s_baseline_idx] = uv_i;
        s_baseline_idx = (s_baseline_idx + 1) % BASELINE_WINDOW_LEN;
        if (s_baseline_idx == 0) s_baseline_filled = 1;

        /* Compute min over filled portion */
        int32_t minval = s_baseline_buf[0];
        int n = s_baseline_filled ? BASELINE_WINDOW_LEN : s_baseline_idx;
        for (int i = 0; i < n; i++) {
            if (s_baseline_buf[i] < minval) minval = s_baseline_buf[i];
        }
        s_current_baseline = (float)minval;

        /* Noise sigma estimate: stdev of recent baseline */
        sigma_acc += uv;
        sigma_count++;
        if (sigma_count >= 64) {
            float mean = sigma_acc / sigma_count;
            float var = 0;
            int cnt = s_baseline_filled ? BASELINE_WINDOW_LEN : s_baseline_idx;
            int start = s_baseline_filled ? s_baseline_idx : 0;
            for (int i = 0; i < cnt && i < 64; i++) {
                float d = (float)s_baseline_buf[(start + i) % BASELINE_WINDOW_LEN] - mean;
                var += d * d;
            }
            s_noise_sigma = sqrtf(var / (cnt > 0 ? cnt : 1));
            sigma_acc = 0;
            sigma_count = 0;
        }

        /* Store in ring buffer */
        tcd_sample_t *s = &s_ring[s_ring_head];
        s->microvolts = uv_i;
        s->baseline_uv = s_current_baseline;
        s->corrected_uv = (float)uv_i - s_current_baseline;
        s->timestamp_us = esp_timer_get_time();
        s_ring_head = (s_ring_head + 1) % TCD_RING_SIZE;
        if (s_ring_head == s_ring_tail)
            s_ring_tail = (s_ring_tail + 1) % TCD_RING_SIZE; /* overwrite oldest */
    }
}

/* ---- Public API ---- */
void tcd_init(void)
{
    ESP_LOGI(TAG, "Initializing ADS122U04 over SPI");

    spi_bus_config_t buscfg = {
        .miso_io_num = TCD_PIN_MISO,
        .mosi_io_num = TCD_PIN_MOSI,
        .sclk_io_num = TCD_PIN_SCLK,
        .max_transfer_sz = 32,
    };
    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = 4000000,
        .mode = 1,            /* ADS122U04: CPOL=0, CPHA=1 */
        .spics_io_num = TCD_PIN_CS,
        .queue_size = 4,
    };
    spi_bus_initialize(TCD_SPI_HOST, &buscfg, SPI_DMA_CH_AUTO);
    spi_bus_add_device(TCD_SPI_HOST, &devcfg, &s_spi);

    /* DRDY interrupt */
    gpio_config_t io = {
        .pin_bit_mask = (1ULL << TCD_PIN_DRDY),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    gpio_config(&io);
    s_drdy_queue = xQueueCreate(8, sizeof(int));
    gpio_install_isr_service(0);
    gpio_isr_handler_add(TCD_PIN_DRDY, drdy_isr, NULL);

    /* Reset and configure ADS122U04 */
    uint8_t reset = ADS_CMD_RESET;
    spi_transaction_t t = { .length = 8, .tx_buffer = &reset };
    spi_device_polling_transmit(s_spi, &t);
    vTaskDelay(pdMS_TO_TICKS(50));

    /* Reg 0: Mux AIN0/AIN1, gain=1, PGA bypass */
    ads_write_reg(0, 0x01);  /* MUX[2:0]=001 (AIN0-AIN1), gain=1 */
    /* Reg 1: 50 SPS, continuous, external ref */
    ads_write_reg(1, 0x04);  /* DR=50SPS, CM=continuous, VREF=external */
    /* Reg 2: IDAC 50µA on AIN0/AIN1 */
    ads_write_reg(2, 0x09);  /* IDAC=50µA, I1MUX=AIN0, I2MUX=AIN1 */
    /* Reg 3: DRDY on DOUT */
    ads_write_reg(3, 0x00);

    ESP_LOGI(TAG, "ADS122U04 configured: reg0=0x%02x reg1=0x%02x reg2=0x%02x reg3=0x%02x",
             ads_read_reg(0), ads_read_reg(1), ads_read_reg(2), ads_read_reg(3));
}

void tcd_start(void)
{
    ads_write_reg(1, 0x04);  /* continuous mode */
    uint8_t start = ADS_CMD_START;
    spi_transaction_t t = { .length = 8, .tx_buffer = &start };
    spi_device_polling_transmit(s_spi, &t);
    xTaskCreate(tcd_sample_task, "tcd_sample", 4096, NULL, 10, NULL);
}

void tcd_stop(void)
{
    uint8_t pwdn = ADS_CMD_POWERDN;
    spi_transaction_t t = { .length = 8, .tx_buffer = &pwdn };
    spi_device_polling_transmit(s_spi, &t);
}

bool tcd_read(tcd_sample_t *out)
{
    if (s_ring_head == s_ring_tail) return false;
    *out = s_ring[s_ring_tail];
    s_ring_tail = (s_ring_tail + 1) % TCD_RING_SIZE;
    return true;
}

int tcd_read_batch(tcd_sample_t *buf, int max)
{
    int count = 0;
    while (count < max && s_ring_head != s_ring_tail) {
        buf[count] = s_ring[s_ring_tail];
        s_ring_tail = (s_ring_tail + 1) % TCD_RING_SIZE;
        count++;
    }
    return count;
}

float tcd_noise_sigma(void) { return s_noise_sigma; }

void tcd_reset_baseline(void)
{
    s_baseline_idx = 0;
    s_baseline_filled = 0;
    s_current_baseline = 0.0f;
}