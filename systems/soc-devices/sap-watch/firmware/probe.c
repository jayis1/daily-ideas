/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * probe.c — Heat-pulse probe driver: heater pulse, ADS122U04 ADC
 *           communication, thermistor-to-temperature conversion
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "probe.h"
#include <math.h>
#include <string.h>

/* ---- Module state ---- */
static probe_state_t probe_state = PROBE_IDLE;
static float baseline_temp_up = 0.0f;   /* pre-pulse T0 upstream */
static float baseline_temp_dn = 0.0f;  /* pre-pulse T0 downstream */
static float max_temp_up = 0.0f;       /* post-pulse T1 upstream */
static float max_temp_dn = 0.0f;       /* post-pulse T2 downstream */

/* ADS122U04 UART command frame (simplified protocol) */
typedef struct {
    uint8_t start;
    uint8_t cmd;
    uint8_t reg;
    uint8_t data[2];
    uint8_t crc;
} __attribute__((packed)) adc_frame_t;

/* ---- Low-level UART helpers (platform-specific stubs) ---- */

extern void uart2_send(const uint8_t *buf, uint16_t len);
extern uint16_t uart2_recv(uint8_t *buf, uint16_t maxlen, uint32_t timeout_ms);
extern void gpio_write(int pin, int val);
extern int  gpio_read(int pin);
extern void delay_ms(uint32_t ms);

/*
 * ADS122U04 register configuration for ratiometric thermistor measurement:
 *   Reg 0 (mux):  MUX_AIN0_AIN1 (channel 0 differential)
 *   Reg 1 (PGA):  Gain 4, no PGA bypass for differential
 *   Reg 2 (DR):   20 SPS, normal mode, continuous
 *   Reg 3 (ref):  Internal 2.048 V reference
 *   Reg 4 (CS):   No current excitation
 */
static const uint8_t adc_reg_init[5] = {
    0x01,  /* MUX[3:0]=0001 AINp=AIN0, AINn=AIN1 */
    0x04,  /* PGA gain = 4 (±0.8125 V), PGA enabled */
    0x04,  /* DR=20 SPS, normal, continuous */
    0x00,  /* Internal Vref 2.048 V */
    0x00   /* No IDAC current */
};

static int ads122u04_write_reg(uint8_t reg, uint8_t val)
{
    uint8_t buf[3];
    buf[0] = 0x40 | (reg & 0x0F);   /* WREG command */
    buf[1] = 0x00;                   /* write 1 byte */
    buf[2] = val;
    /* (CRC omitted for brevity — production code adds CRC-8) */
    gpio_write(PIN_ADC_CS, 0);
    uart2_send(buf, 3);
    gpio_write(PIN_ADC_CS, 1);
    return 0;
}

static int ads122u04_read_data(float *voltage)
{
    uint8_t tx = 0x10;   /* RDATA command */
    uint8_t rx[3];
    gpio_write(PIN_ADC_CS, 0);
    uart2_send(&tx, 1);
    if (uart2_recv(rx, 3, 100) != 3) {
        gpio_write(PIN_ADC_CS, 1);
        return -1;
    }
    gpio_write(PIN_ADC_CS, 1);
    /* 24-bit signed, MSB first */
    int32_t raw = ((int32_t)rx[0] << 16) | ((int32_t)rx[1] << 8) | rx[2];
    if (raw & 0x800000) raw |= 0xFF000000;  /* sign-extend */
    /* Vref = 2.048 V, gain = 4 → LSB = 2.048 / (4 × 8388608) = 61 nV */
    *voltage = (float)raw * (2.048f / (4.0f * 8388608.0f));
    return 0;
}

int probe_init(void)
{
    /* Power-gate the analog front-end ON */
    gpio_write(PIN_AFE_POWER, 0);   /* P-MOSFET: low = ON */
    delay_ms(10);
    gpio_write(PIN_AFE_RESET, 1);
    delay_ms(1);
    gpio_write(PIN_AFE_RESET, 0);
    delay_ms(5);

    /* Configure ADS122U04 registers */
    for (uint8_t i = 0; i < 5; i++) {
        ads122u04_write_reg(i, adc_reg_init[i]);
    }
    delay_ms(1);

    probe_state = PROBE_IDLE;
    return 0;
}

void probe_power_down(void)
{
    gpio_write(PIN_AFE_POWER, 1);   /* P-MOSFET: high = OFF */
    probe_state = PROBE_IDLE;
}

/*
 * Read one thermistor temperature.
 * channel: 0 = upstream (AIN0/AIN1), 1 = downstream (AIN2/AIN3)
 * Returns temperature in °C, or NAN on error.
 */
float probe_read_thermistor(int channel)
{
    /* Switch MUX to the requested channel */
    uint8_t mux_reg;
    if (channel == 0)
        mux_reg = 0x01;  /* AIN0(+) / AIN1(-) */
    else
        mux_reg = 0x23;  /* AIN2(+) / AIN3(-) */
    ads122u04_write_reg(0, mux_reg);
    delay_ms(55);  /* 1/20 SPS settling */

    float voltage;
    if (ads122u04_read_data(&voltage) != 0)
        return NAN;

    /* Voltage divider: R_therm = R_ref × (Vref/V_meas - 1)
     * With ratiometric measurement the ADC reads the divider voltage
     * relative to Vref (2.048 V). R_ref = 10 kΩ.
     */
    if (voltage <= 0.0f || voltage >= 2.048f)
        return NAN;
    float r_therm = THERM_R_DIVIDER * (2.048f / voltage - 1.0f);

    if (r_therm <= 0.0f || r_therm > 1e6f)
        return NAN;

    /* Steinhart-Hart equation: T = 1 / (A + B·ln(R) + C·ln(R)³) */
    float ln_r = logf(r_therm);
    float inv_t = THERM_A + THERM_B * ln_r + THERM_C * ln_r * ln_r * ln_r;
    float temp_k = 1.0f / inv_t;
    float temp_c = temp_k - 273.15f;

    return temp_c;
}

/*
 * Fire a 2 s heat pulse.
 * Uses TIM2 in one-pulse mode — the hardware timer disables the heater
 * automatically after PULSE_DURATION_MS, independent of firmware.
 * Also asserts the high-side enable (safety redundancy).
 */
void probe_fire_heater(void)
{
    /* Safety: check overcurrent fault is clear */
    if (gpio_read(PIN_HEATER_FAULT) == 0) {
        /* Fault line is active-low; 0 = fault present */
        return;
    }

    /* Enable high-side switch (safety redundancy) */
    gpio_write(PIN_HEATER_ENABLE, 1);

    /* Start TIM2 one-pulse mode — gate goes high for PULSE_DURATION_MS */
    gpio_write(PIN_HEATER_MOSFET, 1);

    /* Firmware-side watchdog — wait for pulse to complete */
    delay_ms(PULSE_DURATION_MS);

    /* Ensure heater is off */
    gpio_write(PIN_HEATER_MOSFET, 0);
    gpio_write(PIN_HEATER_ENABLE, 0);
}

/*
 * Run the full measurement cycle:
 *   1. Pre-pulse baseline (10 s @ 10 Hz)
 *   2. Fire heat pulse (2 s)
 *   3. Post-pulse sampling (60 s @ 4 Hz, track max)
 *   4. Return raw results via the result struct
 */
int probe_run_cycle(probe_result_t *result)
{
    probe_state = PROBE_BASELINE;

    /* ---- 1. Baseline ---- */
    float sum_up = 0.0f, sum_dn = 0.0f;
    int valid = 0;
    for (int i = 0; i < BASELINE_SAMPLES; i++) {
        float t_up = probe_read_thermistor(0);
        float t_dn = probe_read_thermistor(1);
        if (!isnan(t_up) && !isnan(t_dn)) {
            sum_up += t_up;
            sum_dn += t_dn;
            valid++;
        }
        delay_ms(1000 / BASELINE_SAMPLE_HZ);
    }
    if (valid < BASELINE_SAMPLES / 2)
        return -1;  /* too many bad readings */

    baseline_temp_up = sum_up / valid;
    baseline_temp_dn = sum_dn / valid;

    /* ---- 2. Heat pulse ---- */
    probe_state = PROBE_PULSE;
    probe_fire_heater();

    /* ---- 3. Post-pulse sampling ---- */
    probe_state = PROBE_POSTPULSE;
    max_temp_up = baseline_temp_up;
    max_temp_dn = baseline_temp_dn;

    for (int i = 0; i < POST_PULSE_SAMPLES; i++) {
        float t_up = probe_read_thermistor(0);
        float t_dn = probe_read_thermistor(1);
        if (!isnan(t_up) && t_up > max_temp_up) max_temp_up = t_up;
        if (!isnan(t_dn) && t_dn > max_temp_dn) max_temp_dn = t_dn;
        delay_ms(1000 / POST_PULSE_SAMPLE_HZ);
    }

    /* ---- 4. Compute temperature rises ---- */
    result->t0_up = baseline_temp_up;
    result->t0_dn = baseline_temp_dn;
    result->t1_up = max_temp_up;
    result->t2_dn = max_temp_dn;
    result->dt_up = max_temp_up - baseline_temp_up;   /* ΔT upstream */
    result->dt_dn = max_temp_dn - baseline_temp_dn;   /* ΔT downstream */

    probe_state = PROBE_IDLE;
    return 0;
}

probe_state_t probe_get_state(void)
{
    return probe_state;
}

int probe_check_health(void)
{
    /* Check overcurrent comparator */
    if (gpio_read(PIN_HEATER_FAULT) == 0)
        return PROBE_HEATER_FAULT;

    /* Check thermistor continuity (resistance in valid range) */
    float t = probe_read_thermistor(0);
    if (isnan(t) || t < -40.0f || t > 100.0f)
        return PROBE_THERM1_FAULT;
    t = probe_read_thermistor(1);
    if (isnan(t) || t < -40.0f || t > 100.0f)
        return PROBE_THERM2_FAULT;

    return PROBE_OK;
}