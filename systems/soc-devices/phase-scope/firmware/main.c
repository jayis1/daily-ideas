/*
 * Phase Scope — 3-Phase Power Quality Analyzer
 * Main entry point
 * STM32G491RET6, CMSIS + HAL
 *
 * MIT License
 */

#include "main.h"
#include "adc.h"
#include "power_quality.h"
#include "fft.h"
#include "display.h"
#include "ble_uart.h"
#include "sd_log.h"
#include "calibration.h"

#include <string.h>
#include <math.h>

/* ------------------------------------------------------------------ */
/* Global state                                                        */
/* ------------------------------------------------------------------ */

volatile uint32_t system_tick = 0;
volatile uint8_t  display_page = PAGE_PHASOR;
volatile uint8_t  logging_active = 0;
volatile uint8_t  ble_streaming = 0;

/* Calibration data (loaded from flash) */
calibration_t cal = {
    .v_gain = {1.0f, 1.0f, 1.0f},
    .i_gain = {1.0f, 1.0f, 1.0f},
    .v_offset = {0.0f, 0.0f, 0.0f},
    .i_offset = {0.0f, 0.0f, 0.0f},
    .phase_offset = {0.0f, -2.094f, -4.189f}, /* -120°, -240° */
    .shunt_res = {0.1f, 100.0f, 100.0f},  /* Ohm */
    .v_divider_ratio = 471.0f, /* 470k / 1k */
    .amc_gain = 8.2f,
};

/* Measurement results */
power_results_t results;

/* ------------------------------------------------------------------ */
/* SysTick handler                                                     */
/* ------------------------------------------------------------------ */

void SysTick_Handler(void)
{
    system_tick++;
}

/* ------------------------------------------------------------------ */
/* Button handlers (interrupt)                                         */
/* ------------------------------------------------------------------ */

volatile uint8_t button_event = 0;

void EXTI15_10_IRQHandler(void)
{
    /* Check which button triggered the interrupt */
    if (EXTI->PR1 & (1 << 13)) {
        EXTI->PR1 = (1 << 13);
        button_event = BTN_MODE;
    }
    if (EXTI->PR1 & (1 << 14)) {
        EXTI->PR1 = (1 << 14);
        button_event = BTN_SELECT;
    }
    if (EXTI->PR1 & (1 << 15)) {
        EXTI->PR1 = (1 << 15);
        button_event = BTN_HOLD;
    }
}

/* ------------------------------------------------------------------ */
/* Watchdog — safety timeout                                           */
/* ------------------------------------------------------------------ */

static void watchdog_init(void)
{
    /* IWDG: 1 second timeout */
    IWDG->KR  = 0x5555;                     /* Enable register access */
    IWDG->PR  = IWDG_PR_4;                  /* Prescaler /64 */
    IWDG->RLR = 0x0F9C;                     /* Reload: ~1s at 40kHz */
    IWDG->KR  = 0xCCCC;                     /* Start watchdog */
}

static inline void watchdog_feed(void)
{
    IWDG->KR = 0xAAAA;
}

/* ------------------------------------------------------------------ */
/* Clock configuration                                                 */
/* ------------------------------------------------------------------ */

static void clock_init(void)
{
    /* Enable HSE (8 MHz crystal on board) */
    RCC->CR |= RCC_CR_HSEON;
    while (!(RCC->CR & RCC_CR_HSERDY))
        ;

    /* Configure PLL: HSE × 17 / 2 = 68 MHz (slightly under max 170MHz)
     * Actually, let's go for 170 MHz: HSE=8MHz, PLLM=1, PLLN=85, PLLR=2
     *  → 8 * 85 / 2 = 340 MHz PLL VCO, /2 = 170 MHz SYSCLK
     */
    RCC->PLLCFGR = (1 << RCC_PLLCFGR_PLLM_Pos)      | /* PLLM = 1 */
                   (85 << RCC_PLLCFGR_PLLN_Pos)      | /* PLLN = 85 */
                   (0 << RCC_PLLCFGR_PLLR_Pos)        | /* PLLR = 2 */
                   (RCC_PLLCFGR_PLLSRC_HSE)           ; /* PLLSRC = HSE */

    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY))
        ;

    /* Flash latency: 5 wait states for 170 MHz at 3.3V */
    FLASH->ACR = FLASH_ACR_LATENCY_5WS | FLASH_ACR_ICEN | FLASH_ACR_DCEN;

    /* Switch SYSCLK to PLL */
    RCC->CFGR = (RCC_CFGR_SW_PLL << RCC_CFGR_SW_Pos);
    while ((RCC->CFGR & RCC_CFGR_SWS) != (RCC_CFGR_SW_PLL << RCC_CFGR_SWS_Pos))
        ;

    SystemCoreClock = 170000000;
}

/* ------------------------------------------------------------------ */
/* GPIO configuration                                                  */
/* ------------------------------------------------------------------ */

static void gpio_init(void)
{
    /* Enable all GPIO port clocks */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN |
                     RCC_AHB2ENR_GPIOCEN | RCC_AHB2ENR_GPIODEN;

    /* --- Analog inputs (PA0-PA6) --- */
    GPIOA->MODER = (GPIOA->MODER & ~(0x3FFF)) /* Clear PA0-PA6 mode */
                 | (0x3 << 0)   /* PA0: Analog (ADC1_IN1, V1) */
                 | (0x3 << 2)   /* PA1: Analog (ADC1_IN2, V2) */
                 | (0x3 << 4)   /* PA2: Analog (ADC1_IN3, V3) */
                 | (0x3 << 6)   /* PA3: Analog (ADC2_IN4, I1) */
                 | (0x3 << 8)   /* PA4: Analog (ADC2_IN5, I2) */
                 | (0x3 << 10)  /* PA5: Analog (ADC2_IN6, I3) */
                 | (0x3 << 12); /* PA6: Analog (DAC1_OUT) */

    /* --- SPI1 pins (OLED + SD card) --- */
    /* PA7 = SPI1_MOSI (AF5) */
    GPIOA->MODER = (GPIOA->MODER & ~(0x3 << 14)) | (0x2 << 14);
    GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xF << 28)) | (5 << 28);

    /* PB3 = SPI1_SCK (AF5) */
    GPIOB->MODER = (GPIOB->MODER & ~(0x3 << 6)) | (0x2 << 6);
    GPIOB->AFR[0] = (GPIOB->AFR[0] & ~(0xF << 12)) | (5 << 12);

    /* PB4 = SPI1_MISO (AF5) */
    GPIOB->MODER = (GPIOB->MODER & ~(0x3 << 8)) | (0x2 << 8);
    GPIOB->AFR[0] = (GPIOB->AFR[0] & ~(0xF << 16)) | (5 << 16);

    /* --- OLED control pins --- */
    /* PB5 = OLED_DC (output) */
    GPIOB->MODER = (GPIOB->MODER & ~(0x3 << 10)) | (0x1 << 10);
    /* PB13 = OLED_CS (output) */
    GPIOB->MODER = (GPIOB->MODER & ~(0x3 << 26)) | (0x1 << 26);
    /* PC5 = OLED_RST (output) */
    GPIOC->MODER = (GPIOC->MODER & ~(0x3 << 10)) | (0x1 << 10);

    /* --- SD card CS --- */
    /* PB12 = SD_CS (output, active low, default high) */
    GPIOB->MODER = (GPIOB->MODER & ~(0x3 << 24)) | (0x1 << 24);
    GPIOB->ODR  |= (1 << 12); /* CS high = deselected */

    /* --- UART4 for BLE (PC10=TX, PC11=RX, AF5) --- */
    GPIOC->MODER = (GPIOC->MODER & ~((0x3 << 20) | (0x3 << 22)))
                 | (0x2 << 20) | (0x2 << 22);
    GPIOC->AFR[1] = (GPIOC->AFR[1] & ~((0xF << 8) | (0xF << 12)))
                  | (5 << 8) | (5 << 12);

    /* --- Debug UART1 (PA9=TX, PA10=RX, AF7) --- */
    GPIOA->MODER = (GPIOA->MODER & ~((0x3 << 18) | (0x3 << 20)))
                 | (0x2 << 18) | (0x2 << 20);
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~((0xF << 4) | (0xF << 8)))
                  | (7 << 4) | (7 << 8);

    /* --- Status LEDs (PB14, PB15, PC0, PC1 = output) --- */
    GPIOB->MODER = (GPIOB->MODER & ~((0x3 << 28) | (0x3 << 30)))
                 | (0x1 << 28) | (0x1 << 30);
    GPIOC->MODER = (GPIOC->MODER & ~((0x3 << 0) | (0x3 << 2)))
                 | (0x1 << 0) | (0x1 << 2);

    /* --- Range relays (PC2, PC3, PC4 = output) --- */
    GPIOC->MODER = (GPIOC->MODER & ~((0x3 << 4) | (0x3 << 6) | (0x3 << 8)))
                 | (0x1 << 4) | (0x1 << 6) | (0x1 << 8);

    /* --- Buttons (PC13, PC14, PC15 = input with pull-up) --- */
    GPIOC->MODER &= ~((0x3 << 26) | (0x3 << 28) | (0x3 << 30)); /* Input */
    GPIOC->PUPDR = (GPIOC->PUPDR & ~((0x3 << 26) | (0x3 << 28) | (0x3 << 30)))
                 | (0x1 << 26) | (0x1 << 28) | (0x1 << 30); /* Pull-up */

    /* --- Power enable (PD2 = output, default high) --- */
    GPIOD->MODER = (GPIOD->MODER & ~(0x3 << 4)) | (0x1 << 4);
    GPIOD->ODR  |= (1 << 2);

    /* --- Buzzer (PC6 = TIM3_CH1, AF2) --- */
    GPIOC->MODER = (GPIOC->MODER & ~(0x3 << 12)) | (0x2 << 12);
    GPIOC->AFR[0] = (GPIOC->AFR[0] & ~(0xF << 24)) | (2 << 24);

    /* --- NTC input (PB0 = analog) --- */
    GPIOB->MODER = (GPIOB->MODER & ~(0x3 << 0)) | (0x3 << 0);

    /* --- Button EXTI interrupts --- */
    EXTI->IMR1 |= (1 << 13) | (1 << 14) | (1 << 15);
    EXTI->FTSR1 |= (1 << 13) | (1 << 14) | (1 << 15); /* Falling edge */
    NVIC_SetPriority(EXTI15_10_IRQn, 3);
    NVIC_EnableIRQ(EXTI15_10_IRQn);
}

/* ------------------------------------------------------------------ */
/* Main loop                                                           */
/* ------------------------------------------------------------------ */

int main(void)
{
    uint32_t last_measurement = 0;
    uint32_t last_display = 0;
    uint32_t last_ble = 0;
    uint32_t last_log = 0;

    /* Initialize hardware */
    clock_init();
    gpio_init();
    watchdog_init();

    /* Initialize peripherals */
    adc_init();
    display_init();
    ble_uart_init();
    sd_log_init();

    /* Load calibration from flash */
    calibration_load(&cal);

    /* Splash screen */
    display_clear();
    display_draw_string(16, 0, "Phase Scope", FONT_LARGE);
    display_draw_string(8, 20, "3-Phase Power QA", FONT_SMALL);
    display_draw_string(16, 35, "v1.0.0", FONT_SMALL);
    display_draw_string(4, 50, "Initializing...", FONT_SMALL);
    display_update();
    delay_ms(1500);

    /* Main loop */
    while (1) {
        watchdog_feed();

        /* Handle button events */
        if (button_event) {
            uint8_t btn = button_event;
            button_event = 0;

            switch (btn) {
            case BTN_MODE:
                display_page = (display_page + 1) % NUM_PAGES;
                break;
            case BTN_SELECT:
                logging_active = !logging_active;
                if (logging_active)
                    sd_log_start();
                else
                    sd_log_stop();
                break;
            case BTN_HOLD:
                /* Hold current readings on display */
                break;
            }
        }

        /* Measurement cycle — every 5ms (200 Hz update) */
        if (system_tick - last_measurement >= 5) {
            last_measurement = system_tick;

            /* Read ADCs (double-buffered DMA fills in background) */
            /* Compute RMS, power, PF, THD */
            power_quality_compute(&results);
        }

        /* Display update — every 100ms */
        if (system_tick - last_display >= 100) {
            last_display = system_tick;
            display_render_page(display_page, &results);
        }

        /* BLE streaming — every 500ms */
        if (ble_streaming && (system_tick - last_ble >= 50)) {
            last_ble = system_tick;
            ble_uart_send_status(&results);
        }

        /* SD card logging — every 1s */
        if (logging_active && (system_tick - last_log >= 1000)) {
            last_log = system_tick;
            sd_log_write(&results);
        }

        /* Low-power: WFI when idle */
        __WFI();
    }
}

/* ------------------------------------------------------------------ */
/* Delay functions                                                      */
/* ------------------------------------------------------------------ */

void delay_ms(uint32_t ms)
{
    uint32_t start = system_tick;
    while ((system_tick - start) < ms)
        ;
}

void delay_us(uint32_t us)
{
    /* Approximate microsecond delay using DWT cycle counter */
    uint32_t start = DWT->CYCCNT;
    uint32_t cycles = us * (SystemCoreClock / 1000000);
    while ((DWT->CYCCNT - start) < cycles)
        ;
}