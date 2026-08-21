/*
 * sipm_bias.c — SiPM 30 V bias boost (TPS61158) enable / fault / monitor
 *
 * The SiPMs need ~29.5 V reverse bias. A TPS61158 boost converter
 * generates this from the 3.7 V LiPo, current-limited to 5 mA.
 * GPIO15 (BIAS_EN) enables the boost; ADC1_CH5 (BIAS_MON, via a
 * ÷30 divider) monitors the voltage; GPIO38 reads the OCP fault.
 */
#include "sipm_bias.h"
#include "sky_lens.h"

#ifdef SKY_LENS_SIM
#include "port_sim.h"
#else
#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_log.h"
#include "esp_rom_delay.h"
static const char *TAG = "bias";
#define PIN_BIAS_EN     15
#define PIN_BIAS_FAULT  38
#define ADC_CH_BIAS     ADC_CHANNEL_5   /* GPIO16 = ADC1_CH5 */
static adc_oneshot_unit_handle_t s_adc;
static bool s_enabled = false;
#endif

void sipm_bias_init(void)
{
#ifdef SKY_LENS_SIM
    port_sim_log("sipm_bias init (sim)");
#else
    gpio_set_direction(PIN_BIAS_EN, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_BIAS_EN, 0);
    gpio_set_direction(PIN_BIAS_FAULT, GPIO_MODE_INPUT);
    /* ADC1 for bias monitor (÷30 divider: 30 V → 1.0 V) */
    adc_oneshot_unit_init_cfg_t cfg = { .unit_id = ADC_UNIT_1 };
    adc_oneshot_new_unit(&cfg, &s_adc);
    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten = ADC_ATTEN_DB_11,   /* ~3.3 V full scale */
        .bitwidth = ADC_BITWIDTH_12,
    };
    adc_oneshot_config_channel(s_adc, ADC_CH_BIAS, &chan_cfg);
    ESP_LOGI(TAG, "sipm_bias init");
#endif
}

bool sipm_bias_enable(void)
{
#ifdef SKY_LENS_SIM
    port_sim_log("sipm_bias enable (sim) → 29.5 V OK");
    return true;
#else
    if (s_enabled) return true;
    gpio_set_level(PIN_BIAS_EN, 1);
    esp_rom_delay_us(50000);   /* 50 ms rail settle */
    if (sipm_bias_fault()) {
        ESP_LOGE(TAG, "bias boost fault on enable");
        gpio_set_level(PIN_BIAS_EN, 0);
        return false;
    }
    s_enabled = true;
    float v = sipm_bias_voltage();
    ESP_LOGI(TAG, "sipm_bias enabled: %.1f V", v);
    return (v > 27.0f && v < 32.0f);
#endif
}

void sipm_bias_disable(void)
{
#ifdef SKY_LENS_SIM
    port_sim_log("sipm_bias disable (sim)");
#else
    gpio_set_level(PIN_BIAS_EN, 0);
    s_enabled = false;
    ESP_LOGI(TAG, "sipm_bias disabled");
#endif
}

float sipm_bias_voltage(void)
{
#ifdef SKY_LENS_SIM
    return 29.5f;
#else
    int raw = 0;
    adc_oneshot_read(s_adc, ADC_CH_BIAS, &raw);
    /* raw is 0..4095 for 0..3.3 V; ÷30 divider → V_bias = raw * 3.3 * 30 / 4096 */
    return (float)raw * 3.3f * 30.0f / 4096.0f;
#endif
}

bool sipm_bias_fault(void)
{
#ifdef SKY_LENS_SIM
    return false;
#else
    return gpio_get_level(PIN_BIAS_FAULT) == 0;   /* active-low fault */
#endif
}

void sipm_bias_clear_fault(void)
{
    /* The TPS61158 fault is cleared by cycling BIAS_EN */
    sipm_bias_disable();
    sipm_bias_enable();
}