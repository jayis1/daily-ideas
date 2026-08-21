/*
 * cor-sono / firmware / sd_logger.h
 */
#pragma once
#include "main.h"

void sd_logger_init(void);
void sd_logger_start_recording(void);
void sd_logger_write_block(const int16_t *contact, const int16_t *ambient, int n);
void sd_logger_log_result(int class_id, int confidence, int hr);
void sd_logger_stop_recording(void);