/*
 * Hive Mind — DS18B20 1-Wire Temperature Chain Driver
 * 3 probes on single bus: floor, mid, crown
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "temp_chain.h"
#include "main.h"

/* 1-Wire commands */
#define OW_SEARCH_ROM       0xF0
#define OW_READ_ROM         0x33
#define OW_MATCH_ROM        0x55
#define OW_SKIP_ROM         0xCC
#define OW_CONVERT_T         0x44
#define OW_READ_SCRATCHPAD  0xBE

/* DS18B20 scratchpad layout */
#define SCRATCHPAD_LEN  9

/* Maximum number of probes on the bus */
#define MAX_PROBES  3

/* ROM IDs for the 3 probes (discovered at init) */
static uint8_t probe_roms[MAX_PROBES][8];
static uint8_t num_probes = 0;

/* Probe mapping: which ROM ID corresponds to floor/mid/crown */
static int8_t map_floor = -1;
static int8_t map_mid = -1;
static int8_t map_crown = -1;

/* 1-Wire timing (in microseconds) for standard speed */
#define OW_RESET_PULSE     480
#define OW_PRESENCE_WAIT   70
#define OW_SLOT            60
#define OW_RECOVERY        1
#define OW_READ_DELAY      10

extern GPIO_TypeDef *ONEWIRE_PORT;
extern uint16_t ONEWIRE_PIN;

/* ------------------------------------------------------------------ */
/* 1-Wire bit-level operations                                          */
/* ------------------------------------------------------------------ */

static void ow_pin_output(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin = ONEWIRE_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_OD;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(ONEWIRE_PORT, &GPIO_InitStruct);
}

static void ow_pin_input(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin = ONEWIRE_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(ONEWIRE_PORT, &GPIO_InitStruct);
}

static void ow_write_low(void)
{
    HAL_GPIO_WritePin(ONEWIRE_PORT, ONEWIRE_PIN, GPIO_PIN_RESET);
}

static void ow_write_high(void)
{
    HAL_GPIO_WritePin(ONEWIRE_PORT, ONEWIRE_PIN, GPIO_PIN_SET);
}

static uint8_t ow_read_bit(void)
{
    return HAL_GPIO_ReadPin(ONEWIRE_PORT, ONEWIRE_PIN) == GPIO_PIN_SET ? 1 : 0;
}

/* Microsecond delay using DWT cycle counter */
static void delay_us(uint32_t us)
{
    uint32_t start = DWT->CYCCNT;
    uint32_t cycles = us * (SystemCoreClock / 1000000);
    while ((DWT->CYCCNT - start) < cycles);
}

/* ------------------------------------------------------------------ */
/* 1-Wire protocol                                                      */
/* ------------------------------------------------------------------ */

static uint8_t ow_reset(void)
{
    uint8_t presence;

    ow_pin_output();
    ow_write_low();
    delay_us(OW_RESET_PULSE);

    ow_write_high();
    delay_us(OW_PRESENCE_WAIT);

    ow_pin_input();
    presence = !ow_read_bit();  /* Presence = bus low */
    delay_us(OW_RESET_PULSE - OW_PRESENCE_WAIT);

    ow_pin_output();
    ow_write_high();

    return presence;
}

static void ow_write_bit(uint8_t bit)
{
    ow_pin_output();
    ow_write_low();

    if (bit) {
        delay_us(6);
        ow_write_high();
        delay_us(OW_SLOT - 6);
    } else {
        delay_us(OW_SLOT);
        ow_write_high();
    }
    delay_us(OW_RECOVERY);
}

static uint8_t ow_read_bit_val(void)
{
    uint8_t bit;

    ow_pin_output();
    ow_write_low();
    delay_us(6);

    ow_pin_input();
    delay_us(OW_READ_DELAY);

    bit = ow_read_bit();
    delay_us(OW_SLOT - OW_READ_DELAY);

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
        byte >>= 1;
        if (ow_read_bit_val()) {
            byte |= 0x80;
        }
    }
    return byte;
}

/* ------------------------------------------------------------------ */
/* DS18B20 operations                                                   */
/* ------------------------------------------------------------------ */

static uint8_t crc8(const uint8_t *data, uint8_t len)
{
    uint8_t crc = 0;
    for (uint8_t i = 0; i < len; i++) {
        uint8_t byte = data[i];
        for (uint8_t j = 0; j < 8; j++) {
            uint8_t mix = (crc ^ byte) & 0x01;
            crc >>= 1;
            if (mix) crc ^= 0x8C;
            byte >>= 1;
        }
    }
    return crc;
}

/* ROM search: discover all DS18B20 devices on the bus */
static uint8_t ow_search(uint8_t *rom, uint8_t last_discrepancy)
{
    uint8_t id_bit, cmp_id_bit;
    uint8_t rom_byte_number = 0;
    uint8_t rom_byte_mask = 1;
    uint8_t search_direction = 0;
    uint8_t last_zero = 0;

    if (!ow_reset()) return 0xFF;  /* No devices */

    ow_write_byte(OW_SEARCH_ROM);

    do {
        id_bit = ow_read_bit_val();
        cmp_id_bit = ow_read_bit_val();

        if (id_bit && cmp_id_bit) {
            return 0xFF;  /* No device responded */
        }

        if (!id_bit && !cmp_id_bit) {
            /* Discrepancy: 0 and 1 both present */
            if (last_discrepancy > ((rom_byte_number * 8) + rom_byte_mask)) {
                search_direction = (rom[rom_byte_number] & rom_byte_mask) ? 1 : 0;
            } else {
                search_direction = (last_discrepancy == ((rom_byte_number * 8) + rom_byte_mask)) ? 1 : 0;
            }
        } else {
            search_direction = id_bit;
        }

        if (search_direction) {
            rom[rom_byte_number] |= rom_byte_mask;
        } else {
            rom[rom_byte_number] &= ~rom_byte_mask;
        }

        ow_write_bit(search_direction);

        if (!search_direction) last_zero = (rom_byte_number * 8) + rom_byte_mask;

        rom_byte_mask <<= 1;
        if (!rom_byte_mask) {
            rom_byte_number++;
            rom_byte_mask = 1;
        }
    } while (rom_byte_number < 8);

    last_discrepancy = last_zero;
    return last_discrepancy;
}

static void ds18b20_start_conversion(const uint8_t *rom)
{
    ow_reset();
    ow_write_byte(OW_MATCH_ROM);
    for (int i = 0; i < 8; i++) {
        ow_write_byte(rom[i]);
    }
    ow_write_byte(OW_CONVERT_T);
    /* No parasite power — external VDD, no need to hold bus high */
}

static float ds18b20_read_temperature(const uint8_t *rom)
{
    uint8_t scratchpad[SCRATCHPAD_LEN];

    ow_reset();
    ow_write_byte(OW_MATCH_ROM);
    for (int i = 0; i < 8; i++) {
        ow_write_byte(rom[i]);
    }
    ow_write_byte(OW_READ_SCRATCHPAD);

    for (int i = 0; i < SCRATCHPAD_LEN; i++) {
        scratchpad[i] = ow_read_byte();
    }

    /* CRC check */
    if (crc8(scratchpad, 8) != scratchpad[8]) {
        return -999.0f;  /* CRC error */
    }

    int16_t raw = (scratchpad[1] << 8) | scratchpad[0];
    /* DS18B20 default: 12-bit resolution, 0.0625 °C LSB */
    return (float)raw * 0.0625f;
}

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

void temp_chain_init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* Configure 1-Wire pin as open-drain output with pullup */
    GPIO_InitStruct.Pin = ONEWIRE_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_OD;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(ONEWIRE_PORT, &GPIO_InitStruct);

    /* Enable DWT for microsecond delays */
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;

    /* Discover probes on the bus */
    num_probes = 0;
    uint8_t last_disc = 0;

    for (int i = 0; i < MAX_PROBES; i++) {
        uint8_t rom[8] = {0};
        last_disc = ow_search(rom, last_disc);
        if (last_disc == 0xFF) break;

        /* Verify CRC of ROM */
        if (crc8(rom, 7) != rom[7]) continue;

        /* Check family code (0x28 = DS18B20) */
        if (rom[0] != 0x28) continue;

        memcpy(probe_roms[num_probes], rom, 8);
        num_probes++;

        if (last_disc == 0) break;
    }

    /* Auto-assign: probe 0 = floor, probe 1 = mid, probe 2 = crown */
    for (uint8_t i = 0; i < num_probes && i < 3; i++) {
        switch (i) {
            case 0: map_floor = i; break;
            case 1: map_mid = i; break;
            case 2: map_crown = i; break;
        }
    }
}

void temp_chain_read_all(float temps[3])
{
    /* Start conversion on all probes simultaneously */
    ow_reset();
    ow_write_byte(OW_SKIP_ROM);
    ow_write_byte(OW_CONVERT_T);

    /* Wait for 12-bit conversion: 750 ms max */
    HAL_Delay(750);

    /* Read each probe */
    temps[0] = (map_floor >= 0) ? ds18b20_read_temperature(probe_roms[map_floor]) : -999.0f;
    temps[1] = (map_mid >= 0) ? ds18b20_read_temperature(probe_roms[map_mid]) : -999.0f;
    temps[2] = (map_crown >= 0) ? ds18b20_read_temperature(probe_roms[map_crown]) : -999.0f;
}

uint8_t temp_chain_get_num_probes(void)
{
    return num_probes;
}

void temp_chain_get_rom_id(uint8_t index, uint8_t rom[8])
{
    if (index < num_probes) {
        memcpy(rom, probe_roms[index], 8);
    }
}

void temp_chain_assign(uint8_t index, probe_location_t location)
{
    switch (location) {
        case PROBE_FLOOR:  map_floor = index; break;
        case PROBE_MID:    map_mid = index; break;
        case PROBE_CROWN:  map_crown = index; break;
    }
}