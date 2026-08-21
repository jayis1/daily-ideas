/*
 * volt-scribe — potentiostat.c
 * Potentiostat control: DAC setpoint, TIA ranging, RE buffer, cell enable
 */

#include "potentiostat.h"
#include <math.h>

/* ── TIA feedback resistor table (Ohms) ───────────────────────── */
static const float tia_rf[TIA_RANGE_COUNT] = {
    100e6f,   /* TIA_1NA   — 1 nA full scale */
    10e6f,    /* TIA_10NA  — 10 nA */
    1e6f,     /* TIA_100NA — 100 nA */
    100e3f,   /* TIA_1UA   — 1 µA */
    10e3f,    /* TIA_10UA  — 10 µA */
    1e3f,     /* TIA_100UA — 100 µA */
    100.0f,   /* TIA_10MA  — 10 mA */
};

static const char *tia_names[TIA_RANGE_COUNT] = {
    "1 nA", "10 nA", "100 nA", "1 µA", "10 µA", "100 µA", "10 mA"
};

/* ── DAC output to setpoint voltage ────────────────────────────── */
/* DAC1 is 12-bit, range 0–2.048V from REF3030.
 * We offset-center: DAC=0 → -2.048V, DAC=2048 → 0V, DAC=4095 → +2.048V
 * Level-shifted in analog by summing with -2.048V reference.
 */

#define DAC_MID    2048
#define DAC_VREF   2.048f
#define DAC_LSB    (DAC_VREF / 4096.0f)

static tia_range_t current_range = TIA_1UA;

/* ── Init ──────────────────────────────────────────────────────── */

extern DAC_HandleTypeDef hdac1;
extern DAC_HandleTypeDef hdac2;
extern ADC_HandleTypeDef hadc1;
extern ADC_HandleTypeDef hadc2;
extern I2C_HandleTypeDef hi2c1;
extern SPI_HandleTypeDef hspi1;
extern UART_HandleTypeDef huart1;

void pot_init(void)
{
    /* Enable DAC channels */
    HAL_DAC_Start(&hdac1, DAC_CHANNEL_1);  /* Potentiostat setpoint */
    HAL_DAC_Start(&hdac1, DAC_CHANNEL_2);  /* Unused */
    HAL_DAC_Start(&hdac2, DAC_CHANNEL_1);  /* EIS AC stimulus */

    /* Default: 0V setpoint, mid-range DAC */
    HAL_DAC_SetValue(&hdac1, DAC_CHANNEL_1, DAC_ALIGN_12B_R, DAC_MID);
    HAL_DAC_SetValue(&hdac2, DAC_CHANNEL_1, DAC_ALIGN_12B_R, 0);

    /* Default TIA range */
    pot_set_range(TIA_1UA);

    /* Cell off */
    pot_cell_enable(0);
}

/* ── Set potentiostat voltage ──────────────────────────────────── */

void pot_set_voltage(float volts)
{
    /* Clamp to ±2.048V */
    if (volts > DAC_VREF)  volts = DAC_VREF;
    if (volts < -DAC_VREF) volts = -DAC_VREF;

    /* Convert voltage to DAC code */
    uint16_t dac_val = (uint16_t)((volts / DAC_VREF) * DAC_MID + DAC_MID);
    if (dac_val > 4095) dac_val = 4095;
    HAL_DAC_SetValue(&hdac1, DAC_CHANNEL_1, DAC_ALIGN_12B_R, dac_val);
}

/* ── Read current through TIA ──────────────────────────────────── */

float pot_read_current(void)
{
    /* Read ADS1115 on I2C (16-bit, ±4.096V range) */
    uint8_t adc_buf[2];
    uint8_t reg = 0x00;  /* Conversion register */

    /* I2C read: ADS1115 address 0x48 (GND) */
    HAL_I2C_Master_Transmit(&hi2c1, 0x48 << 1, &reg, 1, 10);
    HAL_I2C_Master_Receive(&hi2c1, 0x48 << 1, adc_buf, 2, 10);

    int16_t raw = (int16_t)((adc_buf[0] << 8) | adc_buf[1]);
    float voltage = (float)raw * 4.096f / 32768.0f;

    /* Convert voltage to current: I = V / R_f */
    float current = voltage / tia_rf[current_range];
    return current;
}

/* ── Read potential at WE ──────────────────────────────────────── */

float pot_read_potential(void)
{
    /* Read internal ADC2 channel 3 (WE sense) */
    HAL_ADC_Start(&hadc2);
    HAL_ADC_PollForConversion(&hadc2, 10);
    uint16_t raw = HAL_ADC_GetValue(&hadc2);

    /* ADC is 12-bit, 3.3V reference */
    float voltage = (float)raw * 3.3f / 4096.0f;

    /* Subtract mid-point (1.65V = 0V potential) */
    return voltage - 1.65f;
}

/* ── TIA range control ─────────────────────────────────────────── */

void pot_set_range(tia_range_t range)
{
    current_range = range;

    /* 3-bit binary code to ADG1606 select lines */
    uint8_t sel = (uint8_t)range;
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_5, (sel & 1) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_6, (sel & 2) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_7, (sel & 4) ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

tia_range_t pot_get_range(void)
{
    return current_range;
}

/* ── Auto-range TIA ────────────────────────────────────────────── */

tia_range_t pot_auto_range(void)
{
    /* Start at most sensitive range, work down until signal fits */
    for (int i = 0; i < TIA_RANGE_COUNT; i++) {
        pot_set_range((tia_range_t)i);
        HAL_Delay(5);  /* Settle */
        float current = pot_read_current();
        float fullscale = DAC_VREF;  /* TIA output full scale */

        if (fabsf(current * tia_rf[i]) < 0.9f * fullscale) {
            return (tia_range_t)i;
        }
    }
    /* If even 10 mA range saturates, use it anyway */
    return TIA_10MA;
}

/* ── Cell enable / disable ─────────────────────────────────────── */

void pot_cell_enable(int enable)
{
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_8,
                      enable ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

/* ── EIS AC stimulus ──────────────────────────────────────────── */

void pot_eis_set_dc(float volts)
{
    pot_set_voltage(volts);
}

void pot_eis_set_ac_amplitude(float mv_rms)
{
    /* AC amplitude is set as DAC2 peak-to-peak */
    /* DAC2 output is AC-coupled into control amp summing junction */
    /* Store for DDS use */
    eis_ac_amplitude_mv = mv_rms * 1000.0f;
}

/* ── Utility ──────────────────────────────────────────────────── */

const char *tia_range_name(tia_range_t range)
{
    if (range >= 0 && range < TIA_RANGE_COUNT)
        return tia_names[range];
    return "unknown";
}

float tia_rf_value(tia_range_t range)
{
    if (range >= 0 && range < TIA_RANGE_COUNT)
        return tia_rf[range];
    return 0.0f;
}