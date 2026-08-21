# dent-scope / firmware/Core/Src/stm32g4xx_hal_msp.c
# Dent Scope — HAL MSP initialization (peripheral clock + pin config)
# MIT License
#include "stm32g4xx_hal.h"

extern I2C_HandleTypeDef hi2c1;
extern SPI_HandleTypeDef hspi1, hspi2;
extern UART_HandleTypeDef huart1;
extern ADC_HandleTypeDef hadc1;

void HAL_MspInit(void)
{
    __HAL_RCC_SYSCFG_CLK_ENABLE();
    __HAL_RCC_PWR_CLK_ENABLE();
}

void HAL_I2C_MspInit(I2C_HandleTypeDef *h)
{
    if (h->Instance == I2C1) {
        __HAL_RCC_I2C1_CLK_ENABLE();
        GPIO_InitTypeDef g = {0};
        g.Mode = GPIO_MODE_AF_OD;
        g.Pull = GPIO_PULLUP;
        g.Speed = GPIO_SPEED_FREQ_HIGH;
        g.Alternate = GPIO_AF4_I2C1;
        g.Pin = GPIO_PIN_8 | GPIO_PIN_9;
        HAL_GPIO_Init(GPIOB, &g);
    }
}

void HAL_SPI_MspInit(SPI_HandleTypeDef *h)
{
    if (h->Instance == SPI1) {
        __HAL_RCC_SPI1_CLK_ENABLE();
        GPIO_InitTypeDef g = {0};
        g.Mode = GPIO_MODE_AF_PP;
        g.Pull = GPIO_NOPULL;
        g.Speed = GPIO_SPEED_FREQ_HIGH;
        g.Alternate = GPIO_AF5_SPI1;
        g.Pin = GPIO_PIN_3 | GPIO_PIN_4 | GPIO_PIN_5;
        HAL_GPIO_Init(GPIOB, &g);
    } else if (h->Instance == SPI2) {
        __HAL_RCC_SPI2_CLK_ENABLE();
        GPIO_InitTypeDef g = {0};
        g.Mode = GPIO_MODE_AF_PP;
        g.Pull = GPIO_NOPULL;
        g.Speed = GPIO_SPEED_FREQ_HIGH;
        g.Alternate = GPIO_AF5_SPI2;
        g.Pin = GPIO_PIN_10 | GPIO_PIN_11;
        HAL_GPIO_Init(GPIOB, &g);
    }
}

void HAL_UART_MspInit(UART_HandleTypeDef *h)
{
    if (h->Instance == USART1) {
        __HAL_RCC_USART1_CLK_ENABLE();
        GPIO_InitTypeDef g = {0};
        g.Mode = GPIO_MODE_AF_PP;
        g.Pull = GPIO_NOPULL;
        g.Speed = GPIO_SPEED_FREQ_HIGH;
        g.Alternate = GPIO_AF7_USART1;
        g.Pin = GPIO_PIN_9 | GPIO_PIN_10;
        HAL_GPIO_Init(GPIOA, &g);
    }
}

void HAL_ADC_MspInit(ADC_HandleTypeDef *h)
{
    if (h->Instance == ADC1) {
        __HAL_RCC_ADC12_CLK_ENABLE();
        GPIO_InitTypeDef g = {0};
        g.Mode = GPIO_MODE_ANALOG;
        g.Pull = GPIO_NOPULL;
        g.Pin = GPIO_PIN_0;
        HAL_GPIO_Init(GPIOA, &g);
    }
}