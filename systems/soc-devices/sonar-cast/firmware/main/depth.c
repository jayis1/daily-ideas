/*
 * sonar-cast / firmware / depth.c
 * MS5837-30BA pressure depth + DS18B20 water temperature + speed-of-sound.
 */
#include "main.h"
#include <math.h>

#define MS5837_ADDR   0x76
#define DS18B20_PIN   6   /* PB6 */

/* Mackenzie (1981) speed of sound in fresh water, simplified (salinity=0):
   c = 1448.96 + 4.591 T − 0.05304 T² + 0.0002964 T³    [m/s, T in °C] */
static float sound_speed_from_temp(float t_c)
{
    return 1448.96f + 4.591f * t_c - 0.05304f * t_c * t_c
           + 0.0002964f * t_c * t_c * t_c;
}

static void ms5837_read_raw(uint32_t *p_raw, uint32_t *t_raw)
{
    (void)p_raw; (void)t_raw;
    /* In real HW:
       1. Send 0x40 (D1 pressure conversion), wait 10 ms
       2. Send 0x00 (ADC read) → 24-bit D1
       3. Send 0x50 (D2 temp conversion), wait 10 ms
       4. Send 0x00 → 24-bit D2
       5. Apply MS5837 factory calibration C1..C6 → compensated P (mbar), T (°C)
    */
    *p_raw = 101300;   /* placeholder: 1 atm */
    *t_raw = 0;
}

static void ds18b20_read(float *t_c)
{
    (void)t_c;
    /* 1-Wire reset + ROM match + Convert T (0x44), wait 750 ms,
       read scratchpad (0xBE) → 2-byte temp, /16.0.  Placeholder: */
    *t_c = 20.0f;
}

void depth_init(void)
{
    /* MS5837: send 0x1E reset command.
       DS18B20: 1-Wire GPIO init on PB6. */
}

void depth_read(float *temp_c, float *pressure_m, float *sound_speed)
{
    /* Temperature from DS18B20 (on transducer face, wetted) */
    ds18b20_read(temp_c);

    /* Pressure from MS5837-30BA → depth in meters.
       depth = (P_abs − P_atm) / (ρ·g),  ρ≈1000, g=9.81 → ~0.0102 m/mbar */
    uint32_t p_raw, t_raw;
    ms5837_read_raw(&p_raw, &t_raw);
    float p_mbar = 1013.0f;   /* placeholder */
    *pressure_m = (p_mbar - 1013.0f) * 0.0102f;
    if (*pressure_m < 0) *pressure_m = 0;

    /* Speed of sound (temp-corrected, fresh water default) */
    *sound_speed = sound_speed_from_temp(*temp_c);
}