/*
 * pyro-balance / Core/Src/safety.c — Triple-redundant safety.
 */
#include "safety.h"
#include "furnace.h"
#include <stdio.h>

static const char* g_alarm = NULL;

void safety_init(void) { g_alarm = NULL; }

bool safety_check(void) {
    /* 1. TLV3201 hardware comparator over-temp */
    if (furnace_overtemp_hw()) { safety_alarm("HW over-temp"); return false; }
    /* 2. thermal fuse blown */
    if (!furnace_fuse_ok()) { safety_alarm("Thermal fuse blown"); return false; }
    /* 3. interlock open (lid) */
    if (HAL_GPIO_ReadPin(INTERLOCK_PORT, INTERLOCK_PIN) == GPIO_PIN_RESET) {
        safety_alarm("Interlock open"); return false;
    }
    /* 4. software limit 620 °C */
    if (furnace_get_temp() > 620.0f) { safety_alarm("SW over-temp 620C"); return false; }
    /* 5. battery low */
    extern pb_status_t g_status;
    if (g_status.battery_v > 0 && g_status.battery_v < 6.4f) { safety_alarm("Low battery"); return false; }
    return true;
}

void safety_alarm(const char* why) {
    g_alarm = why;
    furnace_emergency_cut();
    extern pb_status_t g_status;
    g_status.state = PB_ALARM;
    char msg[64]; snprintf(msg,sizeof(msg),"ALARM: %s",why);
    extern void sd_log_event(const char*);
    sd_log_event(msg);
    extern void esp32_send_log(const char*);
    esp32_send_log(msg);
}

void safety_pet_watchdog(void) {
    extern IWDG_HandleTypeDef hiwdg;
    HAL_IWDG_Refresh(&hiwdg);
}

void safety_interlock_breach(void) { safety_alarm("Interlock breach"); }