/*
 * onewire.c — DS18B20 1-wire temperature sensor driver
 *
 * Bit-banged 1-wire protocol on a single GPIO pin (open-drain).
 */

#include "onewire.h"
#include "main.h"

/* 1-wire timing constants (microseconds) */
#define OW_RESET_LOW_US    480
#define OW_RESET_WAIT_US   70
#define OW_RESET_HIGH_US   410
#define OW_WRITE_1_LOW_US  6
#define OW_WRITE_1_HIGH_US 64
#define OW_WRITE_0_LOW_US  60
#define OW_WRITE_0_HIGH_US 10
#define OW_READ_LOW_US     6
#define OW_READ_WAIT_US    9
#define OW_READ_HIGH_US    55

/* ── Private helpers ──────────────────────────────────── */

static void delay_us(uint32_t us)
{
    /* At 170 MHz, 170 cycles per µs. Use DWT cycle counter for precision. */
    uint32_t start = DWT->CYCCNT;
    uint32_t cycles = us * (SystemCoreClock / 1000000);
    while ((DWT->CYCCNT - start) < cycles);
}

static void ow_pin_low(void)
{
    HAL_GPIO_WritePin(ONEWIRE_GPIO, ONEWIRE_PIN, GPIO_PIN_RESET);
}

static void ow_pin_high(void)
{
    HAL_GPIO_WritePin(ONEWIRE_GPIO, ONEWIRE_PIN, GPIO_PIN_SET);
}

static int ow_pin_read(void)
{
    return (HAL_GPIO_ReadPin(ONEWIRE_GPIO, ONEWIRE_PIN) == GPIO_PIN_SET) ? 1 : 0;
}

/* ── Public Functions ─────────────────────────────────── */

void ow_init(void)
{
    /* Enable DWT cycle counter for precise µs delays */
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;

    ow_pin_high();
    HAL_Delay(10);
}

int ow_reset(void)
{
    int presence;

    ow_pin_low();
    delay_us(OW_RESET_LOW_US);

    ow_pin_high();
    delay_us(OW_RESET_WAIT_US);

    presence = !ow_pin_read();  /* device pulls low if present */

    delay_us(OW_RESET_HIGH_US);

    return presence;
}

void ow_write_bit(int bit)
{
    if (bit) {
        ow_pin_low();
        delay_us(OW_WRITE_1_LOW_US);
        ow_pin_high();
        delay_us(OW_WRITE_1_HIGH_US);
    } else {
        ow_pin_low();
        delay_us(OW_WRITE_0_LOW_US);
        ow_pin_high();
        delay_us(OW_WRITE_0_HIGH_US);
    }
}

int ow_read_bit(void)
{
    int bit;

    ow_pin_low();
    delay_us(OW_READ_LOW_US);

    ow_pin_high();
    delay_us(OW_READ_WAIT_US);

    bit = ow_pin_read();

    delay_us(OW_READ_HIGH_US);

    return bit;
}

void ow_write_byte(uint8_t byte)
{
    for (int i = 0; i < 8; i++) {
        ow_write_bit(byte & 1);
        byte >>= 1;
    }
}

uint8_t ow_read_byte(void)
{
    uint8_t byte = 0;
    for (int i = 0; i < 8; i++) {
        byte >>= 1;
        if (ow_read_bit()) byte |= 0x80;
    }
    return byte;
}

int ds18b20_start_conversion(void)
{
    if (!ow_reset()) return -1;

    ow_write_byte(0xCC);  /* Skip ROM (single device) */
    ow_write_byte(0x44);  /* Convert T */

    return 0;
}

int ds18b20_read_temp(float *temp_c)
{
    if (!ow_reset()) return -1;

    ow_write_byte(0xCC);  /* Skip ROM */
    ow_write_byte(0xBE);  /* Read scratchpad */

    uint8_t data[9];
    for (int i = 0; i < 9; i++) {
        data[i] = ow_read_byte();
    }

    /* Temperature: 16-bit signed, 0.0625 °C per LSB */
    int16_t raw = (int16_t)((data[1] << 8) | data[0]);
    *temp_c = (float)raw * 0.0625f;

    return 0;
}

int ds18b20_read_temp_blocking(float *temp_c)
{
    if (ds18b20_start_conversion() != 0) return -1;

    /* Wait for conversion (750ms for 12-bit resolution) */
    HAL_Delay(750);

    return ds18b20_read_temp(temp_c);
}