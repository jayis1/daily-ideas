/* display.h — SSD1306 OLED driver: chromatogram plot + peak table
 *
 * I2C 0x3C, 128×64 monochrome. Uses a simple frame buffer in RAM.
 */
#ifndef DISPLAY_H
#define DISPLAY_H

#include "peak.h"
#include "identify.h"

void display_init(void);

/* Show the boot screen with battery voltage. */
void display_boot(float battery_mv);

/* Show the main menu. */
void display_menu(int selected);

/* Show "running" status with live temperature + elapsed time. */
void display_running(float col_temp, float target_temp, float prec_temp,
                     int elapsed_s, int total_s, const char *phase);

/* Plot the live chromatogram (scrolling). */
void display_chromatogram_live(const float *trace, int n, int max_n);

/* Show the final peak table (after run completes). */
void display_peak_table(const identification_t *ids, int n, int scroll);

/* Show a status message. */
void display_status(const char *msg);

#endif /* DISPLAY_H */