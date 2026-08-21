/*
 * pyro-balance / Core/Src/purge.c — N2 purge pump + valve + flow.
 */
#include "purge.h"
#include "bme280.h"
extern I2C_HandleTypeDef hi2c1;
#define SFM_ADDR (0x40 << 1)

void purge_init(void) {
    HAL_GPIO_WritePin(N2_VALVE_PORT, N2_VALVE_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(PUMP_PWM_PORT, PUMP_PWM_PIN, GPIO_PIN_RESET);
}
void purge_set_n2(bool on) {
    HAL_GPIO_WritePin(N2_VALVE_PORT, N2_VALVE_PIN, on ? GPIO_PIN_SET : GPIO_PIN_RESET);
}
void purge_pump_on(bool on) {
    HAL_GPIO_WritePin(PUMP_PWM_PORT, PUMP_PWM_PIN, on ? GPIO_PIN_SET : GPIO_PIN_RESET);
}
void purge_set_flow_ml_per_min(float ml_min) {
    /* scale to PWM duty on PA6 (TIM3 CH1) */
    extern TIM_HandleTypeDef htim3;
    uint16_t duty = (uint16_t)(ml_min / 200.0f * 1000.0f);
    if (duty > 1000) duty = 1000;
    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, duty);
}
float purge_read_flow(void) {
    /* SFM3300 I²C read flow */
    uint8_t cmd = 0x10;
    HAL_I2C_Master_Transmit(&hi2c1, SFM_ADDR, &cmd, 1, 50);
    uint8_t b[2];
    HAL_I2C_Master_Receive(&hi2c1, SFM_ADDR, b, 2, 50);
    int16_t raw = (b[0]<<8)|b[1];
    return raw / 2.0f; /* L/h → scale as needed */
}