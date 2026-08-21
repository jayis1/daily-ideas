/*
 * display.h — SSD1306 OLED UI driver (128x64, I2C)
 *
 * Five display modes:
 *  0: Parameter table (fₛ, R₁, C₁, L₁, C₀, Q, ESR)
 *  1: Admittance circle (G-B plot)
 *  2: Temperature turnover curve (Δf/f₀ vs T)
 *  3: Allan deviation (σ_y vs τ log-log)
 *  4: Classification result
 */

#ifndef QUARTZ_TUNER_DISPLAY_H
#define QUARTZ_TUNER_DISPLAY_H

#include "types.h"

int display_init(void);
void display_update(const crystal_t *crystal, display_mode_t mode);
void display_show_message(const char *msg);
void display_show_state(device_state_t state);

#endif /* QUARTZ_TUNER_DISPLAY_H */