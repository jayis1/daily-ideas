/*
 * display.h — SH1106 OLED UI
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>
#include "main.h"

void display_init(void);
void display_boot(const char *msg);
void display_idle(float temp_c, float vbat_mv, float laser_mw);
void display_menu(uint8_t item);
void display_measure_live(const phase_block_t *pb, const fft_result_t *fft);
void display_result(const measure_result_t *r);
void display_lissajous(const iq_block_t *iq);
void display_audio(uint8_t on, float gain, float shift);
void display_fault(const char *msg);

#endif /* DISPLAY_H */