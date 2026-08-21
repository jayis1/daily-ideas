/*
 * ui.c — Button handling and mode state machine
 * Opti Rot — Pocket Digital Polarimeter
 *
 * Debounces three push buttons (MEAS, MODE, CAL) and dispatches
 * mode-specific actions when the MEAS button is pressed.
 */
#include "stm32g4xx_hal.h"
#include <stdio.h>
#include <math.h>
#include "sdkconfig.h"
#include "ui.h"
#include "display.h"
#include "polarimeter.h"
#include "drude.h"
#include "library.h"
#include "ble_bridge.h"
#include "led.h"
#include "temperature.h"

/* Button GPIO pins */
#define BTN_MEAS_PIN   GPIO_PIN_5   /* PB5 */
#define BTN_MODE_PIN   GPIO_PIN_6   /* PB6 */
#define BTN_CAL_PIN    GPIO_PIN_7   /* PB7 */
#define BTN_PORT       GPIOB

static uint32_t last_press_time[3] = {0, 0, 0};
static uint8_t  last_state[3] = {1, 1, 1};  /* buttons active-low */

void ui_init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin  = BTN_MEAS_PIN | BTN_MODE_PIN | BTN_CAL_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(BTN_PORT, &GPIO_InitStruct);
}

uint8_t ui_poll_buttons(void)
{
    uint32_t now = HAL_GetTick();
    uint8_t pins[3] = {
        HAL_GPIO_ReadPin(BTN_PORT, BTN_MEAS_PIN),
        HAL_GPIO_ReadPin(BTN_PORT, BTN_MODE_PIN),
        HAL_GPIO_ReadPin(BTN_PORT, BTN_CAL_PIN)
    };

    for (int i = 0; i < 3; i++) {
        if (pins[i] == 0 && last_state[i] == 1) {
            /* Falling edge — potential press */
            if (now - last_press_time[i] > BUTTON_DEBOUNCE_MS) {
                last_press_time[i] = now;
                last_state[i] = 0;
                return (uint8_t)(i + 1);  /* 1=MEAS, 2=MODE, 3=CAL */
            }
        }
        if (pins[i] == 1 && last_state[i] == 0) {
            last_state[i] = 1;
        }
    }
    return UI_BUTTON_NONE;
}

void ui_execute_mode(uint8_t mode)
{
    switch (mode) {
    case UI_MODE_MEASURE: {
        led_set_color(LED_COLOR_BLUE, 100);
        display_message("Measuring...", NULL);
        polarimeter_set_wavelength(WAVELENGTH_589_NM);
        polarimeter_result_t r = polarimeter_measure();
        if (r.valid) {
            double rotation = polarimeter_compute_rotation(&r);
            /* Try to compute concentration for sucrose as default */
            double conc = polarimeter_compute_concentration(
                rotation, 66.5, PATH_LENGTH_DM, r.temperature_c, -0.01);
            display_measurement(rotation, conc, NULL, 0);
            ble_bridge_send_result(&r, rotation, conc, NULL, 0);
            led_set_color(LED_COLOR_GREEN, 50);
        } else {
            display_message("Signal too low!", "Check tube/LED");
            led_set_color(LED_COLOR_RED, 100);
            HAL_Delay(1500);
            led_set_color(LED_COLOR_OFF, 0);
        }
        break;
    }

    case UI_MODE_IDENTIFY: {
        led_set_color(LED_COLOR_BLUE, 100);
        display_message("3-wavelength scan", "Please wait...");
        polarimeter_result_t results[3];
        double rotations[3];

        polarimeter_measure_multi(results);

        int valid_count = 0;
        for (int i = 0; i < 3; i++) {
            rotations[i] = polarimeter_compute_rotation(&results[i]);
            if (results[i].valid) valid_count++;
        }

        if (valid_count == 3) {
            /* Convert rotations to specific rotations: [α] = α / (l × c)
             * For identification, we normalize by assuming c=1 g/100mL
             * (or use raw rotation as feature). Here we use raw rotation
             * scaled to typical [α] range. */
            drude_result_t drude = drude_fit(rotations,
                (const double[]){WAVELENGTH_405_NM, WAVELENGTH_520_NM, WAVELENGTH_589_NM}, 3);

            /* Predict [α] at 589nm from Drude for matching */
            double alpha_589_pred = (drude.valid) ?
                drude_predict(drude.K, drude.lambda0_nm, 589.0) : rotations[2];

            library_match_t match = library_match(
                alpha_589_pred, rotations[0], rotations[1], &drude);

            if (match.best_index >= 0) {
                const library_entry_t *e = library_get(match.best_index);
                double conc = polarimeter_compute_concentration(
                    rotations[2], e->specific_rotation, PATH_LENGTH_DM,
                    results[2].temperature_c, e->temp_coefficient);
                display_measurement(rotations[2], conc, e->name, match.confidence);
                ble_bridge_send_multi(results, rotations, &drude, &match);
            } else {
                display_message("No match found", NULL);
            }
            led_set_color(LED_COLOR_GREEN, 50);
        } else {
            display_message("Measurement failed", "Check signal");
            led_set_color(LED_COLOR_RED, 100);
        }
        break;
    }

    case UI_MODE_MONITOR: {
        led_set_color(LED_COLOR_CYAN, 50);
        display_message("Monitoring", "MEAS to stop");
        /* Monitor loop runs until MEAS pressed again */
        while (ui_poll_buttons() != UI_BUTTON_MEAS) {
            polarimeter_set_wavelength(WAVELENGTH_589_NM);
            polarimeter_result_t r = polarimeter_measure();
            if (r.valid) {
                double rotation = polarimeter_compute_rotation(&r);
                double conc = polarimeter_compute_concentration(
                    rotation, 66.5, PATH_LENGTH_DM, r.temperature_c, -0.01);
                display_measurement(rotation, conc, NULL, 0);
                ble_bridge_send_result(&r, rotation, conc, NULL, 0);
            }
            HAL_Delay(MONITOR_INTERVAL_MS);
        }
        led_set_color(LED_COLOR_OFF, 0);
        break;
    }

    case UI_MODE_LIBRARY: {
        int total = library_size();
        int idx = 0;
        for (;;) {
            const library_entry_t *e = library_get(idx);
            if (!e) break;
            display_library(idx, total, e->name, e->specific_rotation);
            uint8_t btn = ui_poll_buttons();
            if (btn == UI_BUTTON_MODE) {
                idx = (idx + 1) % total;
            } else if (btn == UI_BUTTON_MEAS || btn == UI_BUTTON_CAL) {
                break;
            }
            HAL_Delay(50);
        }
        break;
    }

    case UI_MODE_CALIBRATE: {
        led_set_color(LED_COLOR_YELLOW, 80);
        display_message("Auto-zeroing...", "Empty tube");
        polarimeter_auto_zero();
        display_message("Zero complete!", NULL);
        HAL_Delay(1000);
        led_set_color(LED_COLOR_GREEN, 50);
        break;
    }

    case UI_MODE_CONFIG: {
        display_message("Config mode", "Use BLE app");
        HAL_Delay(2000);
        break;
    }
    }
}