/*
 * led.c — RGB status LED driver (GPIO bit-banged PWM)
 * Opti Rot — Pocket Digital Polarimeter
 *
 * Uses three GPIO pins (PB2=Red, PB3=Green, PB4=Blue) with simple
 * software PWM for brightness control. In production, use TIM PWM
 * channels for hardware PWM.
 */
#include "stm32g4xx_hal.h"
#include "sdkconfig.h"
#include "led.h"

#define LED_PORT    GPIOB
#define LED_R_PIN   GPIO_PIN_2
#define LED_G_PIN   GPIO_PIN_3
#define LED_B_PIN   GPIO_PIN_4

static uint8_t current_color = LED_COLOR_OFF;
static uint8_t current_brightness = 0;

void led_init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin   = LED_R_PIN | LED_G_PIN | LED_B_PIN;
    GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull  = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(LED_PORT, &GPIO_InitStruct);

    HAL_GPIO_WritePin(LED_PORT, LED_R_PIN | LED_G_PIN | LED_B_PIN, GPIO_PIN_RESET);
}

void led_set_color(uint8_t color, uint8_t brightness)
{
    current_color = color;
    current_brightness = brightness;

    /* Simple on/off (brightness > 128 = on, else off).
     * In production, use TIM2 PWM channels for smooth dimming. */
    uint8_t r = 0, g = 0, b = 0;
    if (brightness > 128) {
        switch (color) {
        case LED_COLOR_RED:     r = 1; break;
        case LED_COLOR_GREEN:   g = 1; break;
        case LED_COLOR_BLUE:    b = 1; break;
        case LED_COLOR_YELLOW:  r = 1; g = 1; break;
        case LED_COLOR_CYAN:    g = 1; b = 1; break;
        case LED_COLOR_MAGENTA: r = 1; b = 1; break;
        case LED_COLOR_WHITE:   r = 1; g = 1; b = 1; break;
        default: break;
        }
    }

    HAL_GPIO_WritePin(LED_PORT, LED_R_PIN, r ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(LED_PORT, LED_G_PIN, g ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(LED_PORT, LED_B_PIN, b ? GPIO_PIN_SET : GPIO_PIN_RESET);
}