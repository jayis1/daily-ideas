/* sd_log.c — microSD card CSV logging via SPI
 *
 * Uses a simple SPI + FAT-independent raw block write approach.
 * In production, link against FatFs (f_write/f_open) for full FAT32.
 * This implementation writes CSV data to a raw log file using
 * a FatFs-like minimal interface. For the reference firmware,
 * we provide a thin wrapper that can be connected to FatFs.
 */

#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "hardware/spi.h"
#include "hardware/gpio.h"
#include "sd_log.h"
#include "sdkconfig.h"

/* FatFs integration point — in the real build, include ff.h here */
/* #include "ff.h" */
/* #include "diskio.h" */

/* For this reference, we define a minimal interface */
typedef int FRESULT;
typedef void FIL;
#define FR_OK 0

static bool sd_initialized = false;
static bool log_open = false;
static char log_filename[32];
static char write_buf[SD_BUFFER_SIZE];
static int write_buf_pos = 0;
static uint32_t log_count = 0;

/* Placeholder FatFs functions — real build links FatFs */
static FRESULT f_open_stub(FIL *f, const char *path, const char *mode) { (void)f; (void)path; (void)mode; return FR_OK; }
static FRESULT f_write_stub(FIL *f, const void *buf, uint32_t len, uint32_t *bw) { (void)f; (void)buf; (void)len; if(bw) *bw = len; return FR_OK; }
static FRESULT f_close_stub(FIL *f) { (void)f; return FR_OK; }

static FIL log_file;

static void spi_init_sd(void)
{
    spi_init(spi1, 4000000);  /* 4 MHz initially, can go to 25 MHz */
    gpio_set_function(PIN_SPI_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SPI_MOSI, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SPI_MISO, GPIO_FUNC_SPI);
    gpio_init(PIN_SD_CS);
    gpio_set_dir(PIN_SD_CS, GPIO_OUT);
    gpio_put(PIN_SD_CS, 1);  /* deassert */
}

static void sd_select(void)
{
    gpio_put(PIN_SD_CS, 0);
    sleep_us(1);
}

static void sd_deselect(void)
{
    gpio_put(PIN_SD_CS, 1);
    sleep_us(10);
}

/* Send SPI command to SD card (SPI mode initialization) */
static uint8_t sd_cmd(uint8_t cmd, uint32_t arg, uint8_t crc)
{
    uint8_t buf[6];
    buf[0] = cmd | 0x40;
    buf[1] = (arg >> 24) & 0xFF;
    buf[2] = (arg >> 16) & 0xFF;
    buf[3] = (arg >> 8) & 0xFF;
    buf[4] = arg & 0xFF;
    buf[5] = crc;

    sd_select();
    spi_write_blocking(spi1, buf, 6);

    /* Wait for response (0xFF until ready) */
    uint8_t resp = 0xFF;
    for (int i = 0; i < 100; i++) {
        spi_read_blocking(spi1, 0xFF, &resp, 1);
        if (resp != 0xFF) break;
    }
    sd_deselect();
    return resp;
}

bool sd_present(void)
{
    /* Check card detect — simplified: always return true if initialized */
    return sd_initialized;
}

bool sd_init(void)
{
    spi_init_sd();

    /* SD card SPI initialization sequence */
    sd_deselect();
    /* Send 80 dummy clocks */
    uint8_t dummy = 0xFF;
    for (int i = 0; i < 10; i++)
        spi_write_blocking(spi1, &dummy, 1);

    /* CMD0: GO_IDLE_STATE */
    uint8_t r = sd_cmd(0, 0, 0x95);
    if (r != 0x01) {
        printf("[sd] CMD0 failed: 0x%02X\n", r);
        return false;
    }

    /* CMD8: SEND_IF_COND (check version) */
    r = sd_cmd(8, 0x000001AA, 0x87);

    /* CMD55 + ACMD41: SD_SEND_OP_COND */
    for (int i = 0; i < 1000; i++) {
        sd_cmd(55, 0, 0);
        r = sd_cmd(41, 0, 0);
        if (r == 0x00) break;
        sleep_ms(10);
    }

    if (r != 0x00) {
        printf("[sd] init timeout\n");
        return false;
    }

    sd_initialized = true;
    printf("[sd] card initialized\n");
    return true;
}

bool sd_open_log(void)
{
    if (!sd_initialized) return false;

    /* Generate filename from boot timestamp */
    uint32_t ts = time_us_32();
    snprintf(log_filename, sizeof(log_filename), "aero_%lu.csv", ts / 1000000);

    FRESULT fr = f_open_stub(&log_file, log_filename, "w");
    if (fr != FR_OK) {
        printf("[sd] failed to open %s\n", log_filename);
        return false;
    }

    /* Write CSV header */
    const char *header = "timestamp_us,speed,direction,u,v,w,t_sonic,"
                         "bme_temp,bme_press,bme_rh,path0_fwd,path0_rev,"
                         "path1_fwd,path1_rev,path2_fwd,path2_rev\n";
    write_buf_pos = 0;
    strncpy(write_buf, header, SD_BUFFER_SIZE - 1);
    write_buf_pos = strlen(write_buf);

    log_open = true;
    log_count = 0;
    printf("[sd] logging to %s\n", log_filename);
    return true;
}

static void sd_flush_buf(void)
{
    if (write_buf_pos > 0 && log_open) {
        uint32_t bw = 0;
        f_write_stub(&log_file, write_buf, write_buf_pos, &bw);
        write_buf_pos = 0;
    }
}

void sd_log_wind(const sonic_sample_t *sonic, const wind_vector_t *wind,
                 const bme280_data_t *atm)
{
    if (!log_open) return;

    char line[256];
    int len = snprintf(line, sizeof(line),
        "%lu,%.2f,%.1f,%.3f,%.3f,%.3f,%.2f,%.2f,%.0f,%.1f,"
        "%.1f,%.1f,%.1f,%.1f,%.1f,%.1f\n",
        sonic->timestamp_us,
        wind->speed, wind->direction,
        wind->u, wind->v, wind->w,
        wind->t_sonic - 273.15f,
        atm ? atm->temperature : 0.0f,
        atm ? atm->pressure : 0.0f,
        atm ? atm->humidity : 0.0f,
        sonic->paths[0].t_forward_us, sonic->paths[0].t_reverse_us,
        sonic->paths[1].t_forward_us, sonic->paths[1].t_reverse_us,
        sonic->paths[2].t_forward_us, sonic->paths[2].t_reverse_us
    );

    if (write_buf_pos + len >= SD_BUFFER_SIZE) {
        sd_flush_buf();
    }

    if (write_buf_pos + len < SD_BUFFER_SIZE) {
        memcpy(&write_buf[write_buf_pos], line, len);
        write_buf_pos += len;
        log_count++;
    }
}

void sd_log_turbulence(const turbulence_stats_t *stats, uint32_t elapsed_s)
{
    if (!log_open) return;

    char line[256];
    int len = snprintf(line, sizeof(line),
        "TURB,%lu,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%lu\n",
        time_us_32(),
        stats->u_mean, stats->v_mean, stats->w_mean,
        stats->sigma_u, stats->sigma_v, stats->sigma_w,
        stats->u_w_cov, stats->v_w_cov,
        stats->tke, stats->u_star,
        elapsed_s
    );

    if (write_buf_pos + len >= SD_BUFFER_SIZE) {
        sd_flush_buf();
    }
    if (write_buf_pos + len < SD_BUFFER_SIZE) {
        memcpy(&write_buf[write_buf_pos], line, len);
        write_buf_pos += len;
    }
}

void sd_close_log(void)
{
    if (!log_open) return;
    sd_flush_buf();
    f_close_stub(&log_file);
    log_open = false;
    printf("[sd] closed %s (%lu records)\n", log_filename, log_count);
}