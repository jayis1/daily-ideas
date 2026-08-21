/**
 * alarm.c — Alarm and Notification Manager Implementation
 * 
 * Manages buzzer patterns and RGB LED alerts for fermentation events.
 */

#include "alarm.h"
#include "stm32l4xx_hal.h"
#include <string.h>
#include <stdio.h>

extern TIM_HandleTypeDef htim15;  /* Buzzer PWM timer */

static alarm_config_t s_config;
static bool s_active = false;
static alarm_pattern_t s_current_pattern = ALARM_PATTERN_NONE;
static uint32_t s_acknowledge_time = 0;
static char s_alarm_description[64] = "No alarm";

/* Acknowledge cooldown: don't re-trigger same alarm for 30 minutes */
#define ACKNOWLEDGE_COOLDOWN_MS (30 * 60 * 1000)

/*----------------------------------------------------------------------------*/

void alarm_init(const alarm_config_t *config) {
    if (config) {
        s_config = *config;
    } else {
        s_config.enable_buzzer = true;
        s_config.enable_led = true;
        s_config.temp_high_threshold = 30.0f;
        s_config.temp_low_threshold = 10.0f;
        s_config.ph_low_threshold = 2.5f;
        s_config.ph_high_threshold = 4.4f;
        s_config.stuck_hours = 48;
        s_config.alarm_on_finished = true;
        s_config.alarm_on_stuck = true;
    }
    
    /* Initialize buzzer GPIO (PB14 = TIM15_CH1) */
    /* Buzzer is driven by PWM at ~2kHz */
    HAL_TIM_PWM_Start(&htim15, TIM_CHANNEL_1);
    __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 0);  /* Off */
    
    /* Initialize RGB LED GPIOs */
    /* PB15 = Red, PC7 = Green, PC8 = Blue (active low) */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_15, GPIO_PIN_SET);  /* Red off */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_7, GPIO_PIN_SET);   /* Green off */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_8, GPIO_PIN_SET);   /* Blue off */
}

/*----------------------------------------------------------------------------*/

void alarm_check(ferment_stage_t stage, float gravity,
                  float temperature, float ph, uint8_t alerts) {
    s_active = false;
    s_current_pattern = ALARM_PATTERN_NONE;
    
    uint32_t now = HAL_GetTick();
    bool in_cooldown = (now - s_acknowledge_time) < ACKNOWLEDGE_COOLDOWN_MS;
    
    /* Stuck fermentation */
    if ((alerts & ALERT_STUCK_FERMENT) && s_config.alarm_on_stuck && !in_cooldown) {
        s_active = true;
        s_current_pattern = ALARM_PATTERN_SIREN;
        snprintf(s_alarm_description, sizeof(s_alarm_description),
                 "STUCK FERMENT! Gravity stable at %.4f", gravity);
        alarm_set_led(255, 0, 0);  /* Red */
    }
    /* Fermentation finished */
    else if ((alerts & ALERT_FINISHED) && s_config.alarm_on_finished && !in_cooldown) {
        s_active = true;
        s_current_pattern = ALARM_PATTERN_HAPPY;
        snprintf(s_alarm_description, sizeof(s_alarm_description),
                 "FERMENTATION DONE! FG = %.4f", gravity);
        alarm_set_led(0, 255, 0);  /* Green */
    }
    /* High temperature */
    else if (temperature > s_config.temp_high_threshold && !in_cooldown) {
        s_active = true;
        s_current_pattern = ALARM_PATTERN_DOUBLE_BEEP;
        snprintf(s_alarm_description, sizeof(s_alarm_description),
                 "HIGH TEMP: %.1f C (threshold %.1f C)", temperature, s_config.temp_high_threshold);
        alarm_set_led(255, 128, 0);  /* Orange */
    }
    /* Low temperature */
    else if (temperature < s_config.temp_low_threshold && !in_cooldown) {
        s_active = true;
        s_current_pattern = ALARM_PATTERN_DOUBLE_BEEP;
        snprintf(s_alarm_description, sizeof(s_alarm_description),
                 "LOW TEMP: %.1f C (threshold %.1f C)", temperature, s_config.temp_low_threshold);
        alarm_set_led(0, 128, 255);  /* Light blue */
    }
    /* pH too low */
    else if ((alerts & ALERT_PH_LOW) && !in_cooldown) {
        s_active = true;
        s_current_pattern = ALARM_PATTERN_SHORT_BEEP;
        snprintf(s_alarm_description, sizeof(s_alarm_description),
                 "LOW pH: %.2f (threshold %.1f)", ph, s_config.ph_low_threshold);
        alarm_set_led(255, 0, 255);  /* Purple */
    }
    /* pH too high */
    else if ((alerts & ALERT_PH_HIGH) && !in_cooldown) {
        s_active = true;
        s_current_pattern = ALARM_PATTERN_SHORT_BEEP;
        snprintf(s_alarm_description, sizeof(s_alarm_description),
                 "HIGH pH: %.2f (threshold %.1f)", ph, s_config.ph_high_threshold);
        alarm_set_led(255, 255, 0);  /* Yellow */
    }
    /* Normal operation — stage indicator */
    else {
        switch (stage) {
            case FERMENT_LAG:
                alarm_set_led(0, 0, 255);    /* Blue */
                break;
            case FERMENT_ACTIVE:
                alarm_set_led(0, 255, 0);    /* Green */
                break;
            case FERMENT_PEAK:
                alarm_set_led(0, 255, 128);  /* Cyan-green */
                break;
            case FERMENT_SLOWING:
                alarm_set_led(255, 255, 0);  /* Yellow */
                break;
            case FERMENT_FINISHED:
                alarm_set_led(0, 255, 0);    /* Green */
                break;
            case FERMENT_STUCK:
                alarm_set_led(255, 0, 0);    /* Red */
                break;
            default:
                alarm_set_led(128, 128, 128);  /* Gray */
                break;
        }
    }
    
    /* Play alarm pattern if active */
    if (s_active && s_config.enable_buzzer) {
        alarm_play(s_current_pattern);
    } else {
        /* Turn off buzzer */
        __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 0);
    }
}

/*----------------------------------------------------------------------------*/

void alarm_play(alarm_pattern_t pattern) {
    if (!s_config.enable_buzzer) return;
    
    switch (pattern) {
        case ALARM_PATTERN_SHORT_BEEP:
            /* 200ms beep at 2kHz */
            __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 50);  /* 50% duty */
            HAL_Delay(200);
            __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 0);
            break;
            
        case ALARM_PATTERN_DOUBLE_BEEP:
            /* Two 200ms beeps with 200ms gap */
            __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 50);
            HAL_Delay(200);
            __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 0);
            HAL_Delay(200);
            __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 50);
            HAL_Delay(200);
            __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 0);
            break;
            
        case ALARM_PATTERN_LONG_BEEP:
            /* 1000ms beep */
            __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 50);
            HAL_Delay(1000);
            __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 0);
            break;
            
        case ALARM_PATTERN_SIREN:
            /* Alternating tone (2000Hz / 2500Hz) for 3 seconds */
            for (int i = 0; i < 6; i++) {
                /* High tone */
                __HAL_TIM_SET_PRESCALER(&htim15, 0);
                __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 50);
                HAL_Delay(250);
                /* Low tone */
                __HAL_TIM_SET_PRESCALER(&htim15, 1);
                __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 50);
                HAL_Delay(250);
            }
            __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 0);
            break;
            
        case ALARM_PATTERN_HAPPY:
            /* Ascending tone (1000Hz → 3000Hz) */
            for (int freq = 1000; freq <= 3000; freq += 100) {
                uint32_t arr = SystemCoreClock / freq;
                __HAL_TIM_SET_AUTORELOAD(&htim15, arr);
                __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, arr / 2);
                HAL_Delay(50);
            }
            __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 0);
            break;
            
        case ALARM_PATTERN_TICK:
            /* Brief 50ms click */
            __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 50);
            HAL_Delay(50);
            __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 0);
            break;
            
        default:
            break;
    }
}

/*----------------------------------------------------------------------------*/

void alarm_set_led(uint8_t r, uint8_t g, uint8_t b) {
    if (!s_config.enable_led) return;
    
    /* RGB LED is active-low (common anode) */
    /* For simple on/off, we just use GPIO.
     * For dimming, we'd use PWM. Here: threshold at 128. */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_15, r > 128 ? GPIO_PIN_RESET : GPIO_PIN_SET);  /* Red */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_7, g > 128 ? GPIO_PIN_RESET : GPIO_PIN_SET);   /* Green */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_8, b > 128 ? GPIO_PIN_RESET : GPIO_PIN_SET);   /* Blue */
}

/*----------------------------------------------------------------------------*/

void alarm_silence(void) {
    /* Turn off buzzer */
    __HAL_TIM_SET_COMPARE(&htim15, TIM_CHANNEL_1, 0);
    
    /* Turn off LED */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_15, GPIO_PIN_SET);  /* Red off */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_7, GPIO_PIN_SET);   /* Green off */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_8, GPIO_PIN_SET);   /* Blue off */
    
    s_active = false;
    s_current_pattern = ALARM_PATTERN_NONE;
}

/*----------------------------------------------------------------------------*/

bool alarm_is_active(void) {
    return s_active;
}

/*----------------------------------------------------------------------------*/

void alarm_acknowledge(void) {
    s_acknowledge_time = HAL_GetTick();
    alarm_silence();
}

/*----------------------------------------------------------------------------*/

const char *alarm_get_description(void) {
    return s_alarm_description;
}