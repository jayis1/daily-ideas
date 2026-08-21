/*
 * storage.h — SD card logging for EEM data
 */

#ifndef STORAGE_H
#define STORAGE_H

#include <stdint.h>
#include "eem.h"
#include "library.h"

/**
 * Initialize SD card.
 * @return 0 on success, -1 on error
 */
int storage_init(void);

/**
 * Check if SD card is present and mounted.
 * @return 1 if ready, 0 if not
 */
int storage_ready(void);

/**
 * Log EEM data to SD card as CSV.
 * Creates file: /fluor/EEM_NNNN.csv
 * @param eem     EEM data
 * @param result  Optional classification result (NULL if none)
 * @return 0 on success, -1 on error
 */
int storage_log_eem(const eem_t *eem, const classify_result_t *result);

/**
 * Log EEM data as binary (compact format for later analysis).
 * Creates file: /fluor/EEM_NNNN.bin
 */
int storage_log_eem_binary(const eem_t *eem);

/**
 * Log a text line to the daily log.
 * File: /fluor/LOG_YYYYMMDD.txt
 */
int storage_log_line(const char *line);

/**
 * Get next file sequence number.
 */
int storage_next_seq(void);

/**
 * Get current log file name.
 */
void storage_get_filename(char *buf, int bufsize, int seq, const char *ext);

/**
 * List log files on SD card (for transfer).
 * @param callback  Called for each file name
 */
void storage_list_files(void (*callback)(const char *filename, uint32_t size));

/**
 * Format the log directory.
 */
int storage_format(void);

/**
 * Get free space in KB.
 */
uint32_t storage_free_kb(void);

#endif /* STORAGE_H */