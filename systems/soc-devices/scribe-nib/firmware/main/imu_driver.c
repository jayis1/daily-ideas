/*
 * imu_driver.c — ICM-42688-P 6-axis IMU driver for Scribe Nib
 * SPI interface, 200Hz ODR, FIFO watermark mode
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "imu_driver.h"
#include <string.h>
#include "esp_log.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

static const char *TAG = "imu_driver";

/* ICM-42688-P register map */
#define REG_DEVICE_CONFIG      0x01
#define REG_DRIVE_CONFIG       0x02
#define REG_INT_CONFIG         0x03
#define REG_FIFO_CONFIG        0x05
#define REG_TEMP_DATA         0x09
#define REG_ACCEL_DATA_X1     0x0B
#define REG_GYRO_DATA_X1     0x11
#define REG_SIGNAL_PATH_RESET 0x4B
#define REG_INTF_CONFIG_A     0x4C
#define REG_INTF_CONFIG_B     0x4D
#define REG_DEVICE_ID         0x75
#define REG_FIFO_COUNTH       0x7D
#define REG_FIFO_COUNTL       0x7E
#define REG_FIFO_DATA         0x7F
#define REG_BANK_SEL          0x76

/* Bank 0 registers */
#define REG0_ACCEL_CONFIG0     0x03
#define REG0_GYRO_CONFIG0     0x04
#define REG0_ACCEL_CONFIG1    0x05
#define REG0_GYRO_CONFIG1    0x06
#define REG0_ACCEL_AFE       0x07
#define REG0_GYRO_AFE        0x08
#define REG0_FIFO_CONFIG0    0x09
#define REG0_FIFO_CONFIG1    0x0A
#define REG0_FIFO_CONFIG2    0x0B
#define REG0_FIFO_CONFIG3    0x0C
#define REG0_INT_CONFIG0     0x0D
#define REG0_INT_SOURCE0     0x0F
#define REG0_INT_SOURCE3     0x12
#define REG0_INT_SOURCE4     0x13

/* Device ID for ICM-42688-P */
#define ICM42688_DEVICE_ID    0x47

/* FIFO packet size: 2 bytes header + 6 accel + 6 gyro = 14 bytes */
#define FIFO_PACKET_SIZE      14

static spi_device_handle_t spi_dev;
static SemaphoreHandle_t spi_mutex;
static gpio_num_t cs_pin = GPIO_NUM_6;
static imu_config_t current_config;

/* ---- Low-level SPI register access ---- */

static esp_err_t spi_write_reg(uint8_t reg, uint8_t val)
{
    uint8_t tx[2] = { reg, val };
    spi_transaction_t trans = {
        .length = 16,
        .tx_buffer = tx,
        .rx_buffer = NULL,
    };
    return spi_device_polling_transmit(spi_dev, &trans);
}

static esp_err_t spi_read_reg(uint8_t reg, uint8_t *val)
{
    uint8_t tx[2] = { reg | 0x80, 0x00 };
    uint8_t rx[2] = { 0, 0 };
    spi_transaction_t trans = {
        .length = 16,
        .tx_buffer = tx,
        .rx_buffer = rx,
    };
    esp_err_t err = spi_device_polling_transmit(spi_dev, &trans);
    if (err == ESP_OK) {
        *val = rx[1];
    }
    return err;
}

static esp_err_t spi_read_burst(uint8_t start_reg, uint8_t *buf, uint16_t len)
{
    uint8_t cmd = start_reg | 0x80;
    spi_transaction_t trans = {
        .length = 8 + len * 8,
        .tx_buffer = &cmd,
        .rx_buffer = buf,
    };
    /* Need to send cmd byte + read len bytes */
    uint8_t *tx_full = malloc(len + 1);
    uint8_t *rx_full = malloc(len + 1);
    if (!tx_full || !rx_full) {
        free(tx_full);
        free(rx_full);
        return ESP_ERR_NO_MEM;
    }
    tx_full[0] = cmd;
    memset(&tx_full[1], 0xFF, len);

    spi_transaction_t t = {
        .flags = 0,
        .length = (len + 1) * 8,
        .tx_buffer = tx_full,
        .rx_buffer = rx_full,
    };
    esp_err_t err = spi_device_polling_transmit(spi_dev, &t);
    if (err == ESP_OK) {
        memcpy(buf, &rx_full[1], len);
    }
    free(tx_full);
    free(rx_full);
    return err;
}

/* ---- Bank selection ---- */

static esp_err_t select_bank(uint8_t bank)
{
    return spi_write_reg(REG_BANK_SEL, (bank << 4) & 0xF0);
}

/* ---- Public API ---- */

esp_err_t imu_driver_init(spi_host_device_t host, imu_odr_t odr,
                           imu_accel_range_t accel_range,
                           imu_gyro_range_t gyro_range)
{
    spi_device_interface_config_t dev_cfg = {
        .mode = 0,
        .clock_speed_hz = 20 * 1000 * 1000,  /* 20MHz */
        .spics_io_num = cs_pin,
        .queue_size = 7,
        .command_bits = 0,
        .address_bits = 0,
    };
    ESP_ERROR_CHECK(spi_bus_add_device(host, &dev_cfg, &spi_dev));

    spi_mutex = xSemaphoreCreateMutex();

    /* Soft reset */
    spi_write_reg(REG_SIGNAL_PATH_RESET, 0x01);
    vTaskDelay(pdMS_TO_TICKS(10));

    /* Verify device ID */
    uint8_t dev_id = 0;
    spi_read_reg(REG_DEVICE_ID, &dev_id);
    if (dev_id != ICM42688_DEVICE_ID) {
        ESP_LOGE(TAG, "Device ID mismatch: got 0x%02X, expected 0x%02X", dev_id, ICM42688_DEVICE_ID);
        return ESP_ERR_NOT_FOUND;
    }
    ESP_LOGI(TAG, "ICM-42688-P detected (ID=0x%02X)", dev_id);

    /* Configure accelerometer */
    select_bank(0);
    uint8_t accel_cfg0 = (odr << 5) | (accel_range << 1);  /* ODR + range */
    spi_write_reg(REG0_ACCEL_CONFIG0, accel_cfg0);

    /* Configure gyroscope */
    uint8_t gyro_cfg0 = (odr << 5) | (gyro_range << 1);
    spi_write_reg(REG0_GYRO_CONFIG0, gyro_cfg0);

    /* Enable FIFO for accel + gyro in 20-bit mode */
    spi_write_reg(REG0_FIFO_CONFIG0, 0x06);  /* accel+gyro to FIFO */
    spi_write_reg(REG0_FIFO_CONFIG1, 0x00);  /* bypass mode initially */

    /* Set FIFO watermark to 16 packets */
    uint16_t watermark = 16;  /* 16 * 14 = 224 bytes */
    spi_write_reg(REG0_FIFO_CONFIG2, (watermark >> 0) & 0xFF);
    spi_write_reg(REG0_FIFO_CONFIG3, (watermark >> 8) & 0xFF);

    /* Configure INT1 as data-ready / FIFO watermark */
    spi_write_reg(REG0_INT_CONFIG0, 0x00);
    spi_write_reg(REG0_INT_SOURCE0, 0x08);  /* FIFO watermark on INT1 */

    /* Enable FIFO in streaming mode */
    spi_write_reg(REG0_FIFO_CONFIG1, 0x01);  /* Stream mode */

    /* Set ODR and range in config struct */
    current_config.odr = odr;
    current_config.accel_range = accel_range;
    current_config.gyro_range = gyro_range;

    ESP_LOGI(TAG, "IMU configured: ODR=%d, accel_range=%d, gyro_range=%d",
             odr, accel_range, gyro_range);

    return ESP_OK;
}

int imu_driver_read_fifo(imu_sample_t *samples, int max_samples)
{
    if (xSemaphoreTake(spi_mutex, pdMS_TO_TICKS(10)) != pdTRUE) {
        return 0;
    }

    /* Read FIFO count (2 registers) */
    uint8_t fifo_count_h, fifo_count_l;
    select_bank(0);
    spi_read_reg(REG_FIFO_COUNTH, &fifo_count_h);
    spi_read_reg(REG_FIFO_COUNTL, &fifo_count_l);
    uint16_t fifo_count = ((uint16_t)fifo_count_h << 8) | fifo_count_l;

    /* Number of complete packets available */
    int packets = fifo_count / FIFO_PACKET_SIZE;
    if (packets > max_samples) {
        packets = max_samples;
    }

    if (packets == 0) {
        xSemaphoreGive(spi_mutex);
        return 0;
    }

    /* Burst-read FIFO data */
    uint8_t fifo_buf[packets * FIFO_PACKET_SIZE];
    esp_err_t err = spi_read_burst(REG_FIFO_DATA, fifo_buf, packets * FIFO_PACKET_SIZE);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "FIFO burst read failed: 0x%X", err);
        xSemaphoreGive(spi_mutex);
        return 0;
    }

    /* Parse FIFO packets */
    for (int i = 0; i < packets; i++) {
        uint8_t *p = &fifo_buf[i * FIFO_PACKET_SIZE];

        /* Header byte: bits[7:6]=FIFO_PARITY, bits[5:4]=FIFO_H_CTRL,
           bits[3:0]=accel/gyro 20/16 bit flags */
        /* Skip header (2 bytes), parse accel and gyro as 16-bit signed */

        /* Accelerometer: bytes 2-7 (20-bit, we take upper 16) */
        int16_t ax_raw = (int16_t)((p[2] << 8) | p[3]);
        int16_t ay_raw = (int16_t)((p[4] << 8) | p[5]);
        int16_t az_raw = (int16_t)((p[6] << 8) | p[7]);

        /* Gyroscope: bytes 8-13 (20-bit, we take upper 16) */
        int16_t gx_raw = (int16_t)((p[8] << 8) | p[9]);
        int16_t gy_raw = (int16_t)((p[10] << 8) | p[11]);
        int16_t gz_raw = (int16_t)((p[12] << 8) | p[13]);

        /* Convert to physical units */
        float accel_scale = 0.0f;
        switch (current_config.accel_range) {
            case IMU_ACCEL_RANGE_2G:   accel_scale = 2.0f / 32768.0f; break;
            case IMU_ACCEL_RANGE_4G:   accel_scale = 4.0f / 32768.0f; break;
            case IMU_ACCEL_RANGE_8G:   accel_scale = 8.0f / 32768.0f; break;
            case IMU_ACCEL_RANGE_16G:  accel_scale = 16.0f / 32768.0f; break;
        }

        float gyro_scale = 0.0f;
        switch (current_config.gyro_range) {
            case IMU_GYRO_RANGE_250DPS:  gyro_scale = 250.0f / 32768.0f; break;
            case IMU_GYRO_RANGE_500DPS:  gyro_scale = 500.0f / 32768.0f; break;
            case IMU_GYRO_RANGE_1000DPS: gyro_scale = 1000.0f / 32768.0f; break;
            case IMU_GYRO_RANGE_2000DPS: gyro_scale = 2000.0f / 32768.0f; break;
        }

        samples[i].accel_x = ax_raw * accel_scale * 9.81f;   /* m/s² */
        samples[i].accel_y = ay_raw * accel_scale * 9.81f;
        samples[i].accel_z = az_raw * accel_scale * 9.81f;
        samples[i].gyro_x  = gx_raw * gyro_scale * (3.14159f / 180.0f);  /* rad/s */
        samples[i].gyro_y  = gy_raw * gyro_scale * (3.14159f / 180.0f);
        samples[i].gyro_z  = gz_raw * gyro_scale * (3.14159f / 180.0f);
        samples[i].timestamp_ms = xTaskGetTickCount() * portTICK_PERIOD_MS;
    }

    xSemaphoreGive(spi_mutex);
    return packets;
}

const imu_config_t *imu_driver_get_config(void)
{
    return &current_config;
}