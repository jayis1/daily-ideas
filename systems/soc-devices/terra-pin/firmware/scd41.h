/**
 * terra_pin/scd41.h — Sensirion SCD41 NDIR CO2 sensor driver (I2C via TCA9548A mux)
 */

#ifndef SCD41_H
#define SCD41_H

#include "main.h"
#include "driver/i2c.h"

/* SCD41 I2C commands (16-bit, big-endian) */
#define SCD41_CMD_START_PERIODIC      0x21B1
#define SCD41_CMD_READ_MEASUREMENT    0xEC05
#define SCD41_CMD_STOP_PERIODIC       0x3F86
#define SCD41_CMD_REINIT              0x3646
#define SCD41_CMD_PERFORM_FRC         0x362F
#define SCD41_CMD_GET_SERIAL          0x3682
#define SCD41_CMD_SET_AMB_PRESSURE    0xE000
#define SCD41_CMD_PERSIST_SETTINGS    0x3615
#define SCD41_CMD_GET_AMB_PRESSURE    0xE000

#define SCD41_MEASURE_DELAY_MS  20   /* read measurement delay */

/* I2C port — ESP32-S3 default I2C */
#define SCD41_I2C_PORT   I2C_NUM_0
#define SCD41_I2C_FREQ   100000     /* SCD41 max 100 kHz */

#endif /* SCD41_H */