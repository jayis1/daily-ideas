/*
 * imu_driver.h — ICM-42688-P 6-axis IMU driver API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef IMU_DRIVER_H
#define IMU_DRIVER_H

#include "esp_err.h"
#include "driver/spi_master.h"

/* ODR (Output Data Rate) selection */
typedef enum {
    IMU_ODR_8HZ    = 3,
    IMU_ODR_32HZ   = 5,
    IMU_ODR_50HZ   = 6,
    IMU_ODR_100HZ  = 7,
    IMU_ODR_200HZ  = 8,
    IMU_ODR_1KHZ   = 11,
} imu_odr_t;

/* Accelerometer full-scale range */
typedef enum {
    IMU_ACCEL_RANGE_2G   = 0,
    IMU_ACCEL_RANGE_4G   = 1,
    IMU_ACCEL_RANGE_8G   = 2,
    IMU_ACCEL_RANGE_16G  = 3,
} imu_accel_range_t;

/* Gyroscope full-scale range */
typedef enum {
    IMU_GYRO_RANGE_250DPS  = 0,
    IMU_GYRO_RANGE_500DPS  = 1,
    IMU_GYRO_RANGE_1000DPS = 2,
    IMU_GYRO_RANGE_2000DPS = 3,
} imu_gyro_range_t;

/* FIFO watermark — number of packets to buffer before interrupt */
#define IMU_FIFO_WATERMARK  16

/* Single IMU sample (6-axis) */
typedef struct {
    float accel_x;        /* m/s² */
    float accel_y;
    float accel_z;
    float gyro_x;         /* rad/s */
    float gyro_y;
    float gyro_z;
    uint32_t timestamp_ms;
} imu_sample_t;

/* IMU configuration struct */
typedef struct {
    imu_odr_t odr;
    imu_accel_range_t accel_range;
    imu_gyro_range_t gyro_range;
} imu_config_t;

/**
 * @brief Initialize ICM-42688-P over SPI.
 *
 * @param host      SPI peripheral to use (e.g., SPI2_HOST)
 * @param odr       Output data rate
 * @param accel_range  Accelerometer full-scale range
 * @param gyro_range   Gyroscope full-scale range
 * @return ESP_OK on success
 */
esp_err_t imu_driver_init(spi_host_device_t host, imu_odr_t odr,
                           imu_accel_range_t accel_range,
                           imu_gyro_range_t gyro_range);

/**
 * @brief Read samples from IMU FIFO.
 *
 * @param samples     Output buffer
 * @param max_samples Maximum number of samples to read
 * @return Number of samples actually read (0 if FIFO empty)
 */
int imu_driver_read_fifo(imu_sample_t *samples, int max_samples);

/**
 * @brief Get current IMU configuration.
 */
const imu_config_t *imu_driver_get_config(void);

#endif /* IMU_DRIVER_H */