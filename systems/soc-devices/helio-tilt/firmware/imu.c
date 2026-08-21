/*
 * imu.c — LSM6DSO IMU + MMC5603NJ magnetometer fusion
 *
 * I2C1 (PA11/PA12, 400 kHz): LSM6DSO accelerometer + gyroscope.
 *   - Accelerometer: ±2g, 104 Hz → roll/pitch from gravity vector.
 *   - Gyroscope: ±250 dps, 104 Hz → rate of change for tracking.
 * I2C2 (PC0/PC1, 400 kHz): MMC5603NJ 3-axis magnetometer.
 *   - ±30 G, 100 Hz → absolute heading (compass).
 *
 * Tilt compensation: heading = atan2(Mag_Y × cos(roll) + Mag_Z × sin(roll),
 *                                     Mag_X × cos(pitch) +
 *                                     Mag_Y × sin(pitch) × sin(roll) -
 *                                     Mag_Z × sin(pitch) × cos(roll))
 */

#include "imu.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define DEG2RAD(x)  ((x) * M_PI / 180.0f)
#define RAD2DEG(x)  ((x) * 180.0f / M_PI)

/* ---- I2C helpers (simplified register-level) ---- */
static void i2c1_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    RCC->APB1ENR1 |= RCC_APB1ENR1_I2C1EN;
    /* PA11=SDA, PA12=SCL: AF4 */
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (11u * 2u))) | (2u << (11u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (12u * 2u))) | (2u << (12u * 2u));
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << 12)) | (4u << 12);
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << 16)) | (4u << 16);
    I2C1->TIMINGR = 0x10909CEC;  /* 400 kHz @ 170 MHz */
    I2C1->CR1 = I2C_CR1_PE;
}

static void i2c2_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOCEN;
    RCC->APB1ENR1 |= RCC_APB1ENR1_I2C2EN;
    /* PC0=SDA, PC1=SCL: AF4 */
    GPIOC->MODER = (GPIOC->MODER & ~(3u << (0u * 2u))) | (2u << (0u * 2u));
    GPIOC->MODER = (GPIOC->MODER & ~(3u << (1u * 2u))) | (2u << (1u * 2u));
    GPIOC->AFR[0] = (GPIOC->AFR[0] & ~(0xFu << 0))  | (4u << 0);
    GPIOC->AFR[0] = (GPIOC->AFR[0] & ~(0xFu << 4))  | (4u << 4);
    I2C2->TIMINGR = 0x10909CEC;
    I2C2->CR1 = I2C_CR1_PE;
}

static void i2c_write(uint8_t port, uint8_t addr, uint8_t reg, uint8_t val)
{
    /* Simplified: write reg + val to I2C device */
    volatile uint32_t *cr2 = (port == 1) ? &I2C1->CR2 : &I2C2->CR2;
    volatile uint32_t *txdr = (port == 1) ? &I2C1->TXDR : &I2C2->TXDR;
    volatile uint32_t *isr = (port == 1) ? &I2C1->ISR : &I2C2->ISR;

    *cr2 = ((uint32_t)addr << 1) | (2u << I2C_CR2_NBYTES_Pos) | I2C_CR2_START;
    while (!(*isr & I2C_ISR_TXIS)) ;
    *txdr = reg;
    while (!(*isr & I2C_ISR_TXIS)) ;
    *txdr = val;
    while (!(*isr & I2C_ISR_TC)) ;
    *cr2 = I2C_CR2_STOP;
}

static void i2c_read(uint8_t port, uint8_t addr, uint8_t reg,
                      uint8_t *buf, uint8_t len)
{
    volatile uint32_t *cr2 = (port == 1) ? &I2C1->CR2 : &I2C2->CR2;
    volatile uint32_t *txdr = (port == 1) ? &I2C1->TXDR : &I2C2->TXDR;
    volatile uint32_t *rxdr = (port == 1) ? &I2C1->RXDR : &I2C2->RXDR;
    volatile uint32_t *isr = (port == 1) ? &I2C1->ISR : &I2C2->ISR;

    /* Write register address */
    *cr2 = ((uint32_t)addr << 1) | (1u << I2C_CR2_NBYTES_Pos) | I2C_CR2_START;
    while (!(*isr & I2C_ISR_TXIS)) ;
    *txdr = reg;
    while (!(*isr & I2C_ISR_TC)) ;

    /* Repeated start, read */
    *cr2 = ((uint32_t)addr << 1) | I2C_CR2_RD_WRN
         | ((uint32_t)len << I2C_CR2_NBYTES_Pos) | I2C_CR2_START;
    for (uint8_t i = 0; i < len; i++) {
        while (!(*isr & I2C_ISR_RXNE)) ;
        buf[i] = (uint8_t)*rxdr;
    }
    while (!(*isr & I2C_ISR_TC)) ;
    *cr2 = I2C_CR2_STOP;
}

/* ---- LSM6DSO registers ---- */
#define LSM6DSO_WHO_AM_I    0x0F
#define LSM6DSO_CTRL1_XL    0x10
#define LSM6DSO_CTRL2_G     0x11
#define LSM6DSO_OUTX_L_A    0x28
#define LSM6DSO_OUTX_L_G    0x22

/* ---- MMC5603NJ registers ---- */
#define MMC5603_WHO_AM_I    0x39
#define MMC5603_CTRL0       0x04
#define MMC5603_CTRL1       0x05
#define MMC5603_CTRL2       0x06
#define MMC5603_XOUT_L      0x00

/* ---- Magnetometer calibration offsets ---- */
static float mag_offset[3] = {0, 0, 0};
static float mag_scale[3]  = {1.0f, 1.0f, 1.0f};

/* ---- Raw data ---- */
static float accel[3] = {0, 0, 0};   /* g */
static float gyro[3]  = {0, 0, 0};   /* dps */
static float mag[3]   = {0, 0, 0};   /* Gauss */

void imu_init(void)
{
    i2c1_init();
    i2c2_init();

    /* LSM6DSO: accel ±2g @ 104 Hz, gyro ±250 dps @ 104 Hz */
    i2c_write(1, IMU_I2C_ADDR, LSM6DSO_CTRL1_XL, 0x20);  /* ±2g, 104 Hz */
    i2c_write(1, IMU_I2C_ADDR, LSM6DSO_CTRL2_G,  0x20);  /* ±250 dps, 104 Hz */

    /* MMC5603NJ: continuous mode @ 100 Hz */
    i2c_write(2, MAG_I2C_ADDR, MMC5603_CTRL1, 0x00);
    i2c_write(2, MAG_I2C_ADDR, MMC5603_CTRL2, 0x01);
}

static void read_accel(void)
{
    uint8_t buf[6];
    i2c_read(1, IMU_I2C_ADDR, LSM6DSO_OUTX_L_A, buf, 6);
    int16_t x = (int16_t)((buf[1] << 8) | buf[0]);
    int16_t y = (int16_t)((buf[3] << 8) | buf[2]);
    int16_t z = (int16_t)((buf[5] << 8) | buf[4]);
    /* ±2g → 0.061 mg/LSB */
    accel[0] = x * 0.000061f;
    accel[1] = y * 0.000061f;
    accel[2] = z * 0.000061f;
}

static void read_gyro(void)
{
    uint8_t buf[6];
    i2c_read(1, IMU_I2C_ADDR, LSM6DSO_OUTX_L_G, buf, 6);
    int16_t x = (int16_t)((buf[1] << 8) | buf[0]);
    int16_t y = (int16_t)((buf[3] << 8) | buf[2]);
    int16_t z = (int16_t)((buf[5] << 8) | buf[4]);
    /* ±250 dps → 8.75 mdps/LSB */
    gyro[0] = x * 0.00875f;
    gyro[1] = y * 0.00875f;
    gyro[2] = z * 0.00875f;
}

static void read_mag(void)
{
    uint8_t buf[9];
    i2c_read(2, MAG_I2C_ADDR, MMC5603_XOUT_L, buf, 9);
    /* MMC5603NJ: 20-bit unsigned, 2^20 = 1048576, ±30 G range
     * Center = 2^19 = 524288; sensitivity = 60G / 2^20 = 0.0000572 G/LSB
     */
    for (int i = 0; i < 3; i++) {
        int32_t raw = ((int32_t)buf[i*3] << 12)
                    | ((int32_t)buf[i*3+1] << 4)
                    | ((int32_t)buf[i*3+2] >> 4);
        mag[i] = ((float)raw - 524288.0f) * 0.0000572f;
        mag[i] = (mag[i] - mag_offset[i]) * mag_scale[i];
    }
}

void imu_read_tilt(imu_tilt_t *tilt)
{
    read_accel();
    /* Roll (phi) = atan2(ay, az), Pitch (theta) = atan2(-ax, sqrt(ay²+az²)) */
    float phi   = atan2f(accel[1], accel[2]);
    float theta = atan2f(-accel[0],
                         sqrtf(accel[1] * accel[1] + accel[2] * accel[2]));
    tilt->roll  = RAD2DEG(phi);
    tilt->pitch = RAD2DEG(theta);
    tilt->tilt_mag = sqrtf(tilt->roll * tilt->roll
                          + tilt->pitch * tilt->pitch);
    tilt->valid = true;
}

void imu_read_heading(float *heading_deg)
{
    imu_tilt_t tilt;
    imu_read_tilt(&tilt);
    read_mag();

    /* Tilt-compensated heading (arctan of Y/X after tilt correction) */
    float cr = cosf(DEG2RAD(tilt.roll));
    float sr = sinf(DEG2RAD(tilt.roll));
    float cp = cosf(DEG2RAD(tilt.pitch));
    float sp = sinf(DEG2RAD(tilt.pitch));

    /* Compensate magnetometer for tilt */
    float mxh = mag[0] * cp + mag[2] * sp;
    float myh = mag[0] * sr * sp + mag[1] * cr - mag[2] * sr * cp;
    float heading = atan2f(-myh, mxh);
    heading = RAD2DEG(heading);
    if (heading < 0) heading += 360.0f;
    *heading_deg = heading;
}

void imu_read_fusion(imu_tilt_t *tilt)
{
    imu_read_tilt(tilt);
    imu_read_heading(&tilt->heading);
}

void imu_calibrate_mag(void)
{
    /* Simple hard-iron offset calibration.
     * Rotate device 360° in horizontal plane; record min/max per axis.
     */
    float mn[3] = {1e9, 1e9, 1e9};
    float mx[3] = {-1e9, -1e9, -1e9};
    /* Sample for ~30 seconds at 10 Hz = 300 samples */
    for (int i = 0; i < 300; i++) {
        read_mag();
        for (int j = 0; j < 3; j++) {
            if (mag[j] < mn[j]) mn[j] = mag[j];
            if (mag[j] > mx[j]) mx[j] = mag[j];
        }
        /* delay_ms(100); — would use SysTick */
    }
    for (int j = 0; j < 3; j++) {
        mag_offset[j] = (mx[j] + mn[j]) / 2.0f;
        float range = (mx[j] - mn[j]) / 2.0f;
        if (range > 0.001f)
            mag_scale[j] = 1.0f / range;
    }
}