/**
 * display.h — SSD1306 OLED Display Driver for Brew Sense
 * 
 * Renders fermentation data on a 128×32 monochrome OLED display.
 * Shows gravity, temperature, stage, activity, and a mini trend graph.
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>
#include <stdbool.h>
#include "fermentation.h"

/* Display pages/screens */
typedef enum {
    DISPLAY_PAGE_MAIN     = 0,  /* Gravity + Temp + Stage */
    DISPLAY_PAGE_CO2_PH   = 1,  /* CO₂ + pH readings */
    DISPLAY_PAGE_GRAPH    = 2,  /* Gravity trend graph (48h) */
    DISPLAY_PAGE_STATUS   = 3,  /* Battery, Wi-Fi, uptime */
} display_page_t;

/**
 * Initialize SSD1306 OLED display over I²C.
 * @return 0 on success, negative on error
 */
int display_init(void);

/**
 * Render the main fermentation data screen.
 * Shows: SG (large), temperature, stage icon, activity bar.
 * @param gravity Current specific gravity
 * @param temperature Current temperature in °C
 * @param stage Current fermentation stage
 * @param activity Activity index (0-100)
 */
void display_render_main(float gravity, float temperature,
                          ferment_stage_t stage, float activity);

/**
 * Render CO₂ and pH screen.
 * @param co2_ppm CO₂ reading
 * @param ph pH reading
 */
void display_render_co2_ph(uint16_t co2_ppm, float ph);

/**
 * Render gravity trend graph.
 * Shows last 48 hours of gravity readings as a line graph.
 * @param gravity_history Array of gravity values (up to 48)
 * @param count Number of valid entries
 * @param current_sg Current gravity for marker
 */
void display_render_graph(const float *gravity_history, 
                           uint16_t count, float current_sg);

/**
 * Render status screen.
 * @param battery_pct Battery percentage
 * @param wifi_rssi Wi-Fi RSSI (0 if not connected)
 * @param uptime_hours Hours since boot
 */
void display_render_status(uint8_t battery_pct, int8_t wifi_rssi,
                            uint32_t uptime_hours);

/**
 * Turn off the display to save power.
 */
void display_off(void);

/**
 * Turn on the display.
 */
void display_on(void);

/**
 * Check if display is currently on.
 */
bool display_is_on(void);

/**
 * Set display contrast (0-255).
 * Lower values save power.
 */
void display_set_contrast(uint8_t contrast);

/**
 * Cycle to the next display page.
 */
void display_next_page(void);

/**
 * Get current display page.
 */
display_page_t display_get_page(void);

#endif /* DISPLAY_H */