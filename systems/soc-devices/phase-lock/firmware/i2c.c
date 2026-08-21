/*
 * i2c.c — minimal bit-banged I2C driver (PA11=SDA, PA12=SCL)
 *
 * Bit-banged at ~100 kHz (good enough for SH1106 + ADS1115).
 * Hardware I2C1 could be used instead; this avoids HAL dependencies.
 */

#include "stm32g491_conf.h"
#include "i2c.h"

#define SDA_PORT GPIOA
#define SCL_PORT GPIOA
#define SDA_PIN  11
#define SCL_PIN  12

#define SDA_HI()  (SDA_PORT->BSRR = (1U << SDA_PIN))
#define SDA_LO()  (SDA_PORT->BSRR = (1U << (SDA_PIN + 16)))
#define SCL_HI()  (SCL_PORT->BSRR = (1U << SCL_PIN))
#define SCL_LO()  (SCL_PORT->BSRR = (1U << (SCL_PIN + 16)))
#define SDA_READ() ((SDA_PORT->IDR >> SDA_PIN) & 1U)

static void delay_us(uint32_t us)
{
    for (volatile uint32_t i = 0; i < us * 8; ++i) ;
}

static void sda_mode_out(void)
{
    SDA_PORT->MODER = (SDA_PORT->MODER & ~(0x3U << (2*SDA_PIN)))
                    |  (0x1U << (2*SDA_PIN));
    SDA_PORT->OTYPER |= (1U << SDA_PIN);   /* open-drain */
    SDA_PORT->PUPDR  |= (0x1U << (2*SDA_PIN));  /* pull-up */
}
static void sda_mode_in(void)
{
    SDA_PORT->MODER &= ~(0x3U << (2*SDA_PIN));
    SDA_PORT->PUPDR |= (0x1U << (2*SDA_PIN));
}

void i2c_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    sda_mode_out();
    SCL_PORT->MODER = (SCL_PORT->MODER & ~(0x3U << (2*SCL_PIN)))
                    |  (0x1U << (2*SCL_PIN));
    SCL_PORT->OTYPER |= (1U << SCL_PIN);
    SCL_PORT->PUPDR  |= (0x1U << (2*SCL_PIN));
    SDA_HI(); SCL_HI();
    delay_us(10);
}

static void i2c_start(void)
{
    SDA_HI(); SCL_HI(); delay_us(5);
    SDA_LO();          delay_us(5);
    SCL_LO();          delay_us(5);
}
static void i2c_stop(void)
{
    SDA_LO(); SCL_HI(); delay_us(5);
    SDA_HI();          delay_us(5);
}
static int i2c_write_byte(uint8_t b)
{
    sda_mode_out();
    for (int i = 7; i >= 0; --i) {
        if ((b >> i) & 1) SDA_HI(); else SDA_LO();
        SCL_HI(); delay_us(5);
        SCL_LO(); delay_us(5);
    }
    sda_mode_in();
    SDA_HI(); SCL_HI(); delay_us(5);
    int ack = !SDA_READ();
    SCL_LO();
    return ack;
}
static uint8_t i2c_read_byte(int ack)
{
    uint8_t b = 0;
    sda_mode_in();
    SDA_HI();
    for (int i = 7; i >= 0; --i) {
        SCL_HI(); delay_us(5);
        if (SDA_READ()) b |= (1U << i);
        SCL_LO(); delay_us(5);
    }
    sda_mode_out();
    if (ack) SDA_LO(); else SDA_HI();
    SCL_HI(); delay_us(5);
    SCL_LO(); delay_us(5);
    return b;
}

int i2c_write(uint8_t addr, const uint8_t *data, size_t len)
{
    i2c_start();
    if (!i2c_write_byte(addr << 1)) { i2c_stop(); return -1; }
    for (size_t i = 0; i < len; ++i)
        if (!i2c_write_byte(data[i])) { i2c_stop(); return -1; }
    i2c_stop();
    return 0;
}

int i2c_read(uint8_t addr, uint8_t *data, size_t len)
{
    i2c_start();
    if (!i2c_write_byte((addr << 1) | 1)) { i2c_stop(); return -1; }
    for (size_t i = 0; i < len; ++i)
        data[i] = i2c_read_byte(i < len - 1);
    i2c_stop();
    return 0;
}