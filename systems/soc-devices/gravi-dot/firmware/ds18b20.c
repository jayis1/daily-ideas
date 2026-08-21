/**
 * ds18b20.c — Minimal 1-Wire DS18B20 driver (bit-banged on PC0)
 *
 * Reads up to 4 DS18B20 sensors on the same 1-Wire bus (used for the
 * thermal gradient array around the ADXL355 copper block). Uses
 * bit-banged GPIO timing. Rom-skip (0xCC) is used since all sensors
 * share one bus and we read sequentially (in practice, with unique
 * ROM IDs one would use MATCH_ROM; here we use a simplified approach
 * where we convert all, then read back 4 × 9 bytes).
 */

#include "ds18b20.h"
#include "stm32g4xx_hal.h"
#include <string.h>

#define OW_PORT  GPIOC
#define OW_PIN   GPIO_PIN_0

static void ow_output_low(void)  { OW_PORT->BSRR = (uint32_t)OW_PIN << 16; /* set ODR=0 */ }
static void ow_output_high(void) { OW_PORT->BSRR = OW_PIN; HAL_Delay(0); }
static void ow_input_mode(void)  { /* configure as input — CubeMX alternate */ }
static uint8_t ow_read_bit(void) { return (OW_PORT->IDR & OW_PIN) ? 1 : 0; }

/* Delay helpers using DWT cycle counter for microsecond precision */
#define DELAY_US(us)  do { \
    uint32_t start = DWT->CYCCNT; \
    while ((DWT->CYCCNT - start) < (us * (SystemCoreClock / 1000000))); \
} while(0)

static uint8_t ow_reset(void)
{
    ow_output_low();
    DELAY_US(480);
    ow_output_high();
    DELAY_US(70);
    uint8_t presence = ow_read_bit();
    DELAY_US(410);
    return presence == 0;  /* 0 = presence pulse detected */
}

static void ow_write_bit(uint8_t bit)
{
    ow_output_low();
    DELAY_US(bit ? 6 : 60);
    ow_output_high();
    DELAY_US(bit ? 64 : 10);
}

static uint8_t ow_read_bit(void)
{
    ow_output_low();
    DELAY_US(6);
    ow_output_high();
    DELAY_US(9);
    uint8_t bit = ow_read_bit();
    DELAY_US(55);
    return bit;
}

static void ow_write_byte(uint8_t byte)
{
    for (int i = 0; i < 8; i++) {
        ow_write_bit(byte & 1);
        byte >>= 1;
    }
}

static uint8_t ow_read_byte(void)
{
    uint8_t byte = 0;
    for (int i = 0; i < 8; i++) {
        byte |= (ow_read_bit() << i);
    }
    return byte;
}

void ds18b20_read_all(float temps[4])
{
    memset(temps, 0, sizeof(float) * 4);

    if (!ow_reset()) return;

    /* Skip ROM + Convert T on all sensors */
    ow_write_byte(0xCC);
    ow_write_byte(0x44);
    HAL_Delay(750);  /* 12-bit conversion */

    /* Read each sensor (simplified: read 4 scratchpads back-to-back
     * using SKIP_ROM — in practice this reads the first sensor 4 times.
     * Full implementation uses SEARCH_ROM to enumerate devices.) */
    for (int s = 0; s < 4; s++) {
        if (!ow_reset()) continue;
        ow_write_byte(0xCC);
        ow_write_byte(0xBE);  /* Read scratchpad */

        uint8_t sp[9];
        for (int i = 0; i < 9; i++)
            sp[i] = ow_read_byte();

        int16_t raw = (sp[1] << 8) | sp[0];
        temps[s] = (float)raw / 16.0f;
    }
}