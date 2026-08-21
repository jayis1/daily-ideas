/*
 * Tremor Tile — ADXL355 Ultra-Low-Noise Accelerometer Driver
 * sensor_acq.c — SPI driver, FIFO read, sample buffering
 *
 * ADXL355: 3-axis, ±2g/±4g/±8g, 7µg/√Hz noise, 400Hz ODR
 * Interface: SPI @ 4MHz
 */

#include "sensor_acq.h"
#include "config.h"
#include "hardware/spi.h"
#include "hardware/gpio.h"
#include "pico/stdlib.h"
#include <string.h>

// ADXL355 Register Map
#define ADXL355_DEVID_AD        0x00  // Analog Devices ID (0xAD)
#define ADXL355_DEVID_MST       0x01  // MEMS ID (0x1D)
#define ADXL355_PARTID          0x02  // Part ID (0xED)
#define ADXL355_REVId          0x03  // Revision ID
#define ADXL355_STATUS          0x04  // Status register
#define ADXL355_FIFO_ENTRIES    0x05  // FIFO entries (2 bytes)
#define ADXL355_TEMP2           0x06  // Temperature MSB
#define ADXL355_TEMP1           0x07  // Temperature LSB
#define ADXL355_XDATA3          0x08  // X-axis data [23:16]
#define ADXL355_XDATA2          0x09  // X-axis data [15:8]
#define ADXL355_XDATA1          0x0A  // X-axis data [7:0]
#define ADXL355_YDATA3          0x0B  // Y-axis data
#define ADXL355_YDATA2          0x0C
#define ADXL355_YDATA1          0x0D
#define ADXL355_ZDATA3          0x0E  // Z-axis data
#define ADXL355_ZDATA2          0x0F
#define ADXL355_ZDATA1          0x10
#define ADXL355_FIFO_DATA       0x11  // FIFO data
#define ADXL355_OFFSET_X_H      0x1E  // X offset
#define ADXL355_OFFSET_X_L      0x1F
#define ADXL355_OFFSET_Y_H      0x20  // Y offset
#define ADXL355_OFFSET_Y_L      0x21
#define ADXL355_OFFSET_Z_H      0x22  // Z offset
#define ADXL355_OFFSET_Z_L      0x23
#define ADXL355_ACT_EN           0x24  // Activity enable
#define ADXL355_ACT_THRESH_H    0x25  // Activity threshold
#define ADXL355_ACT_THRESH_L    0x26
#define ADXL355_ACT_COUNT        0x27  // Activity count
#define ADXL355_FILTER           0x28  // Filter settings (ODR + HPF)
#define ADXL355_FIFO_SAMPLES     0x29  // FIFO samples (2 bytes)
#define ADXL355_INT_MAP          0x2A  // Interrupt mapping
#define ADXL355_SYNC             0x2B  // Sync
#define ADXL355_RANGE            0x2C  // Range setting
#define ADXL355_POWER_CTL        0x2D  // Power control (standby/measurement)
#define ADXL355_SELF_TEST         0x2E  // Self test
#define ADXL355_RESET             0x2F  // Reset (write 0x52)

// Status bits
#define STATUS_DATA_RDY      (1 << 0)
#define STATUS_FIFO_RDY      (1 << 1)
#define STATUS_FIFO_OVR      (1 << 2)
#define STATUS_FIFO_FULL     (1 << 3)

// RANGE register values
#define RANGE_2G              0x01  // ±2g
#define RANGE_4G              0x02  // ±4g
#define RANGE_8G              0x03  // ±8g

// POWER_CTL bits
#define POWERCTL_STANDBY     (0 << 0)
#define POWERCTL_MEASUREMENT (1 << 0)
#define POWERCTL_TEMP_OFF    (1 << 2)

// FILTER register: ODR[3:0] + HPF[6:4]
// ODR = 400Hz (0x0C), HPF = no filter (0x00)
#define FILTER_ODR_400HZ     0x04  // ODR bits for 400Hz
#define FILTER_ODR_200HZ     0x05  // 200Hz
#define FILTER_ODR_100HZ     0x06  // 100Hz
#define FILTER_HPF_OFF        0x00  // No high-pass filter
#define FILTER_HPF_0_25HZ    0x10  // HPF at 0.25× ODR

// SPI read: first byte bit7=1 for read, bit6=0 for single byte
// SPI write: first byte bit7=0, bit6=0 for single byte
#define SPI_READ_BIT          0x01
#define SPI_WRITE_BIT         0x00
#define SPI_ADDR(addr)        ((addr << 1) | SPI_READ_BIT)
#define SPI_ADDR_W(addr)      (addr << 1)

// Scale factors (LSB/g)
#define SCALE_2G              3.9e-6f   // 3.9 µg/LSB at ±2g = 256000 LSB/g
#define SCALE_4G              7.8e-6f   // 7.8 µg/LSB at ±4g
#define SCALE_8G              15.6e-6f  // 15.6 µg/LSB at ±8g

static float scale_factor = SCALE_2G;
static uint32_t sample_seq = 0;

// SPI chip select helpers
static inline void adxl355_cs_select(void) {
    gpio_put(SPI0_CS_PIN, 0);
    asm volatile("nop\nnop\nnop\nnop\nnop");  // 5 cycle CS setup
}

static inline void adxl355_cs_deselect(void) {
    asm volatile("nop\nnop\nnop\nnop\nnop");  // 5 cycle CS hold
    gpio_put(SPI0_CS_PIN, 1);
}

// Read single register
static uint8_t adxl355_read_reg(uint8_t addr) {
    uint8_t tx_buf[2] = { SPI_ADDR(addr), 0x00 };
    uint8_t rx_buf[2];
    adxl355_cs_select();
    spi_write_blocking(spi0, tx_buf, 1);
    spi_read_blocking(spi0, 0, rx_buf, 1);
    adxl355_cs_deselect();
    return rx_buf[0];
}

// Write single register
static void adxl355_write_reg(uint8_t addr, uint8_t value) {
    uint8_t tx_buf[2] = { SPI_ADDR_W(addr), value };
    adxl355_cs_select();
    spi_write_blocking(spi0, tx_buf, 2);
    adxl355_cs_deselect();
}

// Read multiple registers
static void adxl355_read_regs(uint8_t addr, uint8_t *buf, uint16_t len) {
    uint8_t tx_byte = SPI_ADDR(addr);
    adxl355_cs_select();
    spi_write_blocking(spi0, &tx_byte, 1);
    spi_read_blocking(spi0, 0, buf, len);
    adxl355_cs_deselect();
}

// Read FIFO data (3 axes × 3 bytes = 9 bytes per sample)
static void adxl355_read_fifo(uint8_t *buf, uint16_t num_samples) {
    adxl355_cs_select();
    uint8_t fifo_cmd = SPI_ADDR(ADXL355_FIFO_DATA);
    spi_write_blocking(spi0, &fifo_cmd, 1);
    spi_read_blocking(spi0, 0, buf, num_samples * 9);
    adxl355_cs_deselect();
}

// Convert 20-bit signed value from 3 bytes (big-endian, 20-bit left-justified)
static inline int32_t adxl355_convert_20bit(uint8_t msb, uint8_t mid, uint8_t lsb) {
    int32_t val = ((int32_t)msb << 24) | ((int32_t)mid << 16) | ((int32_t)lsb << 8);
    val >>= 8;  // Right-justify to get 20-bit signed value
    return val;
}

// Check how many samples are in the FIFO
static uint16_t adxl355_get_fifo_entries(void) {
    uint8_t buf[2];
    adxl355_read_regs(ADXL355_FIFO_ENTRIES, buf, 2);
    return ((uint16_t)buf[0] << 8) | buf[1];
}

void sensor_acq_init(void) {
    // Configure GPIO pins
    gpio_init(SPI0_CS_PIN);
    gpio_set_dir(SPI0_CS_PIN, GPIO_OUT);
    gpio_put(SPI0_CS_PIN, 1);  // CS inactive (high)

    gpio_init(ADXL355_DRDY_PIN);
    gpio_set_dir(ADXL355_DRDY_PIN, GPIO_IN);
    gpio_pull_up(ADXL355_DRDY_PIN);

    gpio_init(ADXL355_INT1_PIN);
    gpio_set_dir(ADXL355_INT1_PIN, GPIO_IN);
    gpio_pull_up(ADXL355_INT1_PIN);

    // Software reset
    adxl355_write_reg(ADXL355_RESET, 0x52);
    sleep_ms(1);  // Wait for reset

    // Verify device ID
    uint8_t devid_ad = adxl355_read_reg(ADXL355_DEVID_AD);
    uint8_t devid_mst = adxl355_read_reg(ADXL355_DEVID_MST);
    uint8_t partid = adxl355_read_reg(ADXL355_PARTID);

    if (devid_ad != 0xAD || devid_mst != 0x1D || partid != 0xED) {
        printf("ADXL355: Device ID mismatch! AD=0x%02X MST=0x%02X PART=0x%02X\n",
               devid_ad, devid_mst, partid);
        // Continue anyway — might be a different rev
    } else {
        printf("ADXL355: Detected (AD=0x%02X, MST=0x%02X, PART=0x%02X)\n",
               devid_ad, devid_mst, partid);
    }

    // Put in standby mode for configuration
    adxl355_write_reg(ADXL355_POWER_CTL, POWERCTL_STANDBY | POWERCTL_TEMP_OFF);

    // Set range: ±2g (high sensitivity for structural vibration)
    // RANGE register: bits [1:0] = range, bit [7:2] = reserved
    switch (ADXL355_RANGE_G) {
        case 2:
            adxl355_write_reg(ADXL355_RANGE, RANGE_2G);
            scale_factor = SCALE_2G;
            break;
        case 4:
            adxl355_write_reg(ADXL355_RANGE, RANGE_4G);
            scale_factor = SCALE_4G;
            break;
        case 8:
            adxl355_write_reg(ADXL355_RANGE, RANGE_8G);
            scale_factor = SCALE_8G;
            break;
        default:
            adxl355_write_reg(ADXL355_RANGE, RANGE_2G);
            scale_factor = SCALE_2G;
            break;
    }

    // Configure filter: ODR = 400Hz, no high-pass filter initially
    uint8_t filter_reg = (FILTER_HPF_OFF << 4) | FILTER_ODR_400HZ;
    adxl355_write_reg(ADXL355_FILTER, filter_reg);

    // Set FIFO watermark to 32 entries (288 bytes)
    // FIFO_SAMPLES register: bits [15:0] = number of samples
    // When FIFO reaches this level, INT1 is asserted
    uint16_t watermark = ADXL355_FIFO_WATERMARK;
    adxl355_write_reg(ADXL355_FIFO_SAMPLES, (watermark >> 8) & 0xFF);  // MSB
    adxl355_write_reg(ADXL355_FIFO_SAMPLES + 1, watermark & 0xFF);      // LSB

    // Map FIFO watermark interrupt to INT1 pin
    adxl355_write_reg(ADXL355_INT_MAP, 0x01);  // FIFO_WATERMARK → INT1

    // Clear FIFO by reading status
    adxl355_read_reg(ADXL355_STATUS);

    // Enable measurement mode
    adxl355_write_reg(ADXL355_POWER_CTL, POWERCTL_MEASUREMENT);

    printf("ADXL355: Configured — %dHz ODR, ±%dg range, FIFO watermark=%d\n",
           ADXL355_ODR, ADXL355_RANGE_G, ADXL355_FIFO_WATERMARK);
}

bool sensor_acq_fifo_ready(void) {
    // Check INT1 pin (FIFO watermark)
    return !gpio_get(ADXL355_INT1_PIN);  // Active low
}

sample_batch_t sensor_acq_read_fifo(void) {
    sample_batch_t batch;
    batch.seq_num = sample_seq++;
    batch.count = 0;

    // Read number of FIFO entries
    uint16_t fifo_entries = adxl355_get_fifo_entries();
    if (fifo_entries == 0) {
        return batch;
    }

    // Limit to our buffer size
    uint16_t to_read = fifo_entries;
    if (to_read > MAX_SAMPLES_PER_BATCH) {
        to_read = MAX_SAMPLES_PER_BATCH;
    }

    // Allocate temporary buffer for raw FIFO data (9 bytes per sample)
    uint8_t raw_data[MAX_SAMPLES_PER_BATCH * 9];

    // Read FIFO
    adxl355_read_fifo(raw_data, to_read);

    // Parse raw data into sample structures
    for (uint16_t i = 0; i < to_read; i++) {
        uint16_t offset = i * 9;

        // X axis: 3 bytes (20-bit signed)
        int32_t x_raw = adxl355_convert_20bit(
            raw_data[offset + 0], raw_data[offset + 1], raw_data[offset + 2]);

        // Y axis: 3 bytes (20-bit signed)
        int32_t y_raw = adxl355_convert_20bit(
            raw_data[offset + 3], raw_data[offset + 4], raw_data[offset + 5]);

        // Z axis: 3 bytes (20-bit signed)
        int32_t z_raw = adxl355_convert_20bit(
            raw_data[offset + 6], raw_data[offset + 7], raw_data[offset + 8]);

        // Convert to g using scale factor
        batch.samples[i].x = (float)x_raw * scale_factor;
        batch.samples[i].y = (float)y_raw * scale_factor;
        batch.samples[i].z = (float)y_raw * scale_factor;

        // Timestamp: microsecond offset from batch start
        // (actual timestamp set by caller using RTC)
        batch.samples[i].timestamp_us = 0;  // Will be filled by caller
    }

    batch.count = to_read;

    // Clear status to allow new FIFO entries
    adxl355_read_reg(ADXL355_STATUS);

    return batch;
}

void sensor_acq_set_odr(uint8_t odr_setting) {
    // Put in standby first (required for register changes)
    adxl355_write_reg(ADXL355_POWER_CTL, POWERCTL_STANDBY | POWERCTL_TEMP_OFF);

    // Update filter register
    uint8_t filter_reg = (FILTER_HPF_OFF << 4) | (odr_setting & 0x0F);
    adxl355_write_reg(ADXL355_FILTER, filter_reg);

    // Return to measurement mode
    adxl355_write_reg(ADXL355_POWER_CTL, POWERCTL_MEASUREMENT);
}

void sensor_acq_set_range(uint8_t range_g) {
    adxl355_write_reg(ADXL355_POWER_CTL, POWERCTL_STANDBY | POWERCTL_TEMP_OFF);

    switch (range_g) {
        case 2:
            adxl355_write_reg(ADXL355_RANGE, RANGE_2G);
            scale_factor = SCALE_2G;
            break;
        case 4:
            adxl355_write_reg(ADXL355_RANGE, RANGE_4G);
            scale_factor = SCALE_4G;
            break;
        case 8:
            adxl355_write_reg(ADXL355_RANGE, RANGE_8G);
            scale_factor = SCALE_8G;
            break;
    }

    adxl355_write_reg(ADXL355_POWER_CTL, POWERCTL_MEASUREMENT);
}