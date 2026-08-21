/*
 * breath.c — breath pressure sensor (MP3V5004G on ADC1)
 *
 * The MP3V5004G outputs Vout = Vs × (0.11 × PkPa + 0.095).
 * At 3.3 V supply: Vout ≈ 0.363 × PkPa + 0.313 V
 * Range: 0..3.0 kPa → 0.31..1.4 V (fits ADC1 range).
 *
 * We read at 1 kHz (oversampled) and apply an exponential curve
 * for velocity mapping.
 */
#include "breath.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_log.h"
#include <math.h>

static const char *TAG = "breath";

static adc_oneshot_unit_handle_t adc1 = NULL;
static adc_channel_t breath_chan;

#define ADC_VREF_MV    3300
#define ADC_MAX        4095
#define SAMPLE_RATE_HZ 1000

/* Calibration: zero-pressure offset (measured at boot) */
static int   offset_adc = 0;
static float pressure_kpa = 0.0f;
static float velocity_f = 0.0f;       /* smoothed 0..1 */
static bool  gate = false;

/* Breath threshold for note-on gate (Pascals above zero) */
#define BREATH_GATE_PA   30.0f
/* Max pressure for full velocity (Pascals) */
#define BREATH_MAX_PA    1500.0f

void breath_init(void)
{
    adc_oneshot_unit_init_cfg_t ucfg = {
        .unit_id = ADC_UNIT_1,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    adc_oneshot_new_unit(&ucfg, &adc1);

    /* Breath sensor on GPIO17 = ADC1_CH6 (we map to a free channel) */
    adc_oneshot_io2chan_t ch = (adc_oneshot_io2chan_t)0;
    /* Use channel number directly for ADC1_CH6 (GPIO17 on S3 is ADC1_CH6) */
    breath_chan = (adc_channel_t)6;
    adc_oneshot_chan_cfg_t cfg = {
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_12,
    };
    adc_oneshot_config_channel(adc1, breath_chan, &cfg);

    /* Measure zero offset (50-sample average) */
    int sum = 0;
    for (int i = 0; i < 50; i++) {
        int raw = 0;
        adc_oneshot_read(adc1, breath_chan, &raw);
        sum += raw;
        vTaskDelay(pdMS_TO_TICKS(2));
    }
    offset_adc = sum / 50;
    ESP_LOGI(TAG, "Breath sensor ready. Zero offset = %d", offset_adc);
}

static int oversample_read(int n)
{
    int sum = 0;
    for (int i = 0; i < n; i++) {
        int raw = 0;
        adc_oneshot_read(adc1, breath_chan, &raw);
        sum += raw;
    }
    return sum / n;
}

void breath_scan(void)
{
    int raw = oversample_read(4);
    /* Subtract offset, clamp to >= 0 */
    int delta = raw - offset_adc;
    if (delta < 0) delta = 0;

    /* Convert ADC counts → voltage → pressure
     * MP3V5004G: P = (Vout - 0.313) / 0.363   [kPa]
     * ADC: Vout = raw * 3.3 / 4095
     * delta_adc = Vout_delta * 4095/3.3
     * So P_kPa = delta_adc * 3.3 / (4095 * 0.363) [kPa]  → ×1000 for Pa */
    float vout = (float)delta * ADC_VREF_MV / 1000.0f / ADC_MAX;
    pressure_kpa = (vout - 0.0f) / 0.363f;  /* already offset-corrected */
    if (pressure_kpa < 0) pressure_kpa = 0;

    float pa = pressure_kpa * 1000.0f;

    /* Velocity 0..1 with exponential curve and smoothing */
    float target = pa / BREATH_MAX_PA;
    if (target > 1.0f) target = 1.0f;
    /* Exponential curve: v = x^1.6 for more dynamic range */
    target = powf(target, 1.6f);
    /* Low-pass smooth (attack fast, release slow) */
    if (target > velocity_f)
        velocity_f = velocity_f * 0.7f + target * 0.3f;  /* fast attack */
    else
        velocity_f = velocity_f * 0.92f + target * 0.08f; /* slow release */

    gate = (pa > BREATH_GATE_PA);
}

uint8_t breath_get_velocity(void)
{
    return (uint8_t)(velocity_f * 127.0f + 0.5f);
}

bool breath_get_gate(void)
{
    return gate;
}

float breath_get_pressure_kpa(void)
{
    return pressure_kpa;
}