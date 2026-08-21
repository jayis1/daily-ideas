/*
 * pyro-balance / Core/Src/furnace.c
 * Nichrome furnace PID temperature control + ramp generator.
 * PID tick @ 10 Hz. HRTIM PWM drive on PA5 (simulated via TIM here).
 */
#include "furnace.h"
#include "ads122u04.h"
#include "safety.h"
#include "flash_store.h"

static float g_Kp = 6.0f, g_Ki = 0.15f, g_Kd = 1.2f;
static float g_integral = 0.0f, g_last_err = 0.0f;
static uint16_t g_final = 600, g_rate_x10 = 100, g_hold_min = 5;
static float g_ramp_start_c = 25.0f, g_cur_target = 25.0f;
static uint32_t g_ramp_start_ms = 0;
static bool g_running = false;

void furnace_init(void) {
    g_running = false;
    g_integral = 0.0f; g_last_err = 0.0f;
    /* PWM setup on PA5 via TIM2 CH1 20 kHz (simplified) */
    /* HRTIM in production; here TIM2 placeholder */
}

void furnace_start(uint16_t final_temp_c, uint16_t rate_c_per_min_x10, uint16_t hold_min) {
    g_final = final_temp_c;
    g_rate_x10 = rate_c_per_min_x10;
    g_hold_min = hold_min;
    g_ramp_start_c = furnace_get_temp();
    g_cur_target = g_ramp_start_c;
    g_ramp_start_ms = HAL_GetTick();
    g_integral = 0.0f; g_last_err = 0.0f;
    g_running = true;
    HAL_GPIO_WritePin(HEATER_EN_PORT, HEATER_EN_PIN, GPIO_PIN_SET);
}

void furnace_stop(void) {
    g_running = false;
    g_cur_target = 25.0f;
    furnace_set_duty(0);
    HAL_GPIO_WritePin(HEATER_EN_PORT, HEATER_EN_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(FAN_PORT, FAN_PIN, GPIO_PIN_SET);
}

float furnace_get_temp(void) { return ads_read_temp_c(); }
float furnace_get_target(void) { return g_cur_target; }

void furnace_pid_tick(void) {
    if (!g_running) return;

    /* ramp target */
    float rate = g_rate_x10 / 10.0f;          /* °C/min */
    float dmin = (HAL_GetTick() - g_ramp_start_ms) / 60000.0f;
    g_cur_target = g_ramp_start_c + rate * dmin;
    if (g_cur_target > g_final) g_cur_target = g_final;

    float T = furnace_get_temp();
    float err = g_cur_target - T;

    /* anti-windup clamp */
    g_integral += g_Ki * err * 0.1f;
    if (g_integral > 100.0f) g_integral = 100.0f;
    if (g_integral < 0.0f)   g_integral = 0.0f;

    float der = (err - g_last_err) / 0.1f;
    g_last_err = err;

    float out = g_Kp * err + g_integral + g_Kd * der;   /* 0..1000 */
    if (out < 0)    out = 0;
    if (out > 1000) out = 1000;
    furnace_set_duty((uint16_t)out);
}

void furnace_cooling_tick(void) {
    if (furnace_get_temp() < 60.0f) {
        HAL_GPIO_WritePin(FAN_PORT, FAN_PIN, GPIO_PIN_RESET);
    }
}

bool furnace_is_stable(float tol_c) {
    static float last = -1.0f;
    float t = furnace_get_temp();
    bool ok = (last >= 0) && (fabsf(t - last) < tol_c);
    last = t;
    return ok;
}

void furnace_set_duty(uint16_t pct_x10) {
    /* In production: write to HRTIM CMP. Here: software PWM on PA5 via TIM2. */
    extern TIM_HandleTypeDef htim3;
    if (pct_x10 > 1000) pct_x10 = 1000;
    /* TIM2 CH1 placeholder — assume ARR=1000 */
    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, pct_x10);
}

/* Safety */
bool furnace_overtemp_hw(void) {
    return HAL_GPIO_ReadPin(OVERTEMP_PORT, OVERTEMP_PIN) == GPIO_PIN_RESET; /* active low from TLV3201 */
}
bool furnace_fuse_ok(void) {
    return HAL_GPIO_ReadPin(FUSE_SENSE_PORT, FUSE_SENSE_PIN) == GPIO_PIN_SET;
}
void furnace_emergency_cut(void) {
    g_running = false;
    furnace_set_duty(0);
    HAL_GPIO_WritePin(HEATER_EN_PORT, HEATER_EN_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(FAN_PORT, FAN_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(BUZZER_PORT, BUZZER_PIN, GPIO_PIN_SET);
}