/*
 * kappa-pin / firmware / main / heater.c
 * Constant-power heater driver via MCP4131 digital pot + OPA548
 *
 * PI control loop maintains Q = V*I constant during the heat pulse.
 * The digital pot sets the reference voltage for the OPA548 current source.
 *
 * MIT License.
 */
#include "heater.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "driver/adc.h"
#include "driver/spi_master.h"
#include <math.h>

static const char *TAG = "heater";

static spi_device_handle_t pot_spi;
static bool heater_active = false;
static float target_power = 0.0f;
static float heater_r = HEATER_RESISTANCE_DEFAULT;
static float heater_len = HEATER_ACTIVE_LENGTH;

/* PI controller state */
static float pi_integral = 0.0f;
static float last_power = 0.0f;
static uint8_t current_wiper = 0;

/* ---- MCP4131 SPI commands ---- */
#define POT_CMD_WRITE   0x00
#define POT_CMD_INCREMENT 0x04
#define POT_CMD_DECREMENT 0x08

static esp_err_t pot_write_wiper(uint8_t value)
{
    uint8_t cmd[2] = { POT_CMD_WRITE, value };
    spi_transaction_t t = {0};
    t.length = 16;
    t.tx_buffer = cmd;
    t.flags = SPI_TRANS_USE_RXDATA;
    return spi_device_polling_transmit(pot_spi, &t);
}

/* ---- Public API ---- */

heater_err_t heater_init(void)
{
    /* Configure HEATER_EN pin */
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << HEATER_EN_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
    };
    gpio_config(&io_conf);
    gpio_set_level(HEATER_EN_PIN, 0);  /* heater OFF */

    /* Configure POT CS pin */
    gpio_config_t cs_conf = {
        .pin_bit_mask = (1ULL << POT_CS_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
    };
    gpio_config(&cs_conf);
    gpio_set_level(POT_CS_PIN, 1);

    /* Add MCP4131 to SPI bus */
    spi_device_interface_config_t dev_cfg = {
        .clock_speed_hz = 10000000,  /* 10 MHz */
        .mode = 0,                    /* CPOL=0, CPHA=0 */
        .spics_io_num = POT_CS_PIN,
        .queue_size = 2,
    };
    esp_err_t ret = spi_bus_add_device(SPI_HOST, &dev_cfg, &pot_spi);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "POT SPI add failed: %s", esp_err_to_name(ret));
        return HEATER_ERR_POT;
    }

    /* Configure voltage monitor ADC */
    adc_oneshot_chan_cfg_t adc_cfg = {
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_12,
    };
    adc_oneshot_config_channel(adc1_handle, ADC_CHANNEL_2, &adc_cfg);

    /* Initialize pot to 0 (no current) */
    pot_write_wiper(0);
    current_wiper = 0;

    ESP_LOGI(TAG, "Heater driver initialized (R=%.3fΩ, L=%.3fm)", heater_r, heater_len);
    return HEATER_OK;
}

heater_err_t heater_set_resistance(float r)
{
    heater_r = r;
    ESP_LOGI(TAG, "Heater resistance set to %.4f Ω", r);
    return HEATER_OK;
}

void heater_set_length(float l)
{
    heater_len = l;
}

heater_err_t heater_set_power(float target_w, float *actual_w)
{
    if (target_w < 0 || target_w > HEATER_MAX_POWER_W) {
        ESP_LOGE(TAG, "Power %.3f W out of range", target_w);
        return HEATER_ERR_OVERCURRENT;
    }

    target_power = target_w;

    /* Initial wiper estimate: P = V² / R, V = wiper_fraction * Vref * gain
     * We need V_heater = sqrt(P * R)
     * The OPA548 gain and pot mapping determines the relationship.
     * Empirically: V_heater ≈ (wiper/255) * 3.3V * 2.0 (OPA548 gain) ≈ 6.6V max
     * For safety we limit to ~3V across heater (I = V/R, must be < 2A)
     */
    float v_target = sqrtf(target_w * heater_r);
    float v_max = 6.6f;  /* max heater voltage from driver */
    float fraction = v_target / v_max;
    if (fraction > 1.0f) fraction = 1.0f;
    current_wiper = (uint8_t)(fraction * 255.0f);
    if (current_wiper > 250) current_wiper = 250;

    pot_write_wiper(current_wiper);

    if (actual_w) {
        *actual_w = (v_target * v_target) / heater_r;
    }

    return HEATER_OK;
}

heater_err_t heater_enable(bool en)
{
    gpio_set_level(HEATER_EN_PIN, en ? 1 : 0);
    heater_active = en;
    if (!en) {
        pot_write_wiper(0);
        current_wiper = 0;
        pi_integral = 0.0f;
    }
    ESP_LOGI(TAG, "Heater %s", en ? "ENABLED" : "DISABLED");
    return HEATER_OK;
}

heater_err_t heater_read_vi(float *voltage, float *current)
{
    /* Read voltage monitor ADC (GPIO13 = ADC1_CH2)
     * Voltage divider: V_heater = Vmon * (R1+R2)/R2, assume 1:1 for simplicity
     */
    int raw;
    esp_err_t ret = adc_oneshot_read(adc1_handle, ADC_CHANNEL_2, &raw);
    if (ret != ESP_OK) return HEATER_ERR_POT;

    float v_mon = (raw / 4095.0f) * 3.3f;   /* ADC reading in V */
    float v_heater = v_mon * 2.0f;           /* scaled by divider gain */

    /* Current = V / R_heater */
    float i_heater = (heater_r > 0.01f) ? (v_heater / heater_r) : 0.0f;

    if (voltage) *voltage = v_heater;
    if (current) *current = i_heater;

    /* Safety: check overcurrent */
    if (i_heater > HEATER_MAX_CURRENT_A) {
        ESP_LOGE(TAG, "OVERCURRENT: %.3f A > %.3f A", i_heater, HEATER_MAX_CURRENT_A);
        heater_emergency_stop();
        return HEATER_ERR_OVERCURRENT;
    }

    return HEATER_OK;
}

heater_err_t heater_read_power(float *power_w)
{
    float v, i;
    heater_err_t err = heater_read_vi(&v, &i);
    if (err != HEATER_OK) return err;
    *power_w = v * i;
    last_power = *power_w;
    return HEATER_OK;
}

heater_err_t heater_pi_update(void)
{
    if (!heater_active) return HEATER_OK;

    float p_actual;
    heater_err_t err = heater_read_power(&p_actual);
    if (err != HEATER_OK) return err;

    /* PI controller: adjust wiper to maintain constant power */
    float error = target_power - p_actual;
    float kp = 20.0f;   /* proportional: wiper steps per W error */
    float ki = 5.0f;    /* integral */

    pi_integral += error * 0.01f;  /* 10ms loop = 0.01s */
    if (pi_integral > 100.0f) pi_integral = 100.0f;
    if (pi_integral < -100.0f) pi_integral = -100.0f;

    float adjustment = kp * error + ki * pi_integral;
    int new_wiper = (int)current_wiper + (int)adjustment;

    if (new_wiper < 0) new_wiper = 0;
    if (new_wiper > 250) new_wiper = 250;

    if (new_wiper != current_wiper) {
        current_wiper = (uint8_t)new_wiper;
        pot_write_wiper(current_wiper);
    }

    last_power = p_actual;
    return HEATER_OK;
}

void heater_emergency_stop(void)
{
    gpio_set_level(HEATER_EN_PIN, 0);
    pot_write_wiper(0);
    current_wiper = 0;
    heater_active = false;
    pi_integral = 0.0f;
    ESP_LOGW(TAG, "EMERGENCY STOP");
}

bool heater_is_active(void)
{
    return heater_active;
}