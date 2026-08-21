/*
 * laser.c — laser diode driver + shutter control + safety
 *
 * Drives the 650 nm laser diode via AL8805 constant-current PWM, controls
 * the electromechanical shutter via DRV8833, and enforces laser safety:
 *   - Class 2 software limit (1 mW default)
 *   - Max 5 mW (Class 3R) with menu confirmation
 *   - Shutter closes on: lid open (reed), tilt > 45° (IMU), watchdog, user OFF
 */

#include "laser.h"
#include "stm32g4xx_hal.h"
#include "config.h"
#include "imu.h"
#include <math.h>

extern TIM_HandleTypeDef htim8;

static float s_power_mw = CONFIG_LASER_DEFAULT_MW;
static uint8_t s_enabled = 0;
static uint8_t s_shutter_open = 0;

void laser_init(void)
{
    /* TIM8 PWM for laser diode current */
    HAL_TIM_PWM_Start(&htim8, TIM_CHANNEL_1);
    laser_set_power_mw(CONFIG_LASER_DEFAULT_MW);
}

void laser_set_power_mw(float mw)
{
    if (mw < 0.0f) mw = 0.0f;
    if (mw > CONFIG_LASER_MAX_MW) mw = CONFIG_LASER_MAX_MW;
    s_power_mw = mw;

    /* Convert mW → duty cycle (AL8805 is linear; 100% = max current) */
    float duty = mw / CONFIG_LASER_MAX_MW;
    uint32_t arr = __HAL_TIM_GET_AUTORELOAD(&htim8);
    uint32_t ccr = (uint32_t)(duty * arr);
    __HAL_TIM_SET_COMPARE(&htim8, TIM_CHANNEL_1, ccr);
}

float laser_get_power_mw(void) { return s_power_mw; }

void laser_enable(void)
{
    HAL_GPIO_WritePin(CONFIG_LASER_EN_PORT, CONFIG_LASER_EN_PIN, GPIO_PIN_SET);
    s_enabled = 1;
}

void laser_disable(void)
{
    HAL_GPIO_WritePin(CONFIG_LASER_EN_PORT, CONFIG_LASER_EN_PIN, GPIO_PIN_RESET);
    s_enabled = 0;
}

void shutter_open(void)
{
    /* DRV8833 channel A: forward → solenoid pulls shutter open */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_7, GPIO_PIN_SET);
    HAL_Delay(20);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_6, GPIO_PIN_SET);  /* hold */
    s_shutter_open = 1;
}

void shutter_close(void)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_6, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_7, GPIO_PIN_RESET);
    /* spring-return shutter */
    s_shutter_open = 0;
}

uint8_t laser_safety_check(void)
{
    /* Reed interlock: lid open → shutter closed, laser off */
    if (HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_14) == GPIO_PIN_SET) {
        return 0;
    }

    /* Tilt check via IMU (must be < 45° from vertical) */
    imu_sample_t imu;
    imu_read(&imu);
    float accel_mag = sqrtf(imu.ax * imu.ax + imu.ay * imu.ay + imu.az * imu.az);
    if (accel_mag > 0.1f) {
        /* Angle from vertical = acos(az / |a|) */
        float cos_tilt = imu.az / accel_mag;
        if (cos_tilt < 0.0f) cos_tilt = -cos_tilt;
        float tilt_deg = acosf(cos_tilt) * 180.0f / (float)M_PI;
        if (tilt_deg > CONFIG_SAFETY_TILT_MAX_DEG) {
            return 0;
        }
    }
    return 1;
}