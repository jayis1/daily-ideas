/*
 * dent-scope / Core/Src/imu.c
 * Dent Scope — ICM-42688-P 6-axis IMU driver (SPI2) for leveling
 *
 * The IMU ensures the indentation axis is within ±2° of the surface
 * normal. We read the accelerometer and compute tilt from gravity.
 *
 * MIT License.
 */
#include "imu.h"

#define ICM42688_WHOAMI  0x47
#define ICM42688_REG_WHOAMI    0x75
#define ICM42688_REG_PWR_MGMT0 0x4F
#define ICM42688_REG_ACCEL_DATA_X1 0x1F
#define ICM42688_REG_ACCEL_CONFIG 0x1D

static float tilt_deg = 0.0f;

static void spi_cs_low(void)  { HAL_GPIO_WritePin(IMU_CS_PORT, IMU_CS_PIN, GPIO_PIN_RESET); }
static void spi_cs_high(void) { HAL_GPIO_WritePin(IMU_CS_PORT, IMU_CS_PIN, GPIO_PIN_SET); }

static uint8_t imu_read_reg(uint8_t reg)
{
    uint8_t tx[2] = {reg | 0x80, 0x00};
    uint8_t rx[2] = {0, 0};
    spi_cs_low();
    HAL_SPI_TransmitReceive(&hspi2, tx, rx, 2, 50);
    spi_cs_high();
    return rx[1];
}

static void imu_write_reg(uint8_t reg, uint8_t val)
{
    uint8_t tx[2] = {reg & 0x7F, val};
    spi_cs_low();
    HAL_SPI_Transmit(&hspi2, tx, 2, 50);
    spi_cs_high();
}

void imu_init(void)
{
    uint8_t who = imu_read_reg(ICM42688_REG_WHOAMI);
    (void)who; /* could verify == ICM42688_WHOAMI */
    /* power on: LN mode */
    imu_write_reg(ICM42688_REG_PWR_MGMT0, 0x0C); /* accel LN, gyro off */
    HAL_Delay(2);
    /* accel config: ODR=1kHz, range=±2g, UI filter */
    imu_write_reg(ICM42688_REG_ACCEL_CONFIG, 0x06); /* ±2g, ODR 1kHz */
    HAL_Delay(10);
}

float imu_get_tilt_deg(void)
{
    /* read 6 bytes of accel data */
    int16_t ax = (int16_t)((imu_read_reg(ICM42688_REG_ACCEL_DATA_X1) << 8) |
                            imu_read_reg(ICM42688_REG_ACCEL_DATA_X0));
    int16_t ay = (int16_t)((imu_read_reg(0x21) << 8) | imu_read_reg(0x20));
    int16_t az = (int16_t)((imu_read_reg(0x23) << 8) | imu_read_reg(0x22));

    /* convert to g (±2g range, 16-bit → /16384) */
    float gx = (float)ax / 16384.0f;
    float gy = (float)ay / 16384.0f;
    float gz = (float)az / 16384.0f;

    /* tilt = angle between gravity vector and Z axis */
    float g_mag = sqrtf(gx*gx + gy*gy + gz*gz);
    if (g_mag < 0.01f) return 90.0f;

    /* cos(θ) = |gz| / |g| (assuming device is mostly vertical) */
    float cos_tilt = fabsf(gz) / g_mag;
    if (cos_tilt > 1.0f) cos_tilt = 1.0f;
    tilt_deg = acosf(cos_tilt) * 180.0f / 3.14159265f;
    return tilt_deg;
}

float imu_get_roll_deg(void)
{
    int16_t ax = (int16_t)((imu_read_reg(ICM42688_REG_ACCEL_DATA_X1) << 8) |
                            imu_read_reg(ICM42688_REG_ACCEL_DATA_X0));
    int16_t ay = (int16_t)((imu_read_reg(0x21) << 8) | imu_read_reg(0x20));
    float gx = (float)ax / 16384.0f;
    float gy = (float)ay / 16384.0f;
    return atan2f(gy, gx) * 180.0f / 3.14159265f;
}

bool imu_is_level(void)
{
    return tilt_deg < 2.0f;
}