/**
 * ds18b20.c — DS18B20 1-Wire temperature sensor driver
 *
 * Implements 1-Wire protocol via bit-banging on PB11.
 * The DS18B20 is bonded to the prism body for temperature measurement.
 * 12-bit resolution gives 0.0625°C precision with 750 ms conversion time.
 */

#include "ds18b20.h"
#include <string.h>

/* 1-Wire bus pin: PB11 */
#define DS18B20_PORT    GPIOB
#define DS18B20_PIN     GPIO_PIN_11

/* Timing constants (microseconds) for 1-Wire at 3.3V */
#define OW_RESET_LOW_US     480
#define OW_RESET_WAIT_US    70
#define OW_RESET_READ_US    410
#define OW_WRITE_1_LOW_US   6
#define OW_WRITE_1_WAIT_US  64
#define OW_WRITE_0_LOW_US   60
#define OW_WRITE_0_WAIT_US  10
#define OW_READ_LOW_US      6
#define OW_READ_WAIT_US     9
#define OW_READ_SAMPLE_US   55

/* ROM commands */
#define OW_CMD_SKIP_ROM     0xCC
#define OW_CMD_CONVERT_T    0x44
#define OW_CMD_READ_SCRATCH 0xBE

/* ---- Microsecond delay ---- */
static void delay_us(uint32_t us) {
    /* At 170 MHz, 170 cycles per µs. Use DWT cycle counter for precision. */
    uint32_t start = DWT->CYCCNT;
    uint32_t cycles = us * 170;
    while ((DWT->CYCCNT - start) < cycles);
}

/* ---- 1-Wire bus operations ---- */
static void ow_pin_output(void) {
    GPIO_InitTypeDef gp = {0};
    gp.Pin = DS18B20_PIN;
    gp.Mode = GPIO_MODE_OUTPUT_OD;  /* Open-drain for 1-Wire */
    gp.Pull = GPIO_NOPULL;
    gp.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(DS18B20_PORT, &gp);
}

static void ow_pin_input(void) {
    GPIO_InitTypeDef gp = {0};
    gp.Pin = DS18B20_PIN;
    gp.Mode = GPIO_MODE_INPUT;
    gp.Pull = GPIO_PULLUP;  /* External 4.7kΩ pullup also present */
    HAL_GPIO_Init(DS18B20_PORT, &gp);
}

static void ow_low(void) {
    HAL_GPIO_WritePin(DS18B20_PORT, DS18B20_PIN, GPIO_PIN_RESET);
}

static void ow_high(void) {
    HAL_GPIO_WritePin(DS18B20_PORT, DS18B20_PIN, GPIO_PIN_SET);
}

static uint8_t ow_read(void) {
    return HAL_GPIO_ReadPin(DS18B20_PORT, DS18B20_PIN);
}

/* Reset pulse + presence detect */
static uint8_t ow_reset(void) {
    uint8_t presence;

    ow_pin_output();
    ow_low();
    delay_us(OW_RESET_LOW_US);

    ow_pin_input();
    delay_us(OW_RESET_WAIT_US);

    presence = !ow_read();  /* Low = device present */
    delay_us(OW_RESET_READ_US);

    return presence;
}

/* Write one bit */
static void ow_write_bit(uint8_t bit) {
    ow_pin_output();
    ow_low();

    if (bit) {
        delay_us(OW_WRITE_1_LOW_US);
        ow_pin_input();
        delay_us(OW_WRITE_1_WAIT_US);
    } else {
        delay_us(OW_WRITE_0_LOW_US);
        ow_pin_input();
        delay_us(OW_WRITE_0_WAIT_US);
    }
}

/* Read one bit */
static uint8_t ow_read_bit(void) {
    uint8_t bit;

    ow_pin_output();
    ow_low();
    delay_us(OW_READ_LOW_US);

    ow_pin_input();
    delay_us(OW_READ_WAIT_US);

    bit = ow_read();
    delay_us(OW_READ_SAMPLE_US);

    return bit;
}

/* Write one byte (LSB first) */
static void ow_write_byte(uint8_t byte) {
    for (int i = 0; i < 8; i++) {
        ow_write_bit(byte & 0x01);
        byte >>= 1;
    }
}

/* Read one byte (LSB first) */
static uint8_t ow_read_byte(void) {
    uint8_t byte = 0;
    for (int i = 0; i < 8; i++) {
        byte >>= 1;
        if (ow_read_bit()) byte |= 0x80;
    }
    return byte;
}

/* ---- Public API ---- */

void ds18b20_init(void) {
    /* Enable DWT cycle counter for precise µs delays */
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;

    /* Configure pin as input with pullup initially */
    ow_pin_input();

    /* Check if sensor is present */
    if (ow_reset()) {
        /* Set 12-bit resolution (0.0625°C, 750ms conversion) */
        ow_write_byte(OW_CMD_SKIP_ROM);
        /* Write scratchpad: TH=0, TL=0, Config=0x7F (12-bit) */
        /* Simplified — skip for now, default is 12-bit */
    }
}

uint8_t ds18b20_is_present(void) {
    return ow_reset();
}

float ds18b20_read_temperature(void) {
    if (!ow_reset()) return -1000.0f;

    /* Start temperature conversion */
    ow_write_byte(OW_CMD_SKIP_ROM);
    ow_write_byte(OW_CMD_CONVERT_T);

    /* Wait for conversion (750ms for 12-bit) */
    HAL_Delay(750);

    /* Read scratchpad */
    if (!ow_reset()) return -1000.0f;
    ow_write_byte(OW_CMD_SKIP_ROM);
    ow_write_byte(OW_CMD_READ_SCRATCH);

    /* Read 9 bytes (2 temp + 3 config + 4 reserved) */
    uint8_t scratch[9];
    for (int i = 0; i < 9; i++) {
        scratch[i] = ow_read_byte();
    }

    /* Temperature: 16-bit signed, LSB first, in 0.0625°C units */
    int16_t raw = (int16_t)((scratch[1] << 8) | scratch[0]);
    float temp = (float)raw * 0.0625f;

    return temp;
}