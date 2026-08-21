/* calibration.c — geometry calibration and zero-wind offset storage
 *
 * Stores per-unit calibration in the RP2040's last flash page:
 *   - 3 path length corrections (mm)
 *   - 3 zero-wind offsets (m/s)
 *   - Magic word for validity check
 *
 * Zero-wind calibration: place the device in still air (indoors,
 * away from HVAC vents), enter calibration mode, and the firmware
 * averages N samples to determine the per-path timing offset.
 */

#include <string.h>
#include <math.h>
#include "pico/stdlib.h"
#include "hardware/flash.h"
#include "hardware/sync.h"
#include "calibration.h"
#include "sonic.h"
#include "sdkconfig.h"

#define CAL_FLASH_OFFSET (PICO_FLASH_SIZE_BYTES - FLASH_SECTOR_SIZE)
#define CAL_MAGIC        0xAEC57A11

typedef struct {
    uint32_t magic;
    float path_length_mm[NUM_PATHS];
    float wind_offset[NUM_PATHS];
    uint32_t crc;
} cal_data_t;

static cal_data_t cal_data;

static uint32_t crc32(const uint8_t *data, int len)
{
    uint32_t crc = 0xFFFFFFFF;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 1)
                crc = (crc >> 1) ^ 0xEDB88320;
            else
                crc >>= 1;
        }
    }
    return ~crc;
}

void cal_init(void)
{
    /* Load from flash */
    const uint8_t *flash_ptr = (const uint8_t *)(XIP_BASE + CAL_FLASH_OFFSET);
    memcpy(&cal_data, flash_ptr, sizeof(cal_data));

    if (cal_data.magic != CAL_MAGIC) {
        /* Not calibrated — use defaults */
        cal_data.magic = CAL_MAGIC;
        for (int i = 0; i < NUM_PATHS; i++) {
            cal_data.path_length_mm[i] = PATH_LENGTH_MM;
            cal_data.wind_offset[i] = 0.0f;
        }
        cal_data.crc = 0;
        printf("[cal] no calibration found, using defaults\n");
    } else {
        printf("[cal] loaded from flash: L0=%.1f L1=%.1f L2=%.1f off0=%.3f off1=%.3f off2=%.3f\n",
               cal_data.path_length_mm[0], cal_data.path_length_mm[1], cal_data.path_length_mm[2],
               cal_data.wind_offset[0], cal_data.wind_offset[1], cal_data.wind_offset[2]);
    }
}

float cal_get_offset(int path_idx)
{
    if (path_idx < 0 || path_idx >= NUM_PATHS) return 0.0f;
    return cal_data.wind_offset[path_idx];
}

void cal_set_offset(int path_idx, float offset)
{
    if (path_idx >= 0 && path_idx < NUM_PATHS)
        cal_data.wind_offset[path_idx] = offset;
}

float cal_get_path_length(int path_idx)
{
    if (path_idx < 0 || path_idx >= NUM_PATHS) return PATH_LENGTH_MM;
    return cal_data.path_length_mm[path_idx];
}

void cal_set_path_length(int path_idx, float length_mm)
{
    if (path_idx >= 0 && path_idx < NUM_PATHS)
        cal_data.path_length_mm[path_idx] = length_mm;
}

bool cal_save(void)
{
    /* Compute CRC */
    cal_data.crc = crc32((uint8_t *)&cal_data, offsetof(cal_data_t, crc));

    /* Write to flash — must disable interrupts and erase sector first */
    uint32_t ints = save_and_disable_interrupts();
    flash_range_erase(CAL_FLASH_OFFSET, FLASH_SECTOR_SIZE);

    /* Write data (padded to FLASH_PAGE_SIZE = 256) */
    uint8_t page_buf[FLASH_PAGE_SIZE];
    memset(page_buf, 0xFF, sizeof(page_buf));
    memcpy(page_buf, &cal_data, sizeof(cal_data));
    flash_range_program(CAL_FLASH_OFFSET, page_buf, FLASH_PAGE_SIZE);

    restore_interrupts(ints);

    printf("[cal] saved to flash\n");
    return true;
}

bool cal_zero_wind(int num_samples)
{
    /* Average N samples to determine path offsets */
    float v_sum[NUM_PATHS] = {0, 0, 0};
    int valid_count = 0;

    printf("[cal] zero-wind: collecting %d samples...\n", num_samples);

    for (int i = 0; i < num_samples; i++) {
        sonic_sample_t sample;
        if (sonic_measure(&sample)) {
            for (int p = 0; p < NUM_PATHS; p++) {
                v_sum[p] += sample.paths[p].v_path;
            }
            valid_count++;
        }
        sleep_ms(1000 / SAMPLE_RATE_HZ);
    }

    if (valid_count < num_samples / 2) {
        printf("[cal] insufficient valid samples (%d/%d)\n", valid_count, num_samples);
        return false;
    }

    for (int p = 0; p < NUM_PATHS; p++) {
        float avg = v_sum[p] / valid_count;
        cal_set_offset(p, avg);
        printf("[cal] path %d offset = %.4f m/s\n", p, avg);
    }

    cal_save();
    printf("[cal] zero-wind calibration complete\n");
    return true;
}

bool cal_is_valid(void)
{
    return cal_data.magic == CAL_MAGIC;
}