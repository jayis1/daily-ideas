/*
 * stm32g474_conf.h — STM32G474RET6 HAL/bare-metal configuration
 *
 * Device defines, clock constants, peripheral base addresses, and
 * register-level helpers used across all firmware modules.
 */

#ifndef STM32G474_CONF_H
#define STM32G474_CONF_H

#include <stdint.h>
#include <stdbool.h>
#include <math.h>

/* ---- Device constants ---- */
#define SYSCLK_FREQ     170000000u
#define SYSTICK_HZ      1000u

/* PLL config: HSI 16 MHz → PLL(PLLM=4, PLLN=85, PLLP=2) → 170 MHz */
#define PLLM_VALUE      4u
#define PLLN_VALUE      85u
#define PLLP_VALUE      2u

/* ---- CMSIS register access ---- */
/* The full STM32G474 CMSIS header is large; in the real build
   #include <stm32g474xx.h> from STM32CubeMX CMSIS. For this
   standalone source we use the standard register addresses. */

/* RCC */
#define RCC_CR                 (*((volatile uint32_t *)0x40021000))
#define RCC_CR_HSION           (1u << 8)
#define RCC_CR_HSIRDY          (1u << 10)
#define RCC_CR_PLLON           (1u << 24)
#define RCC_CR_PLLRDY          (1u << 25)

#define RCC_CFGR               (*((volatile uint32_t *)0x40021008))
#define RCC_CFGR_SW            (0x3u << 0)
#define RCC_CFGR_SWS           (0x3u << 2)
#define RCC_CFGR_SWS_PLL       (0x3u << 2)

#define RCC_PLLCFGR            (*((volatile uint32_t *)0x4002100C))
#define RCC_PLLCFGR_PLLM_Pos   4u
#define RCC_PLLCFGR_PLLN_Pos   8u
#define RCC_PLLCFGR_PLLP_Pos   17u
#define RCC_PLLCFGR_PLLREN     (1u << 24)

#define RCC_AHB1ENR            (*((volatile uint32_t *)0x40021038))
#define RCC_AHB1ENR_DMA1EN     (1u << 0)

#define RCC_AHB2ENR            (*((volatile uint32_t *)0x4002103C))
#define RCC_AHB2ENR_GPIOAEN    (1u << 0)
#define RCC_AHB2ENR_GPIOBEN    (1u << 1)
#define RCC_AHB2ENR_GPIOCEN    (1u << 2)
#define RCC_AHB2ENR_GPIODEN    (1u << 3)
#define RCC_AHB2ENR_ADC12EN    (1u << 13)

#define RCC_APB1ENR1           (*((volatile uint32_t *)0x40021040))
#define RCC_APB1ENR1_TIM2EN    (1u << 0)
#define RCC_APB1ENR1_TIM3EN    (1u << 1)
#define RCC_APB1ENR1_I2C1EN    (1u << 21)
#define RCC_APB1ENR1_I2C3EN    (1u << 23)
#define RCC_APB1ENR1_SPI2EN    (1u << 14)

#define RCC_APB2ENR            (*((volatile uint32_t *)0x4002104C))
#define RCC_APB2ENR_USART1EN   (1u << 14)
#define RCC_APB2ENR_ADC1EN     (1u << 16)  /* note: same as ADC12EN on AHB2 */

/* FLASH */
#define FLASH_ACR             (*((volatile uint32_t *)0x40022000))
#define FLASH_ACR_ICEN         (1u << 9)
#define FLASH_ACR_DCEN         (1u << 10)
#define FLASH_ACR_PRFTEN       (1u << 8)
#define FLASH_ACR_LATENCY_2WS  (2u << 0)

/* ---- GPIO helpers ---- */
#define GPIO_MODER_OFFSET      0x00
#define GPIO_OTYPER_OFFSET     0x04
#define GPIO_PUPDR_OFFSET      0x0C
#define GPIO_IDR_OFFSET        0x10
#define GPIO_BSRR_OFFSET       0x18
#define GPIO_AFR_OFFSET        0x20

#define GPIO_MODER(gpio, n, mode) \
    do { (gpio)->MODER = ((gpio)->MODER & ~(3u << (2*(n)))) | ((mode) << (2*(n))); } while(0)

/* GPIOA base = 0x48000000, GPIOB = 0x48000400, etc. (G4 family) */
#define GPIOA  ((volatile uint32_t *)0x48000000u)
#define GPIOB  ((volatile uint32_t *)0x48000400u)
#define GPIOC  ((volatile uint32_t *)0x48000800u)
#define GPIOD  ((volatile uint32_t *)0x48000C00u)

/* Simplified: define GPIO as structs */
typedef struct {
    volatile uint32_t MODER;
    volatile uint32_t OTYPER;
    volatile uint32_t OSPEEDR;
    volatile uint32_t PUPDR;
    volatile uint32_t IDR;
    volatile uint32_t ODR;
    volatile uint32_t BSRR;
    volatile uint32_t LCKR;
    volatile uint32_t AFRL;
    volatile uint32_t AFRH;
} GPIO_TypeDef;

/* Redefine GPIO bases correctly for G4 */
#undef GPIOA
#undef GPIOB
#undef GPIOC
#undef GPIOD
#define GPIOA   ((GPIO_TypeDef *)0x48000000u)
#define GPIOB   ((GPIO_TypeDef *)0x48000400u)
#define GPIOC   ((GPIO_TypeDef *)0x48000800u)
#define GPIOD   ((GPIO_TypeDef *)0x48000C00u)

/* GPIO bit helpers */
#define GPIO_MODER_MODE0      (3u << 0)
#define GPIO_MODER_MODE4       (3u << 8)
#define GPIO_MODER_MODE8       (3u << 16)
#define GPIO_MODER_MODE9       (3u << 18)
#define GPIO_MODER_MODE10      (3u << 20)
#define GPIO_MODER_MODE11      (3u << 22)
#define GPIO_MODER_MODE12      (3u << 24)
#define GPIO_MODER_MODE13      (3u << 26)
#define GPIO_MODER_MODE14      (3u << 28)
#define GPIO_MODER_MODE15      (3u << 30)

#define GPIO_PUPDR_PUPD5       (3u << 10)
#define GPIO_PUPDR_PUPD6       (3u << 12)
#define GPIO_PUPDR_PUPD7       (3u << 14)
#define GPIO_PUPDR_PUPD8       (3u << 16)
#define GPIO_PUPDR_PUPD9       (3u << 18)
#define GPIO_PUPDR_PUPD11      (3u << 22)
#define GPIO_PUPDR_PUPD12      (3u << 24)

#define GPIO_OTYPER_OT8        (1u << 8)
#define GPIO_OTYPER_OT9        (1u << 9)
#define GPIO_OTYPER_OT11        (1u << 11)
#define GPIO_OTYPER_OT12       (1u << 12)

#define GPIO_IDR_ID8           (1u << 8)
#define GPIO_IDR_ID12          (1u << 12)

#define GPIO_BSRR_BS12         (1u << 12)

#define GPIO_AFRL_AFSEL0       (0xFu << 0)
#define GPIO_AFRL_AFSEL4       (0xFu << 16)
#define GPIO_AFRH_AFSEL8       (0xFu << 0)
#define GPIO_AFRH_AFSEL9       (0xFu << 4)
#define GPIO_AFRH_AFSEL10      (0xFu << 8)
#define GPIO_AFRH_AFSEL11      (0xFu << 12)
#define GPIO_AFRH_AFSEL12      (0xFu << 16)
#define GPIO_AFRH_AFSEL13      (0xFu << 20)
#define GPIO_AFRH_AFSEL14      (0xFu << 24)
#define GPIO_AFRH_AFSEL15      (0xFu << 28)

#define GPIO_AFRL_AFSEL4_Pos   16u
#define GPIO_AFRL_AFSEL0_Pos   0u
#define GPIO_AFRH_AFSEL8_Pos   0u
#define GPIO_AFRH_AFSEL9_Pos   4u
#define GPIO_AFRH_AFSEL10_Pos  8u
#define GPIO_AFRH_AFSEL11_Pos  12u
#define GPIO_AFRH_AFSEL12_Pos  16u
#define GPIO_AFRH_AFSEL13_Pos  20u
#define GPIO_AFRH_AFSEL14_Pos  24u
#define GPIO_AFRH_AFSEL15_Pos  28u

#define GPIO_MODER_MODE4_Pos   8u
#define GPIO_MODER_MODE8_Pos   16u
#define GPIO_MODER_MODE9_Pos   18u
#define GPIO_MODER_MODE10_Pos  20u
#define GPIO_MODER_MODE11_Pos  22u
#define GPIO_MODER_MODE12_Pos  24u
#define GPIO_MODER_MODE13_Pos  26u
#define GPIO_MODER_MODE14_Pos  28u
#define GPIO_MODER_MODE15_Pos  30u

#define GPIO_PUPDR_PUPD5_Pos   10u
#define GPIO_PUPDR_PUPD6_Pos   12u
#define GPIO_PUPDR_PUPD7_Pos   14u
#define GPIO_PUPDR_PUPD8_Pos   16u
#define GPIO_PUPDR_PUPD9_Pos   18u
#define GPIO_PUPDR_PUPD11_Pos  22u
#define GPIO_PUPDR_PUPD12_Pos  24u

/* ---- SysTick ---- */
#define SysTick   (*((volatile uint32_t *)0xE000E010u))
#define SysTick_LOAD  (*((volatile uint32_t *)0xE000E014u))
#define SysTick_VAL   (*((volatile uint32_t *)0xE000E018u))
#define SysTick_CTRL  (*((volatile uint32_t *)0xE000E010u))
#define SysTick_CTRL_CLKSOURCE_Msk  (1u << 2)
#define SysTick_CTRL_ENABLE_Msk    (1u << 0)
#define SysTick_CTRL_TICKINT_Msk   (1u << 1)

/* ---- DMA1 ---- */
#define DMA1        ((volatile uint32_t *)0x40020000u)
#define DMA1_ISR    (*((volatile uint32_t *)0x40020004u))
#define DMA1_IFCR   (*((volatile uint32_t *)0x40020008u))
#define DMA1_Channel1  ((volatile struct DMA_Channel_t *)0x40020010u)

typedef struct {
    volatile uint32_t CCR;
    volatile uint32_t CNDTR;
    volatile uint32_t CPAR;
    volatile uint32_t CMAR;
    volatile uint32_t RESERVED;
} DMA_Channel_t;

#define DMA1_Channel1_IRQn  11

#define DMA_CCR_MINC    (1u << 7)
#define DMA_CCR_CIRC    (1u << 8)
#define DMA_CCR_PSIZE_0 (1u << 9)
#define DMA_CCR_MSIZE_0 (1u << 11)
#define DMA_CCR_HTIE    (1u << 3)
#define DMA_CCR_TCIE    (1u << 4)
#define DMA_CCR_EN      (1u << 0)
#define DMA_ISR_HTIF1   (1u << 1)
#define DMA_ISR_TCIF1   (1u << 2)
#define DMA_IFCR_CHTIF1 (1u << 1)
#define DMA_IFCR_CTCIF1 (1u << 2)

/* ---- ADC1 / ADC2 ---- */
#define ADC1  ((volatile struct ADC_t *)0x50000000u)
#define ADC2  ((volatile struct ADC_t *)0x50000100u)

typedef struct {
    volatile uint32_t CR;
    volatile uint32_t CFGR;
    volatile uint32_t CFGR2;
    volatile uint32_t SMPR1;
    volatile uint32_t SMPR2;
    volatile uint32_t RESERVED0[2];
    volatile uint32_t TR1;
    volatile uint32_t TR2;
    volatile uint32_t TR3;
    volatile uint32_t RESERVED1;
    volatile uint32_t SQR1;
    volatile uint32_t SQR2;
    volatile uint32_t SQR3;
    volatile uint32_t SQR4;
    volatile uint32_t DR;
    volatile uint32_t RESERVED2[2];
    volatile uint32_t ISR;
    volatile uint32_t IER;
    volatile uint32_t RESERVED3[2];
    volatile uint32_t AWD2CR;
    volatile uint32_t AWD3CR;
    volatile uint32_t RESERVED4;
    volatile uint32_t OFR1;
    volatile uint32_t OFR2;
    volatile uint32_t OFR3;
    volatile uint32_t OFR4;
} ADC_t;

#define ADC_CR_ADVREGEN  (1u << 28)
#define ADC_CR_DEEPPWD   (1u << 29)
#define ADC_CR_ADCAL     (1u << 24)
#define ADC_CR_ADEN      (1u << 0)
#define ADC_CR_ADSTART   (1u << 2)
#define ADC_CR_ADSTP     (1u << 4)
#define ADC_ISR_ADRDY    (1u << 0)
#define ADC_ISR_EOC      (1u << 2)
#define ADC_ISR_TXIS     (1u << 4)   /* not used; for I2C */
#define ADC_CFGR_CONT    (1u << 2)
#define ADC_CFGR_DMAEN   (1u << 0)
#define ADC_CFGR_DMACFG  (1u << 1)
#define ADC_SMPR1_SMP1_Pos 3u
#define ADC_SQR1_SQ1_Pos 6u

/* ---- USART1 ---- */
#define USART1 ((volatile struct USART_t *)0x40013800u)

typedef struct {
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    volatile uint32_t CR3;
    volatile uint32_t BRR;
    volatile uint32_t RESERVED;
    volatile uint32_t RDR;
    volatile uint32_t TDR;
    volatile uint32_t RESERVED2[2];
    volatile uint32_t ISR;
    volatile uint32_t ICR;
} USART_t;

#define USART_CR1_UE      (1u << 0)
#define USART_CR1_TE      (1u << 3)
#define USART_CR1_RE      (1u << 2)
#define USART_CR1_RXNEIE  (1u << 5)
#define USART_ISR_TXE     (1u << 7)
#define USART_ISR_RXNE    (1u << 5)
#define USART_ISR_TC      (1u << 6)

/* ---- I2C ---- */
#define I2C1 ((volatile struct I2C_t *)0x40005400u)
#define I2C3 ((volatile struct I2C_t *)0x40007800u)

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
} I2C_t;

#define I2C_CR1_PE         (1u << 0)
#define I2C_CR2_START      (1u << 13)
#define I2C_CR2_STOP       (1u << 14)
#define I2C_CR2_RD_WRN     (1u << 10)
#define I2C_CR2_AUTOEND    (1u << 20)
#define I2C_CR2_NBYTES_Pos 16u
#define I2C_ISR_TXIS       (1u << 1)
#define I2C_ISR_RXNE       (1u << 2)
#define I2C_ISR_TC         (1u << 6)
#define I2C_ISR_NACKF      (1u << 4)
#define I2C_ICR_NACKCF     (1u << 4)

/* ---- TIM2 / TIM3 ---- */
#define TIM2 ((volatile struct TIM_t *)0x40000000u)
#define TIM3 ((volatile struct TIM_t *)0x40000400u)

typedef struct {
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    volatile uint32_t SMCR;
    volatile uint32_t DIER;
    volatile uint32_t SR;
    volatile uint32_t EGR;
    volatile uint32_t RESERVED0;
    volatile uint32_t CCMR1;
    volatile uint32_t CCMR2;
    volatile uint32_t CCER;
    volatile uint32_t CNT;
    volatile uint32_t PSC;
    volatile uint32_t ARR;
    volatile uint32_t RESERVED1;
    volatile uint32_t CCR1;
    volatile uint32_t CCR2;
    volatile uint32_t CCR3;
    volatile uint32_t CCR4;
    volatile uint32_t BDTR;
} TIM_t;

#define TIM_CR1_CEN        (1u << 0)
#define TIM_CCMR1_OC1M_PWM1 (6u << 4)
#define TIM_CCMR1_OC1PE     (1u << 3)
#define TIM_CCMR2_OC3M_PWM1 (6u << 4)
#define TIM_CCMR2_OC3PE     (1u << 3)
#define TIM_CCER_CC1E       (1u << 0)
#define TIM_CCER_CC3E       (1u << 8)
#define TIM_BDTR_MOE        (1u << 15)

/* ---- SPI2 ---- */
#define SPI2 ((volatile struct SPI_t *)0x40003800u)

typedef struct {
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    volatile uint32_t RESERVED;
    volatile uint32_t SR;
    volatile uint32_t DR;
    volatile uint32_t CRCPR;
} SPI_t;

#define SPI_CR1_MSTR  (1u << 2)
#define SPI_CR1_BR_0  (1u << 3)
#define SPI_CR1_BR_1  (1u << 4)
#define SPI_CR1_SSM   (1u << 9)
#define SPI_CR1_SSI   (1u << 8)
#define SPI_CR1_SPE   (1u << 6)
#define SPI_SR_RXNE   (1u << 0)
#define SPI_SR_TXE    (1u << 1)

/* ---- NVIC ---- */
#define NVIC_EnableIRQ(irqn) (*((volatile uint32_t *)0xE000E100u + (irqn/32)) |= (1u << (irqn%32)))

/* ---- Flash ---- */
#define RCC_AHB2ENR_ADC12EN_Pos  13u

#endif /* STM32G474_CONF_H */