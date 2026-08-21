/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * stm32g474.h — Minimal register definitions for STM32G474RET6
 *
 * This is a simplified set of register definitions covering the peripherals
 * used by the firmware. A full build would use ST's STM32G4 HAL/CMSIS headers
 * instead of this stub.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef STM32G474_H
#define STM32G474_H

#include <stdint.h>

/* ---- Cortex-M4 system control ---- */
typedef struct {
    volatile uint32_t CPACR;
    /* ... full SCB omitted ... */
} SCB_TypeDef;
#define SCB ((SCB_TypeDef *)0xE000ED00U)

/* ---- RCC ---- */
typedef struct {
    volatile uint32_t CR;
    volatile uint32_t ICSCR;
    volatile uint32_t CFGR;
    /* ... full RCC omitted ... */
    volatile uint32_t AHB2ENR;
    volatile uint32_t AHB1ENR;
    volatile uint32_t AHB3ENR;
    volatile uint32_t APB1ENR1;
    volatile uint32_t APB1ENR2;
    volatile uint32_t APB2ENR;
    /* ... */
    volatile uint32_t PLLCFGR;
} RCC_TypeDef;

#define RCC_BASE        0x40021000U
#define RCC             ((RCC_TypeDef *)RCC_BASE)

/* RCC bit positions (simplified) */
#define RCC_CR_HSION    (1U << 8)
#define RCC_CR_HSIRDY   (1U << 10)
#define RCC_CR_PLLON    (1U << 24)
#define RCC_CR_PLLRDY   (1U << 25)
#define RCC_PLLCFGR_PLLM_Pos  4
#define RCC_PLLCFGR_PLLN_Pos  8
#define RCC_PLLCFGR_PLLR_Pos 25
#define RCC_CFGR_SW_Pos      0
#define RCC_CFGR_SW_PLL     2
#define RCC_CFGR_SWS_Pos    3
#define RCC_CFGR_SWS_Msk    (3U << 3)
#define RCC_AHB2ENR_GPIOAEN  (1U << 0)
#define RCC_AHB2ENR_GPIOBEN  (1U << 1)
#define RCC_AHB2ENR_GPIOCEN  (1U << 2)
#define RCC_AHB2ENR_ADC12EN  (1U << 13)
#define RCC_AHB2ENR_DMA1EN   (1U << 0)   /* in AHB1ENR — approximated here */
#define RCC_AHB1ENR_DMA1EN   (1U << 0)
#define RCC_APB1ENR1_USART3EN (1U << 18)
#define RCC_APB1ENR1_I2C1EN   (1U << 21)
#define RCC_APB2ENR_SPI1EN    (1U << 12)
#define RCC_APB2ENR_HRTIM1EN  (1U << 28)  /* actually APB2ENR bit 28 */
#define RCC_AHB2ENR_DAC1EN    (1U << 16)

/* ---- GPIO ---- */
typedef struct {
    volatile uint32_t MODER;
    volatile uint32_t OTYPER;
    volatile uint32_t OSPEEDR;
    volatile uint32_t PUPDR;
    volatile uint32_t IDR;
    volatile uint32_t ODR;
    volatile uint32_t BSRR;
    volatile uint32_t LCKR;
    volatile uint32_t AFR[2];
    volatile uint32_t BRR;
} GPIO_TypeDef;

#define GPIOA ((GPIO_TypeDef *)0x48000000U)
#define GPIOB ((GPIO_TypeDef *)0x48000400U)
#define GPIOC ((GPIO_TypeDef *)0x48000800U)

#define GPIO_MODER_MODE0   (3U << 0)
#define GPIO_MODER_MODE1   (3U << 2)
#define GPIO_MODER_MODE2   (3U << 4)
#define GPIO_MODER_MODE3   (3U << 6)
#define GPIO_MODER_MODE4   (3U << 8)
#define GPIO_MODER_MODE5   (3U << 10)
#define GPIO_MODER_MODE6   (3U << 12)
#define GPIO_MODER_MODE7   (3U << 14)
#define GPIO_MODER_MODE8   (3U << 16)
#define GPIO_MODER_MODE10  (3U << 20)
#define GPIO_MODER_MODE11  (3U << 22)
#define GPIO_MODER_MODE12  (3U << 24)
#define GPIO_MODER_MODE13  (3U << 26)
#define GPIO_MODER_MODE14  (3U << 28)
#define GPIO_MODER_MODE15  (3U << 30)
#define GPIO_MODER_MODE0_Pos  0
#define GPIO_MODER_MODE1_Pos  2
#define GPIO_MODER_MODE3_Pos  6
#define GPIO_MODER_MODE5_Pos  10
#define GPIO_MODER_MODE6_Pos  12
#define GPIO_MODER_MODE7_Pos  14
#define GPIO_MODER_MODE8_Pos  16
#define GPIO_MODER_MODE9_Pos  18
#define GPIO_MODER_MODE10_Pos 20
#define GPIO_MODER_MODE11_Pos 22
#define GPIO_MODER_MODE12_Pos 24
#define GPIO_MODER_MODE13_Pos 26
#define GPIO_MODER_MODE15_Pos 30
#define GPIO_OTYPER_OT6   (1U << 6)
#define GPIO_OTYPER_OT7   (1U << 7)
#define GPIO_OTYPER_OT8   (1U << 8)
#define GPIO_OTYPER_OT10  (1U << 10)
#define GPIO_OTYPER_OT11  (1U << 11)
#define GPIO_PUPDR_PUPD9_Pos  18
#define GPIO_PUPDR_PUPD10_Pos 20
#define GPIO_PUPDR_PUPD11_Pos 22
#define GPIO_PUPDR_PUPD12_Pos 24
#define GPIO_PUPDR_PUPD14_Pos 28
#define GPIO_PUPDR_PUPD15_Pos 30

/* ---- DMA ---- */
typedef struct {
    volatile uint32_t ISR;
    volatile uint32_t Reserved0;
    volatile uint32_t IFCR;
} DMA_TypeDef;
typedef struct {
    volatile uint32_t CCR;
    volatile uint32_t CNDTR;
    volatile uint32_t CPAR;
    volatile uint32_t CMAR;
    volatile uint32_t Reserved;
} DMA_Channel_TypeDef;

#define DMA1_BASE       0x40020000U
#define DMA1           ((DMA_TypeDef *)DMA1_BASE)
#define DMA1_Channel1  ((DMA_Channel_TypeDef *)(DMA1_BASE + 0x08))
#define DMA1_Channel2  ((DMA_Channel_TypeDef *)(DMA1_BASE + 0x1C))
#define DMA1_Channel3  ((DMA_Channel_TypeDef *)(DMA1_BASE + 0x30))

#define DMA_ISR_TCIF1   (1U << 0)
#define DMA_IFCR_CTCIF1 (1U << 0)
#define DMA_CCR_EN      (1U << 0)
#define DMA_CCR_TCIE    (1U << 1)
#define DMA_CCR_MINC    (1U << 7)
#define DMA_CCR_DIR     (1U << 4)
#define DMA_CCR_CIRC    (1U << 8)
#define DMA_CCR_MSIZE_0 (1U << 10)
#define DMA_CCR_MSIZE_1 (2U << 10)
#define DMA_CCR_PSIZE_0 (1U << 8)
#define DMA_CCR_PSIZE_1 (2U << 8)
#define DMA_CCR_PL_1    (2U << 12)

/* ---- ADC ---- */
typedef struct {
    volatile uint32_t ISR;
    volatile uint32_t IER;
    volatile uint32_t CR;
    volatile uint32_t CFGR;
    volatile uint32_t CFGR2;
    volatile uint32_t SMPR1;
    volatile uint32_t SMPR2;
    /* ... */
    volatile uint32_t SQR1;
    /* ... */
    volatile uint32_t DR;
} ADC_TypeDef;

typedef struct {
    volatile uint32_t CCR;
} ADC_Common_TypeDef;

#define ADC1_BASE        0x50000000U
#define ADC2_BASE        0x50000100U
#define ADC12_COMMON_BASE 0x50000300U
#define ADC1            ((ADC_TypeDef *)ADC1_BASE)
#define ADC2            ((ADC_TypeDef *)ADC2_BASE)
#define ADC12_COMMON    ((ADC_Common_TypeDef *)ADC12_COMMON_BASE)

#define ADC_CCR_CKMODE_Pos 16
#define ADC_CR_ADVREGEN  (1U << 28)
#define ADC_CR_CAL       (1U << 16)
#define ADC_CR_ADEN      (1U << 0)
#define ADC_CR_ADSTART   (1U << 2)
#define ADC_CR_ADSTP     (1U << 4)
#define ADC_ISR_ADRDY    (1U << 0)
#define ADC_SQR1_SQ1_Pos 6
#define ADC_SQR1_L_Pos   0
#define ADC_SMPR1_SMP3_Pos 9
#define ADC_SMPR1_SMP4_Pos 12
#define ADC_CFGR_DMAEN   (1U << 0)
#define ADC_CFGR_DMACFG  (1U << 1)
#define ADC_CFGR_EXTSEL_Pos 6
#define ADC_CFGR_EXTEN_0 (1U << 10)

/* ---- DAC ---- */
typedef struct {
    volatile uint32_t CR;
    volatile uint32_t SWTRIGR;
    volatile uint32_t DHR12R1;
    volatile uint32_t DHR12R2;
    /* ... */
    volatile uint32_t DOR1;
    volatile uint32_t DOR2;
    /* ... */
    volatile uint32_t MCR;
} DAC_TypeDef;

#define DAC1_BASE       0x50000800U
#define DAC1           ((DAC_TypeDef *)DAC1_BASE)

#define DAC_CR_EN1      (1U << 0)
#define DAC_CR_EN2      (1U << 16)
#define DAC_CR_DMAEN1   (1U << 12)
#define DAC_CR_DMAEN2   (1U << 28)
#define DAC_CR_TSEL1_0  (1U << 3)

/* ---- SPI ---- */
typedef struct {
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    volatile uint32_t SR;
    volatile uint32_t DR;
    /* ... */
} SPI_TypeDef;

#define SPI1_BASE       0x42000000U
#define SPI1           ((SPI_TypeDef *)SPI1_BASE)

#define SPI_CR1_MSTR    (1U << 2)
#define SPI_CR1_CPOL    (1U << 1)
#define SPI_CR1_CPHA    (1U << 0)
#define SPI_CR1_BR_Pos  3
#define SPI_CR1_SSM     (1U << 9)
#define SPI_CR1_SSI     (1U << 10)
#define SPI_CR1_SPE     (1U << 6)
#define SPI_SR_TXE      (1U << 1)
#define SPI_SR_BSY      (1U << 7)

/* ---- USART ---- */
typedef struct {
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    volatile uint32_t CR3;
    volatile uint32_t BRR;
    volatile uint32_t GTPR;
    volatile uint32_t RTOR;
    volatile uint32_t RQR;
    volatile uint32_t ISR;
    volatile uint32_t ICR;
    volatile uint32_t RDR;
    volatile uint32_t TDR;
} USART_TypeDef;

#define USART3_BASE      0x40004800U
#define USART3          ((USART_TypeDef *)USART3_BASE)

#define USART_CR1_UE     (1U << 0)
#define USART_CR1_TE     (1U << 3)
#define USART_CR1_RE     (1U << 2)
#define USART_CR1_RXNEIE (1U << 5)
#define USART_ISR_TXE    (1U << 7)
#define USART_ISR_RXNE   (1U << 5)
#define USART_ISR_TC     (1U << 6)

/* ---- I2C ---- */
typedef struct {
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    volatile uint32_t OAR1;
    volatile uint32_t OAR2;
    volatile uint32_t TIMINGR;
    volatile uint32_t TIMEOUTR;
    volatile uint32_t ISR;
    volatile uint32_t ICR;
    volatile uint32_t PECR;
    volatile uint32_t RXDR;
    volatile uint32_t TXDR;
} I2C_TypeDef;

#define I2C1_BASE        0x40005400U
#define I2C1            ((I2C_TypeDef *)I2C1_BASE)

#define I2C_CR1_PE       (1U << 0)
#define I2C_CR2_START    (1U << 13)
#define I2C_CR2_STOP     (1U << 14)
#define I2C_CR2_RD_WRN   (1U << 10)
#define I2C_ISR_TXIS     (1U << 1)
#define I2C_ISR_RXNE     (1U << 2)

/* ---- HRTIM (simplified — high-resolution timer) ---- */
typedef struct {
    volatile uint32_t CMP1xR;
    volatile uint32_t CMP2xR;
    volatile uint32_t CMP3xR;
    volatile uint32_t CMP4xR;
    volatile uint32_t PERxR;
    volatile uint32_t REPxR;
    volatile uint32_t TIMA_CR;
    /* ... */
} HRTIM_Timer_TypeDef;

typedef struct {
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    /* ... */
} HRTIM_Common_TypeDef;

typedef struct {
    volatile uint32_t MCMP1R;
    volatile uint32_t MCMP2R;
    volatile uint32_t MCMP3R;
    volatile uint32_t MCMP4R;
    volatile uint32_t MPER;
    volatile uint32_t MREP;
    volatile uint32_t MCR;
} HRTIM_Master_TypeDef;

#define HRTIM1_BASE      0x40016800U
#define HRTIM1_COMMON    ((HRTIM_Common_TypeDef *)(HRTIM1_BASE + 0x0000))
#define HRTIM1_MASTER    ((HRTIM_Master_TypeDef *)(HRTIM1_BASE + 0x0020))
#define HRTIM1_TIMA       ((HRTIM_Timer_TypeDef *)(HRTIM1_BASE + 0x0080))

/* ---- FLASH ---- */
typedef struct {
    volatile uint32_t ACR;
    volatile uint32_t KEYR;
    volatile uint32_t OPTKEYR;
    volatile uint32_t SR;
    volatile uint32_t CR;
    volatile uint32_t AR;
    /* ... */
} FLASH_TypeDef;

#define FLASH_BASE       0x40022000U
#define FLASH           ((FLASH_TypeDef *)FLASH_BASE)

#define FLASH_ACR_LATENCY_5WS 5
#define FLASH_ACR_PRFTEN     (1U << 8)
#define FLASH_ACR_ICEN       (1U << 9)
#define FLASH_ACR_DCEN       (1U << 10)
#define FLASH_CR_PER    (1U << 1)
#define FLASH_CR_PG     (1U << 0)
#define FLASH_CR_STTR  (1U << 6)   /* start (simplified) */
#define FLASH_CR_STRT  (1U << 16)
#define FLASH_CR_LOCK  (1U << 31)
#define FLASH_SR_BSY   (1U << 16)

/* ---- NVIC ---- */
typedef struct {
    volatile uint32_t ISER[8];
    volatile uint32_t Reserved0[24];
    volatile uint32_t ICER[8];
    /* ... */
} NVIC_TypeDef;
#define NVIC ((NVIC_TypeDef *)0xE000E100U)

static inline void NVIC_EnableIRQ(int irq)
{
    NVIC->ISER[irq / 32] = (1U << (irq % 32));
}

static inline void NVIC_SetPriorityGrouping(int group)
{
    (void)group;
}

/* ---- SysTick ---- */
typedef struct {
    volatile uint32_t CSR;
    volatile uint32_t LOAD;
    volatile uint32_t VAL;
    volatile uint32_t CALIB;
} SysTick_TypeDef;
#define SysTick ((SysTick_TypeDef *)0xE000E010U)

/* ---- FreeRTOS port handlers (declared in main.c) ---- */
void xPortSysTickHandler(void);
void vTaskStartScheduler(void);

/* ---- Misc helpers ---- */
static inline void __WFI(void) { __asm volatile ("wfi"); }
static inline void __NOP(void) { __asm volatile ("nop"); }

#endif /* STM32G474_H */