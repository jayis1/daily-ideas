/*
 * hall-puck / firmware / Core / Src / main.c
 * Main application — Hall Puck semiconductor characterization
 *
 * State machine, UI, measurement orchestration, ESP32 link.
 *
 * MIT License.
 */
#include "main.h"
#include "stm32g4xx.h"
#include "ads122u04.h"
#include "current_source.h"
#include "vdp_switch.h"
#include "magnet.h"
#include "measurement.h"
#include "oled_display.h"
#include "sd_logger.h"
#include "esp32_link.h"
#include "flash_store.h"
#include "buttons.h"
#include "database.h"
#include <stdio.h>
#include <string.h>

volatile uint32_t sys_tick_ms = 0;

static const char *TAG = "hall-puck";
static meas_mode_t current_mode = MODE_SINGLE;
static int menu_index = 0;

static const char *menu_items[] = {
    "Mode: ",
    "Set Current",
    "Set Thickness",
    "Calibrate B",
    "Info",
    "Reset Config",
    "Exit",
};
#define MENU_COUNT 7

static meas_params_t params;

/* ---- ESP32 command callback ---- */
static void esp_cmd_handler(uint8_t cmd, const uint8_t *payload, int len)
{
    switch (cmd) {
    case ESP_CMD_START:
        params.mode = current_mode;
        params.current_ma = measurement_get_current();
        params.sample_thickness_mm = measurement_get_thickness();
        measurement_start(&params);
        break;
    case ESP_CMD_STOP:
        measurement_cancel();
        break;
    case ESP_CMD_SET_CURRENT:
        if (len >= 4) {
            float ma;
            memcpy(&ma, payload, 4);
            measurement_set_current(ma);
        }
        break;
    case ESP_CMD_SET_THICK:
        if (len >= 4) {
            float mm;
            memcpy(&mm, payload, 4);
            measurement_set_thickness(mm);
        }
        break;
    case ESP_CMD_SET_MODE:
        if (len >= 1) {
            current_mode = (meas_mode_t)payload[0];
        }
        break;
    case ESP_CMD_CALIBRATE:
        /* Run calibration measurement with known sample */
        break;
    case ESP_CMD_GET_INFO:
        esp32_link_send_info("1.0", magnet_get_calibration(), 0);
        break;
    default:
        break;
    }
}

/* ---- Button handler ---- */
static void handle_buttons(void)
{
    static bool in_menu = false;
    button_event_t ev = buttons_poll();

    if (ev == BTN_NONE) return;

    meas_state_t st = measurement_get_state();

    if (!in_menu) {
        switch (ev) {
        case BTN_MEASURE_PRESS:
            if (st == MEAS_IDLE || st == MEAS_DONE || st == MEAS_ERROR) {
                params.mode = current_mode;
                params.current_ma = measurement_get_current();
                params.sample_thickness_mm = measurement_get_thickness();
                measurement_start(&params);
            }
            break;
        case BTN_MODE_PRESS:
            if (st == MEAS_IDLE || st == MEAS_DONE) {
                current_mode = (meas_mode_t)((current_mode + 1) % MODE_COUNT);
            }
            break;
        case BTN_MENU_PRESS:
            if (st == MEAS_IDLE || st == MEAS_DONE) {
                in_menu = true;
                menu_index = 0;
            }
            break;
        case BTN_MEASURE_LONG:
            if (st != MEAS_IDLE) {
                measurement_cancel();
            }
            break;
        default:
            break;
        }
    } else {
        switch (ev) {
        case BTN_MODE_PRESS:
            menu_index = (menu_index + 1) % MENU_COUNT;
            break;
        case BTN_MEASURE_PRESS:
            switch (menu_index) {
            case 0:
                current_mode = (meas_mode_t)((current_mode + 1) % MODE_COUNT);
                break;
            case 1:
                /* Cycle current: 0.1 → 0.5 → 1 → 5 → 10 mA */
                {
                    float cur = measurement_get_current();
                    if (cur < 0.3f) cur = 0.5f;
                    else if (cur < 0.8f) cur = 1.0f;
                    else if (cur < 3.0f) cur = 5.0f;
                    else if (cur < 8.0f) cur = 10.0f;
                    else cur = 0.1f;
                    measurement_set_current(cur);
                }
                break;
            case 2:
                /* Cycle thickness: 0.1 → 0.5 → 1.0 mm */
                {
                    float th = measurement_get_thickness();
                    if (th < 0.3f) th = 0.5f;
                    else if (th < 0.8f) th = 1.0f;
                    else th = 0.1f;
                    measurement_set_thickness(th);
                }
                break;
            case 3:
                /* Calibrate B-field */
                break;
            case 4:
                /* Info */
                esp32_link_send_info("1.0", magnet_get_calibration(), 0);
                break;
            case 5:
                flash_store_reset();
                break;
            case 6:
                break;
            }
            if (menu_index != 0) in_menu = false;
            break;
        case BTN_MENU_PRESS:
            in_menu = false;
            break;
        default:
            break;
        }

        if (in_menu) {
            oled_show_menu(menu_index, menu_items, MENU_COUNT);
        }
    }
}

/* ---- UI update ---- */
static void update_ui(void)
{
    meas_state_t st = measurement_get_state();

    switch (st) {
    case MEAS_IDLE:
        oled_show_idle(24.3f, &params);
        break;
    case MEAS_DONE:
        oled_show_result(measurement_get_result());
        break;
    default:
        break;
    }
}

/* ---- Main ---- */
int main(void)
{
    /* System init (CMSIS) */
    SystemInit();

    /* SysTick: 1ms */
    SysTick_Config(SystemCoreClock / 1000);

    /* Initialize flash storage */
    flash_store_init();
    const flash_config_t *cfg = flash_store_get();
    measurement_set_current(cfg->measurement_current_ma);
    measurement_set_thickness(cfg->sample_thickness_mm);
    measurement_set_b_calibration(cfg->b_field_calibration);
    current_mode = (meas_mode_t)cfg->last_mode;

    /* Initialize measurement engine */
    measurement_init();

    /* Initialize SPI1 (ADS122U04 + ADG714) */
    /* SPI2 (OLED + SD) */
    ads122u04_init();
    current_source_init();
    vdp_switch_init();
    magnet_init();
    oled_init();
    sd_logger_init();
    buttons_init();
    esp32_link_init();
    esp32_link_set_cmd_callback(esp_cmd_handler);

    /* Set up measurement params defaults */
    params.mode = current_mode;
    params.current_ma = measurement_get_current();
    params.sample_thickness_mm = measurement_get_thickness();
    params.temp_start_c = 25.0f;
    params.temp_end_c = 80.0f;
    params.temp_step_c = 10.0f;

    /* Main loop */
    while (1) {
        measurement_task();
        handle_buttons();
        update_ui();
        esp32_link_poll();
        __WFI();  /* sleep until next interrupt */
    }
}

/* ---- SysTick handler ---- */
void SysTick_Handler(void)
{
    sys_tick_ms++;
}

/* ---- Delay functions ---- */
void delay_ms(uint32_t ms)
{
    uint32_t start = sys_tick_ms;
    while ((sys_tick_ms - start) < ms) {
        __NOP();
    }
}