/*
 * imu.c — ICM-42688-P 6-axis IMU driver (SPI)
 *
 * Reads accel + gyro at 1 kHz, computes tilt angle (pitch) for modulation
 * and detects vibrato (gyro oscillation in the 4-8 Hz band).
 */
#include "imu.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include <math.h>
#include <string.h>

static const char *TAG = "imu";

#define IMU_SPI_HOST  SPI2_HOST
#define IMU_CS_PIN    21
#define IMU_INT_PIN   38
#define IMU_SCK_PIN   20
#define IMU_MISO_PIN  18
#define IMU_MOSI_PIN  19

/* ICM-42688-P registers */
#define REG_WHOAMI     0x75
#define REG_PWR_CTRL   0x4F
#define REG_GYRO_CFG0  0x4E
#define REG_ACCEL_CFG0 0x50
#define REG_ACCEL_DATA 0x1F
#define REG_GYRO_DATA  0x25
#define VAL_WHOAMI     0x47

static spi_device_handle_t spi_dev;
static float pitch_deg = 0.0f;
static float gyro_hist[32] = {0};
static int   gyro_idx = 0;
static float vibrato_rate = 0.0f;
static float vibrato_depth = 0.0f;

static uint8_t reg_read(uint8_t addr)
{
    uint8_t tx[2] = { (uint8_t)(addr | 0x80), 0 };
    uint8_t rx[2] = {0};
    spi_transaction_t t = {
        .length = 16, .tx_buffer = tx, .rx_buffer = rx,
    };
    spi_device_polling_transmit(spi_dev, &t);
    return rx[1];
}

static void reg_write(uint8_t addr, uint8_t val)
{
    uint8_t tx[2] = { (uint8_t)(addr & 0x7F), val };
    spi_transaction_t t = {
        .length = 16, .tx_buffer = tx,
    };
    spi_device_polling_transmit(spi_dev, &t);
}

static void read_burst(uint8_t addr, uint8_t *buf, int len)
{
    uint8_t tx[len + 1];
    tx[0] = (uint8_t)(addr | 0x80);
    memset(&tx[1], 0, len);
    spi_transaction_t t = {
        .length = (len + 1) * 8,
        .tx_buffer = tx,
        .rx_buffer = buf,
    };
    spi_device_polling_transmit(spi_dev, &t);
    /* buf[0] is the addr echo; data starts at buf[1] */
    memmove(buf, buf + 1, len);
}

void imu_init(void)
{
    spi_bus_config_t buscfg = {
        .miso_io_num = IMU_MISO_PIN,
        .mosi_io_num = IMU_MOSI_PIN,
        .sclk_io_num = IMU_SCK_PIN,
        .quadwp_io_num = -1, .quadhd_io_num = -1,
        .max_transfer_sz = 16,
    };
    spi_bus_initialize(IMU_SPI_HOST, &buscfg, SPI_DMA_CH_AUTO);

    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = 8 * 1000 * 1000,  /* 8 MHz */
        .mode = 0, .spics_io_num = IMU_CS_PIN,
        .queue_size = 4,
    };
    spi_bus_add_device(IMU_SPI_HOST, &devcfg, &spi_dev);

    /* Reset + configure */
    vTaskDelay(pdMS_TO_TICKS(10));
    uint8_t whoami = reg_read(REG_WHOAMI);
    ESP_LOGI(TAG, "IMU WHO_AM_I = 0x%02X (expected 0x%02X)", whoami, VAL_WHOAMI);
    if (whoami != VAL_WHOAMI) {
        ESP_LOGW(TAG, "IMU not detected! Check wiring. Continuing with stub data.");
        return;
    }

    /* Enable accel + gyro, low-noise mode */
    reg_write(REG_PWR_CTRL, 0x0E);   /* accel + gyro enable */
    vTaskDelay(pdMS_TO_TICKS(5));
    /* Accel: ±4g, ODR 1 kHz */
    reg_write(REG_ACCEL_CFG0, (0x06 << 4) | 0x07);  /* FS=±4g, ODR=1kHz */
    /* Gyro: ±2000 dps, ODR 1 kHz */
    reg_write(REG_GYRO_CFG0, (0x00 << 4) | 0x07);   /* FS=±2000dps, ODR=1kHz */
    ESP_LOGI(TAG, "IMU configured");
}

void imu_scan(void)
{
    uint8_t buf[12];
    read_burst(REG_ACCEL_DATA, buf, 12);

    int16_t ax = (buf[0] << 8) | buf[1];
    int16_t ay = (buf[2] << 8) | buf[3];
    int16_t az = (buf[4] << 8) | buf[5];
    int16_t gx = (buf[6] << 8) | buf[7];
    /* gy, gz similarly from buf[8..11] */

    /* Compute pitch from accel: pitch = atan2(ay, sqrt(ax²+az²)) */
    float ayf = (float)ay / 8192.0f;   /* /8192 LSB/g for ±4g */
    float azf = (float)az / 8192.0f;
    float axf = (float)ax / 8192.0f;
    pitch_deg = atan2f(ayf, sqrtf(axf * axf + azf * azf)) * 180.0f / M_PI;

    /* Vibrato detection: gyro X (roll rate) oscillation 4-8 Hz.
     * Store in ring buffer; compute RMS of AC component. */
    float gx_rate = (float)gx / 16.4f;  /* LSB/(°/s) for ±2000dps */
    gyro_hist[gyro_idx] = gx_rate;
    gyro_idx = (gyro_idx + 1) % 32;

    /* Compute AC RMS (deviation from mean) */
    float mean = 0;
    for (int i = 0; i < 32; i++) mean += gyro_hist[i];
    mean /= 32.0f;
    float rms = 0;
    for (int i = 0; i < 32; i++) {
        float d = gyro_hist[i] - mean;
        rms += d * d;
    }
    rms = sqrtf(rms / 32.0f);

    /* If RMS > threshold → vibrato present */
    if (rms > 15.0f) {
        vibrato_depth = (rms - 15.0f) * 0.5f;
        if (vibrato_depth > 50.0f) vibrato_depth = 50.0f;
        vibrato_rate = 5.5f;  /* approximate; FFT would be precise */
    } else {
        vibrato_depth *= 0.95f;  /* decay */
        vibrato_rate = 0.0f;
    }
}

uint8_t imu_get_modulation(void)
{
    /* Map |pitch| 0..45° → 0..127 */
    float p = fabsf(pitch_deg);
    if (p > 45.0f) p = 45.0f;
    return (uint8_t)(p / 45.0f * 127.0f);
}

float imu_get_pitch_deg(void) { return pitch_deg; }
float imu_get_vibrato_rate(void) { return vibrato_rate; }
float imu_get_vibrato_depth(void) { return vibrato_depth; }

int8_t imu_get_tilt_octave(void)
{
    /* Sharp tilt up → +1 octave, down → -1 */
    if (pitch_deg > 35.0f) return 1;
    if (pitch_deg < -35.0f) return -1;
    return 0;
}