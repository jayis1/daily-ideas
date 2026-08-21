/*
 * Levia Forge — SD Card Logging (SPI0)
 * Logs trap position, particle height, pattern, and power at 10 Hz.
 *
 * SPDX-License-Identifier: MIT
 */
#include "sd_log.h"
#include "sdkconfig.h"
#include "pico/stdlib.h"
#include "hardware/spi.h"
#include <stdio.h>
#include <string.h>

#define SD_MOUNT_OK   0

static bool initialized = false;
static int log_counter = 0;
static char current_filename[32];

/* Simplified SD card SPI interface.
 * In production, use the pico-sdcard library or FatFs.
 * This is a skeleton that writes raw SPI commands. */

static void sd_spi_init(void)
{
    spi_init(spi0, 1000 * 1000);  /* 1 MHz for initialization */
    gpio_set_function(PIN_SPI_SCK,  GPIO_FUNC_SPI);
    gpio_set_function(PIN_SPI_MOSI, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SPI_MISO, GPIO_FUNC_SPI);
    gpio_init(PIN_SPI_CS);
    gpio_set_dir(PIN_SPI_CS, GPIO_OUT);
    gpio_put(PIN_SPI_CS, 1);  /* Deselect */
}

static bool sd_send_cmd(uint8_t cmd, uint32_t arg, uint8_t crc, uint8_t *response)
{
    uint8_t tx[6] = { cmd | 0x40, (arg >> 24) & 0xFF, (arg >> 16) & 0xFF,
                      (arg >> 8) & 0xFF, arg & 0xFF, crc };
    uint8_t rx[6];

    gpio_put(PIN_SPI_CS, 0);  /* Select */
    spi_write_blocking(spi0, tx, 6);

    /* Wait for response (0xFF means busy) */
    for (int i = 0; i < 10; i++) {
        spi_read_blocking(spi0, 0xFF, rx, 1);
        if (rx[0] != 0xFF) {
            if (response) *response = rx[0];
            gpio_put(PIN_SPI_CS, 1);
            return true;
        }
    }
    gpio_put(PIN_SPI_CS, 1);
    return false;
}

static bool sd_init_card(void)
{
    uint8_t response;
    /* Send 80 dummy clocks with CS high to enter SPI mode */
    gpio_put(PIN_SPI_CS, 1);
    uint8_t dummy[10];
    memset(dummy, 0xFF, sizeof(dummy));
    spi_write_blocking(spi0, dummy, 10);

    /* CMD0: GO_IDLE_STATE */
    if (!sd_send_cmd(0, 0, 0x95, &response) || response != 0x01)
        return false;

    /* CMD8: SEND_IF_COND (check voltage) */
    if (!sd_send_cmd(8, 0x000001AA, 0x87, &response))
        return false;

    /* CMD55 + ACMD41: SD_SEND_OP_COND (initialize) */
    for (int i = 0; i < 100; i++) {
        sd_send_cmd(55, 0, 0xFF, &response);
        sd_send_cmd(41, 0x40000000, 0xFF, &response);
        if (response == 0x00)
            break;
        sleep_ms(10);
    }
    if (response != 0x00)
        return false;

    /* CMD16: SET_BLOCKLEN to 512 */
    sd_send_cmd(16, 512, 0xFF, &response);

    /* Increase SPI clock to 10 MHz */
    spi_set_baudrate(spi0, 10000000);

    return true;
}

void sd_log_init(void)
{
    sd_spi_init();
    if (sd_init_card()) {
        initialized = true;
        /* Generate filename based on boot count (simplified: always session.csv) */
        snprintf(current_filename, sizeof(current_filename), "levia_%d.csv",
                 log_counter);
        /* In a full implementation, we'd use FatFs to create the file
         * and write a CSV header. For now, log to UART as fallback. */
        printf("[SD] Card initialized, logging to %s\n", current_filename);
        printf("[SD] header: time_ms,pattern,x,y,z,particle_mm,bat_mv,temp_c,safety\n");
    } else {
        initialized = false;
        printf("[SD] No SD card detected, logging to UART only\n");
    }
}

/* State struct for logging (same layout as display_state_t) */
typedef struct {
    float target_x, target_y, target_z;
    float actual_x, actual_y, actual_z;
    int pattern;
    int vortex_charge;
    float twin_delta;
    float bend_gradient;
    float transport_progress;
    float transport_speed;
    bool active;
    bool particle_detected;
    float particle_height_mm;
    int battery_mv;
    float temp_c;
    int safety;
    uint32_t uptime_ms;
    bool auto_track_z;
} log_state_t;

void sd_log_write(void *state_ptr)
{
    log_state_t *s = (log_state_t *)state_ptr;

    /* Format CSV line */
    printf("LOG,%lu,%d,%.1f,%.1f,%.1f,%.1f,%d,%.0f,%d\n",
           (unsigned long)s->uptime_ms,
           s->pattern,
           s->actual_x, s->actual_y, s->actual_z,
           s->particle_detected ? s->particle_height_mm : -1.0f,
           s->battery_mv,
           s->temp_c,
           s->safety);

    /* In a full implementation with FatFs:
     * - Open file in append mode
     * - Write CSV line
     * - Close file (or flush periodically)
     */
    if (initialized) {
        /* TODO: FatFs f_open, f_printf, f_close */
    }

    log_counter++;
}