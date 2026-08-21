/*
 * Flux Ring — data_logger.h
 * W25Q16 SPI flash data logger for magnetic field samples.
 */

#ifndef DATA_LOGGER_H_
#define DATA_LOGGER_H_

#include "field_engine.h"
#include "accel_sensor.h"
#include "compass.h"
#include <stdint.h>

/* Log header magic */
#define LOG_MAGIC  0x46504C58  /* "FLUX" */

/* Log format version */
#define LOG_VERSION  0x01

/* Header size (bytes) */
#define LOG_HEADER_SIZE  32

/* Sample size (bytes) */
#define LOG_SAMPLE_SIZE  22

/**
 * Initialize W25Q16 SPI flash and prepare logging.
 * Reads existing log state (resumes or resets).
 */
int data_logger_init(void);

/**
 * Append a field sample to the flash log.
 * Returns 0 on success, negative on error (flash full, etc.)
 */
int data_logger_append(const field_vector_t *field,
                       const accel_data_t *accel,
                       compass_heading_t heading);

/**
 * Read the number of stored samples.
 */
uint32_t data_logger_sample_count(void);

/**
 * Erase the entire log (erases flash sectors).
 */
int data_logger_erase(void);

/**
 * Dump log contents over UART as CSV.
 */
int data_logger_dump_uart(void);

#endif /* DATA_LOGGER_H_ */