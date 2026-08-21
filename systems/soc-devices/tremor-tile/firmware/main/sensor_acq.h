/*
 * Tremor Tile — Sensor Acquisition Header
 * sensor_acq.h — Data structures and function prototypes
 */

#ifndef TREMOR_TILE_SENSOR_ACQ_H
#define TREMOR_TILE_SENSOR_ACQ_H

#include <stdint.h>
#include <stdbool.h>

// Maximum samples per batch (limited by ADXL355 FIFO depth)
#define MAX_SAMPLES_PER_BATCH    64

// Single vibration sample (3-axis, in g units)
typedef struct {
    float x;               // X-axis acceleration (g)
    float y;               // Y-axis acceleration (g)
    float z;               // Z-axis acceleration (g)
    uint32_t timestamp_us;  // Microsecond timestamp
} vibration_sample_t;

// Batch of samples read from FIFO
typedef struct {
    vibration_sample_t samples[MAX_SAMPLES_PER_BATCH];
    uint16_t count;        // Number of valid samples in this batch
    uint32_t seq_num;      // Sequence number (monotonically increasing)
    int64_t timestamp;     // Unix timestamp from RTC
} sample_batch_t;

// Initialize ADXL355 and configure for vibration acquisition
void sensor_acq_init(void);

// Check if FIFO has enough data (watermark reached)
bool sensor_acq_fifo_ready(void);

// Read all available samples from FIFO
sample_batch_t sensor_acq_read_fifo(void);

// Change output data rate dynamically
// ODR values: 0=4000Hz, 1=2000Hz, 2=1000Hz, 3=500Hz, 4=400Hz,
//             5=200Hz, 6=100Hz, 7=50Hz, 8=25Hz, 9=12.5Hz, 10=6.25Hz
void sensor_acq_set_odr(uint8_t odr_setting);

// Change measurement range
// Range values: 2, 4, or 8 (g)
void sensor_acq_set_range(uint8_t range_g);

#endif // TREMOR_TILE_SENSOR_ACQ_H