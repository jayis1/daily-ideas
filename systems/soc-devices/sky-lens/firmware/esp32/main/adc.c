/*
 * adc.c — ADS7946 dual 14-bit SAR ADC driver (pulse-height capture)
 *
 * The ADS7946 is a 14-bit, 1 Msps, dual-channel SAR ADC with an SPI
 * interface. On a coincidence trigger, we assert CONVST, wait for the
 * conversion, and read both channels. The ADC samples the peak-hold
 * output of each TIA, which holds the SiPM pulse peak.
 *
 * Simulation: port_sim_adc_read() returns synthetic pulse heights.
 */
#include "adc.h"
#include "sky_lens.h"

#ifdef SKY_LENS_SIM
#include "port_sim.h"
#else
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_log.h"
static const char *TAG = "adc";
#define ADC_HOST     SPI2_HOST
#define PIN_SCK      4
#define PIN_CS       5
#define PIN_MISO     6
#define PIN_MOSI     7
#define PIN_CONVST   8
static spi_device_handle_t s_spi;
#endif

static bool s_ready = false;

void adc_init(void)
{
#ifdef SKY_LENS_SIM
    port_sim_log("adc init (sim)");
    s_ready = true;
#else
    /* SPI bus + device config for the ADS7946 */
    spi_bus_config_t buscfg = {
        .miso_io_num = PIN_MISO,
        .mosi_io_num = PIN_MOSI,
        .sclk_io_num = PIN_SCK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 8,
    };
    spi_bus_initialize(ADC_HOST, &buscfg, SPI_DMA_CH_AUTO);
    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = 40 * 1000 * 1000,   /* 40 MHz */
        .mode = 0,
        .spics_io_num = PIN_CS,
        .queue_size = 4,
    };
    spi_bus_add_device(ADC_HOST, &devcfg, &s_spi);
    gpio_set_direction(PIN_CONVST, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_CONVST, 1);
    s_ready = true;
    ESP_LOGI(TAG, "ADS7946 init (SPI @ 40 MHz)");
#endif
}

void adc_deinit(void)
{
    s_ready = false;
}

/* Trigger a conversion and read both channels.
 * Returns heights in millivolts (0..4500 mV for a 4.5 V reference).
 *
 * The ADS7946 protocol:
 *   - Pull CONVST low to start a conversion on both channels.
 *   - Wait ~1 µs for conversion complete.
 *   - Read 14 bits on CH0, then 14 bits on CH1 over SPI.
 *
 * Full bit-banging of the ADS7946 protocol is omitted; this shows the
 * call structure and the conversion to millivolts.
 */
void adc_trigger_and_read(int16_t *h0_mv, int16_t *h1_mv)
{
    if (!s_ready) {
        *h0_mv = *h1_mv = 0;
        return;
    }

#ifdef SKY_LENS_SIM
    /* Sim: ask the simulator for synthetic heights */
    port_sim_adc_read(h0_mv, h1_mv);
#else
    /* Real: trigger + read over SPI */
    uint16_t raw0, raw1;
    gpio_set_level(PIN_CONVST, 0);            /* start conversion */
    esp_rom_delay_us(2);                      /* ~1 µs conversion */
    gpio_set_level(PIN_CONVST, 1);

    /* Read CH0 (command 0x00) and CH1 (command 0x10) — simplified */
    uint8_t tx[3] = {0x00, 0x00, 0x00};
    uint8_t rx[3] = {0};
    spi_transaction_t t = {
        .length = 24,
        .tx_buffer = tx,
        .rx_buffer = rx,
    };
    spi_device_polling_transmit(s_spi, &t);
    raw0 = ((uint16_t)(rx[0] & 0x3F) << 8) | rx[1];
    spi_device_polling_transmit(s_spi, &t);   /* CH1 */
    raw1 = ((uint16_t)(rx[0] & 0x3F) << 8) | rx[1];

    /* Convert to millivolts (4.5 V ref, 14-bit → 16384 codes) */
    *h0_mv = (int16_t)((uint32_t)raw0 * 4500 / 16384);
    *h1_mv = (int16_t)((uint32_t)raw1 * 4500 / 16384);
    ESP_LOGD(TAG, "h0=%d mV, h1=%d mV", *h0_mv, *h1_mv);
#endif
}