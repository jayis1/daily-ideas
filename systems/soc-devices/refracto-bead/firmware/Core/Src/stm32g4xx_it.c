/**
 * stm32g4xx_it.c — Interrupt handlers for the Refracto Bead
 */

#include "stm32g4xx_hal.h"

extern void ADC1_2_IRQHandler(void);
extern void EXTI9_5_IRQHandler(void);
extern void EXTI10_15_IRQHandler(void);
extern void USART1_IRQHandler(void);
extern void SPI2_IRQHandler(void);
extern void I2C1_IRQHandler(void);
extern void TIM2_IRQHandler(void);

/* These are defined in main.c */
void HAL_GPIO_EXTI_Callback(uint16_t pin);

/* Default handler — weak overrides are in HAL */

void NMI_Handler(void) {
    while (1);
}

void HardFault_Handler(void) {
    while (1);
}

void MemManage_Handler(void) {
    while (1);
}

void BusFault_Handler(void) {
    while (1);
}

void UsageFault_Handler(void) {
    while (1);
}

void SVC_Handler(void) {
}

void DebugMon_Handler(void) {
}

void PendSV_Handler(void) {
}

void SysTick_Handler(void) {
    HAL_IncTick();
}