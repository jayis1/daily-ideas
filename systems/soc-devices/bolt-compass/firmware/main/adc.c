/*
 * adc.c — ADS131M04 4-channel 24-bit simultaneous-sampling ADC driver
 *
 * The ADS131M04 is configured for:
 *   - 8 ksps per channel (OSR=512 on the 4.096 MHz modulator clock)
 *   - PGA gain 8 (full-scale ~0.4 V differential — matches the loop
 *     preamp output after a 40 dB gain stage)
 *   - Continuous conversion, DRDY falling edge on a dedicated GPIO.
 *
 * On every DRDY edge, the ESP32 ISR reads 4 x 3 bytes (24-bit signed) +
 * 3 bytes status over SPI at 20 MHz, sign-extends to int16 (scaled by
 * 1/256 to fit the 24-bit range into int16 while preserving ~16 bits of
 * useful dynamic range), and pushes into the PSRAM ring buffer.
 *
 * The ring is a single-producer (ISR) / single-consumer (detector task)
 * lock-free SPSC queue — wr is only written by the ISR, rd only by the
 * detector. This is the same pattern used by the audio DMA rings in
 * Echo Mote (#8) and Aero Reed (#20).
 */
#include "adc.h"
#include "esp_log.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_heap_caps.h"
#include "esp_intr_alloc.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

static const char *TAG = "adc";

#define PIN_SCLK   0
#define PIN_DOUT   1
#define PIN_DIN    2
#define PIN_CS     3
#define PIN_DRDY   4
#define PIN_PWDN   6
#define SPI_HOST   SPI2_HOST

static spi_device_handle_t s_spi;
static ring_t s_ring;
static volatile uint64_t s_last_ts_us;

/* ADS131M04 register writes (simplified — full driver in the real HW). */
#define REG_CLK         0x20
#define REG_MODE        0x21
#define REG_GAIN        0x23   /* PGA gains per channel */
#define REG_OSR         0x24   /* oversampling ratio */

static esp_err_t spi_write_reg(uint8_t addr, uint16_t val)
{
    uint8_t tx[3] = { (uint8_t)(addr | 0x40), (uint8_t)(val >> 8), (uint8_t)val };
    spi_transaction_t t = { .length = 24, .tx_buffer = tx, .flags = SPI_TRANS_USE_RXDATA };
    return spi_device_polling_transmit(s_spi, &t);
}

static void IRAM_ATTR drdy_isr(void *arg)
{
    (void)arg;
    /* Read 12 bytes (4 ch x 24-bit + 3 status) from the ADS131M04. */
    uint8_t rx[15] = {0};
    uint8_t tx[15] = {0};
    spi_transaction_t t = {
        .length = 15 * 8,
        .tx_buffer = tx,
        .rx_buffer = rx,
    };
    spi_device_polling_transmit(s_spi, &t);

    /* Parse 4 x 24-bit signed samples (big-endian). */
    int idx = s_ring.wr;
    for (int c = 0; c < ADC_CH; c++) {
        int32_t v = ((int32_t)rx[1 + c*3] << 16) |
                    ((int32_t)rx[2 + c*3] << 8)  |
                     (int32_t)rx[3 + c*3];
        if (v & 0x800000) v |= 0xFF000000;   /* sign-extend */
        /* Scale 24-bit → int16: shift right 8 (keep top 16 bits). */
        s_ring.buf[idx].ch[c] = (int16_t)(v >> 8);
    }
    s_ring.wr = (idx + 1) & (RING_LEN - 1);
    /* Timestamp: gps_pps_last() + sample-counter * (1e6/ADC_RATE). */
    extern uint64_t gps_pps_last(void);
    extern uint64_t gps_sample_count(void);
    s_last_ts_us = gps_pps_last() +
                   gps_sample_count() * (1000000ULL / ADC_RATE);
    s_ring.ts_us = s_last_ts_us;
}

int adc_init(void)
{
    /* Allocate the ring in PSRAM (4 ch x 2 bytes x 2048 = 16 KB). */
    s_ring.buf = (sample_t *)heap_caps_calloc(RING_LEN, sizeof(sample_t),
                                              MALLOC_CAP_SPIRAM);
    if (!s_ring.buf) {
        ESP_LOGE(TAG, "PSRAM ring alloc failed");
        return -1;
    }
    s_ring.wr = 0;

    /* Configure PWDN pin. */
    gpio_set_direction(PIN_PWDN, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_PWDN, 1);      /* power up */

    /* SPI bus init — 20 MHz, MSB first, mode 1 (CPOL=0, CPHA=1 for ADS131M). */
    spi_bus_config_t buscfg = {
        .miso_io_num = PIN_DOUT,
        .mosi_io_num = PIN_DIN,
        .sclk_io_num = PIN_SCLK,
        .max_transfer_sz = 32,
    };
    ESP_ERROR_CHECK(spi_bus_initialize(SPI_HOST, &buscfg, 1));

    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = 20 * 1000 * 1000,
        .mode = 1,
        .spics_io_num = PIN_CS,
        .queue_size = 2,
        .flags = SPI_DEVICE_HALFDUPLEX,
    };
    ESP_ERROR_CHECK(spi_bus_add_device(SPI_HOST, &devcfg, &s_spi));

    /* Configure the ADS131M04 registers. */
    vTaskDelay(pdMS_TO_TICKS(10));     /* let the ADC settle */
    spi_write_reg(REG_CLK,  0x0001);   /* use internal 8.192 MHz osc */
    spi_write_reg(REG_MODE, 0x0000);   /* continuous, 8 ksps */
    spi_write_reg(REG_GAIN, 0x0808);   /* PGA x8 on ch0/ch1, x8 on ch2/3 */
    spi_write_reg(REG_OSR,  0x0200);   /* OSR=512 → 8 ksps */

    /* DRDY GPIO — falling-edge interrupt. */
    gpio_set_direction(PIN_DRDY, GPIO_MODE_INPUT);
    gpio_set_intr_type(PIN_DRDY, GPIO_INTR_NEGEDGE);
    ESP_ERROR_CHECK(gpio_install_isr_service(0));
    ESP_ERROR_CHECK(gpio_isr_handler_add(PIN_DRDY, drdy_isr, NULL));

    ESP_LOGI(TAG, "ADS131M04 @ 8 ksps, PGA x8, DRDY on GPIO%d", PIN_DRDY);
    return 0;
}

void adc_isr(void) { /* alias for external callers */ }

ring_t *adc_ring(void) { return &s_ring; }

uint64_t adc_snapshot(sample_t *out, int n)
{
    ring_t *r = &s_ring;
    int wr = r->wr;
    int start = (wr - n) & (RING_LEN - 1);
    for (int i = 0; i < n; i++)
        out[i] = r->buf[(start + i) & (RING_LEN - 1)];
    return r->ts_us;
}

void adc_sleep(void)
{
    gpio_set_level(PIN_PWDN, 0);
}

void adc_wake(void)
{
    gpio_set_level(PIN_PWDN, 1);
    vTaskDelay(pdMS_TO_TICKS(5));
}