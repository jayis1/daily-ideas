/* display.h — SSD1306 OLED display driver for Taste Bead
 *
 * Simple I2C OLED driver for showing measurement results,
 * library browser, and status messages.
 */

#ifndef TASTE_BEAD_DISPLAY_H
#define TASTE_BEAD_DISPLAY_H

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>

/* Screen dimensions */
#define DISPLAY_WIDTH   128
#define DISPLAY_HEIGHT  64
#define DISPLAY_PAGES   8

/* Initialize OLED display */
esp_err_t display_init(void);

/* Show splash screen */
esp_err_t display_show_splash(const char *title, const char *subtitle);

/* Show a two-line message */
esp_err_t display_show_message(const char *line1, const char *line2);

/* Show classification result with confidence bar */
esp_err_t display_show_result(const char *label, const char *confidence_str,
                                float confidence_pct);

/* Show library browser entry */
esp_err_t display_show_library(int index, int total, const char *label,
                                int measurement_count);

/* Show progress bar (0-100%) */
esp_err_t display_show_progress(const char *label, int percent);

/* Show monitor view (live measurement + result) */
esp_err_t display_show_monitor(const char *last_label, float last_conf,
                                 int sweep_count);

/* Clear display */
esp_err_t display_clear(void);

/* Power off display */
esp_err_t display_off(void);

#endif /* TASTE_BEAD_DISPLAY_H */