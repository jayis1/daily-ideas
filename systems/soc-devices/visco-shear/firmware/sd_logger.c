/*
 * visco-shear / firmware / sd_logger.c
 * MicroSD CSV logging for Visco Shear
 *
 * SPI mode, FAT32 via FatFs (or minimal raw write in skeleton).
 *
 * MIT License.
 */
#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "hardware/spi.h"
#include "main.h"
#include "sd_logger.h"
#include "spindle.h"

static bool sd_ok = false;

void sd_logger_init(void)
{
    /* Init SPI for SD card */
    spi_init(spi1, 4 * 1000 * 1000);  /* 4 MHz */
    gpio_set_function(PIN_SPI_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SPI_MISO, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SPI_MOSI, GPIO_FUNC_SPI);

    gpio_init(PIN_SD_CS);
    gpio_set_dir(PIN_SD_CS, GPIO_OUT);
    gpio_put(PIN_SD_CS, 1);  /* Deselect */

    /* In production: init FatFs here.
     * Skeleton: mark as not fully initialized. */
    printf("[SD] MicroSD SPI initialized (CS=GPIO%d)\n", PIN_SD_CS);
    sd_ok = false;  /* Set true after FatFs mount succeeds */
}

static void sd_write_line(const char *line)
{
    /* In production: f_puts(line, &file) */
    printf("[SD] %s", line);
}

void sd_logger_write_result(const measure_result_t *res)
{
    char buf[128];
    char filename[32];

    /* Generate filename: VS_YYYYMMDD_HHMMSS.csv */
    /* In production: use RTC or GPS time. Skeleton uses timestamp 0. */
    snprintf(filename, sizeof(filename), "VS_%06d_%06d.csv", 0, 0);
    printf("[SD] Writing %s\n", filename);

    snprintf(buf, sizeof(buf), "# Visco Shear measurement log\n");
    sd_write_line(buf);
    snprintf(buf, sizeof(buf), "# Spindle: %s\n", spindle_name(res->spindle));
    sd_write_line(buf);
    snprintf(buf, sizeof(buf), "# Mode: %d\n", res->mode);
    sd_write_line(buf);
    snprintf(buf, sizeof(buf), "# Temperature: %.2f C\n", res->temperature);
    sd_write_line(buf);
    snprintf(buf, sizeof(buf), "# Best model: %s (R2=%.5f)\n",
             model_names[res->best_fit.model], res->best_fit.r_squared);
    sd_write_line(buf);
    snprintf(buf, sizeof(buf), "# Columns: step, omega_rpm, shear_rate_1_s, torque_uNm, viscosity_mPa_s\n");
    sd_write_line(buf);

    for (int i = 0; i < res->n_points; i++) {
        snprintf(buf, sizeof(buf), "%d,%.3f,%.4f,%.2f,%.2f\n",
                 i + 1, res->omega[i], res->shear_rate[i],
                 res->torque[i], res->viscosity[i]);
        sd_write_line(buf);
    }

    /* Oscillatory data */
    if (res->n_freq > 0) {
        snprintf(buf, sizeof(buf), "# Oscillatory: freq_Hz, G_prime_Pa, G_double_prime_Pa, tan_delta, eta_complex_Pa_s\n");
        sd_write_line(buf);
        for (int i = 0; i < res->n_freq; i++) {
            snprintf(buf, sizeof(buf), "%.3f,%.2f,%.2f,%.4f,%.2f\n",
                     res->freq[i], res->G_prime[i], res->G_double[i],
                     res->tan_delta[i], res->eta_complex[i]);
            sd_write_line(buf);
        }
    }

    /* Thixotropy */
    if (res->hysteresis_area > 0) {
        snprintf(buf, sizeof(buf), "# Thixotropy: hysteresis_area=%.2f, recovery_time=%.2f s\n",
                 res->hysteresis_area, res->recovery_time);
        sd_write_line(buf);
    }

    snprintf(buf, sizeof(buf), "# END\n");
    sd_write_line(buf);
    printf("[SD] Log complete\n");
}

void sd_logger_write_osc(const measure_result_t *res)
{
    /* Oscillatory data is written as part of write_result */
    (void)res;
}