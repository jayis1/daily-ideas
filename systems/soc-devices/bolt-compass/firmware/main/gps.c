/*
 * gps.c — NEO-M9N UART parser + PPS microsecond time-tagging
 *
 * The NEO-M9N sends UBX/nav-pvt solutions at 1 Hz over UART1 and a 1 Hz
 * PPS on a GPIO. We capture the PPS edge timestamp (esp_timer_get_us())
 * and reset the sample counter; the ADC ISR increments the sample counter
 * once per 8 ksps sample. A sferic's timestamp is then:
 *
 *   ts = gps_pps_last_us + sample_count_at_trigger * (1e6 / 8000)
 *
 * giving microsecond-accurate, GPS-locked time for every stroke, suitable
 * for cross-correlation with the Blitzortung network.
 */
#include "gps.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>

static const char *TAG = "gps";

#define UART_PORT   UART_NUM_1
#define PIN_TX       8
#define PIN_RX       9
#define PIN_PPS      7
#define BUF_SIZE     256

static volatile uint64_t s_pps_us;
static volatile uint64_t s_sample_count;
static volatile int      s_fix_valid;
static int32_t s_lat_e7, s_lon_e7, s_alt_cm;

static void IRAM_ATTR pps_isr(void *arg)
{
    (void)arg;
    s_pps_us = (uint64_t)esp_timer_get_time();
    s_sample_count = 0;
}

uint64_t gps_pps_last(void)      { return s_pps_us; }
uint64_t gps_sample_count(void)  { return s_sample_count; }
void     gps_tick_sample(void)   { s_sample_count++; }
int      gps_fix_valid(void)     { return s_fix_valid; }

void gps_position(int32_t *lat_e7, int32_t *lon_e7, int32_t *alt_cm)
{
    *lat_e7 = s_lat_e7; *lon_e7 = s_lon_e7; *alt_cm = s_alt_cm;
}

/* Minimal UBX parser — look for the nav-pvt (0x01 0x07) message. */
static void parse_ubx(const uint8_t *buf, int len)
{
    for (int i = 0; i + 9 < len; i++) {
        if (buf[i] == 0xB5 && buf[i+1] == 0x62 &&
            buf[i+2] == 0x01 && buf[i+3] == 0x07) {
            int payload_len = (buf[i+5] << 8) | buf[i+4];
            if (i + 6 + payload_len + 2 > len) break;
            const uint8_t *p = buf + i + 6;
            /* nav-pvt fields (UBX protocol v27): */
            uint8_t fix_type = p[21];
            s_fix_valid = (fix_type >= 2);   /* 2 = 2D, 3 = 3D */
            s_lat_e7 = (int32_t)(p[30] | (p[31]<<8) | (p[32]<<16) | (p[33]<<24));
            s_lon_e7 = (int32_t)(p[34] | (p[35]<<8) | (p[36]<<16) | (p[37]<<24));
            s_alt_cm = (int32_t)(p[38] | (p[39]<<8) | (p[40]<<16) | (p[41]<<24));
            ESP_LOGD(TAG, "fix=%d lat=%.7f lon=%.7f alt=%.2f",
                     fix_type, s_lat_e7/1e7, s_lon_e7/1e7, s_alt_cm/100.0);
            return;
        }
    }
}

static void gps_task(void *arg)
{
    (void)arg;
    uint8_t buf[BUF_SIZE];
    for (;;) {
        int len = uart_read_bytes(UART_PORT, buf, BUF_SIZE - 1, pdMS_TO_TICKS(100));
        if (len > 0) parse_ubx(buf, len);
    }
}

void gps_init(void)
{
    uart_config_t cfg = {
        .baud_rate  = 38400,
        .data_bits  = UART_DATA_8_BITS,
        .parity     = UART_PARITY_DISABLE,
        .stop_bits  = UART_STOP_BITS_1,
        .source_clk = UART_SCLK_DEFAULT,
    };
    uart_driver_install(UART_PORT, BUF_SIZE * 2, 0, 0, NULL, 0);
    uart_param_config(UART_PORT, &cfg);
    uart_set_pin(UART_PORT, PIN_TX, PIN_RX, -1, -1);

    gpio_set_direction(PIN_PPS, GPIO_MODE_INPUT);
    gpio_set_intr_type(PIN_PPS, GPIO_INTR_POSEDGE);
    gpio_isr_handler_add(PIN_PPS, pps_isr, NULL);

    xTaskCreatePinnedToCore(gps_task, "gps", 4096, NULL, 4, NULL, 0);
    ESP_LOGI(TAG, "NEO-M9N UART1 @ 38400, PPS on GPIO%d", PIN_PPS);
}