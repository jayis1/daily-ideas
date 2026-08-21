/*
 * Soil Whisper — Main Firmware
 * STM32WL55JC — Soil Intelligence Probe
 *
 * Copyright (c) 2026 jayis1 — MIT License
 *
 * Firmware flow:
 *   1. Init hardware, load calibration from flash
 *   2. Deep sleep (STOP2 mode, RTC wake)
 *   3. On wake: sample all sensors
 *   4. Format LoRaWAN payload
 *   5. TX over Sub-GHz radio
 *   6. Return to deep sleep
 */

#include "main.h"
#include <string.h>
#include <stdio.h>

/* ── Globals ──────────────────────────────────────────────────────── */

static ADC_HandleTypeDef hadc1;
static I2C_HandleTypeDef hi2c1;
static TIM_HandleTypeDef htim3;
static UART_HandleTypeDef huart2;
static RTC_HandleTypeDef hrtc;
static SUBGHZ_HandleTypeDef hsubghz;

/* Calibration data (stored in flash page, loaded to RAM at boot) */
static cal_data_t g_cal;

/* Sensor readings */
static sensor_data_t g_sensors;

/* LoRaWAN state */
static lora_state_t g_lora;

/* Sleep interval in seconds (default 30 min) */
static uint32_t g_sleep_interval = 1800;

/* ── Forward declarations ──────────────────────────────────────────── */

static void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_ADC1_Init(void);
static void MX_I2C1_Init(void);
static void MX_TIM3_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_RTC_Init(void);
static void MX_SUBGHZ_Init(void);

static void power_gate_init(void);
static void power_gate_on(sensor_power_domain_t domain);
static void power_gate_off(sensor_power_domain_t domain);

static int  moisture_read_all(moisture_data_t *data);
static int  temperature_read_all(temp_data_t *data);
static int  npk_read_all(npk_data_t *data);
static int  ph_read(float *ph_val);
static int  humidity_read(float *rh, float *temp);
static int  vbat_read(float *voltage);

static int  lora_init_and_join(void);
static int  lora_transmit(const uint8_t *payload, uint8_t len, uint8_t port);

static int  load_calibration(void);
static int  save_calibration(const cal_data_t *cal);

static void format_payload(const sensor_data_t *s, uint8_t *buf, uint8_t *len);

static void debug_print(const char *msg);
static void debug_printf(const char *fmt, ...);

/* ── Entry point ──────────────────────────────────────────────────── */

int main(void)
{
    HAL_Init();
    SystemClock_Config();

    MX_GPIO_Init();
    MX_ADC1_Init();
    MX_I2C1_Init();
    MX_TIM3_Init();
    MX_USART2_UART_Init();
    MX_RTC_Init();
    MX_SUBGHZ_Init();

    debug_print("Soil Whisper v1.0 booting\r\n");

    /* Load calibration from flash */
    if (load_calibration() != 0) {
        debug_print("WARNING: No calibration data, using defaults\r\n");
        memset(&g_cal, 0, sizeof(g_cal));
        /* Default moisture calibration: 20kHz=0%, 50kHz=100% */
        g_cal.moist[0].freq_dry  = 20000;
        g_cal.moist[0].freq_wet  = 50000;
        g_cal.moist[1].freq_dry  = 20000;
        g_cal.moist[1].freq_wet  = 50000;
        g_cal.moist[2].freq_dry  = 20000;
        g_cal.moist[2].freq_wet  = 50000;
        /* Default pH: ideal Nernst slope (59.16 mV/pH at 25°C) */
        g_cal.ph_slope  = -59.16f;
        g_cal.ph_offset = 0.0f;
    }

    /* Power-gate everything off initially */
    power_gate_init();

    /* ── Main loop ─────────────────────────────────────────────── */
    while (1) {
        debug_print("Waking sensors...\r\n");

        /* Enable sensor power domains */
        power_gate_on(PWR_MOISTURE);
        HAL_Delay(10);   /* Let oscillators stabilize */

        power_gate_on(PWR_NPK_PH);
        HAL_Delay(500);  /* ISE stabilization time */

        power_gate_on(PWR_ONEWIRE);
        HAL_Delay(100);  /* DS18B20 conversion time (12-bit) */

        /* ── Sample all sensors ─────────────────────────────────── */
        memset(&g_sensors, 0, sizeof(g_sensors));

        moisture_read_all(&g_sensors.moist);
        temperature_read_all(&g_sensors.temp);
        npk_read_all(&g_sensors.npk);
        ph_read(&g_sensors.ph);
        humidity_read(&g_sensors.humidity, &g_sensors.ambient_temp);
        vbat_read(&g_sensors.vbat);

        /* Set validity flags */
        g_sensors.flags = 0;
        g_sensors.flags |= FLAG_MOIST_VALID;
        g_sensors.flags |= FLAG_TEMP_VALID;
        g_sensors.flags |= FLAG_NPK_VALID;
        g_sensors.flags |= FLAG_PH_VALID;
        g_sensors.flags |= FLAG_HUMID_VALID;

        debug_print("Sampling complete\r\n");

        /* ── Transmit via LoRaWAN ───────────────────────────────── */
        uint8_t payload[21];
        uint8_t payload_len;

        format_payload(&g_sensors, payload, &payload_len);

        if (lora_init_and_join() == 0) {
            lora_transmit(payload, payload_len, 2);
            debug_print("LoRa TX complete\r\n");
        } else {
            debug_print("LoRa join failed, data lost\r\n");
        }

        /* ── Power down everything ─────────────────────────────── */
        power_gate_off(PWR_MOISTURE);
        power_gate_off(PWR_NPK_PH);
        power_gate_off(PWR_ONEWIRE);

        /* ── Enter deep sleep ──────────────────────────────────── */
        debug_print("Entering STOP2 sleep for %lus\r\n", g_sleep_interval);

        /* Configure RTC wakeup timer */
        HAL_RTCEx_SetWakeUpTimer_IT(&hrtc, g_sleep_interval, RTC_WAKEUPCLOCK_RTCCLK_DIV16);

        /* Enter STOP2 mode */
        HAL_PWREx_EnterSTOP2Mode(PWR_STOPENTRY_WFI);

        /* Woken up! Re-init clocks (HSE → PLL) */
        SystemClock_Config();

        debug_print("Woke up!\r\n");
    }
}

/* ── Moisture reading (3 channels via TIM3 input capture) ─────────── */

static int moisture_read_all(moisture_data_t *data)
{
    for (int ch = 0; ch < 3; ch++) {
        /* Start TIM3 input capture on channel ch+1 */
        HAL_TIM_IC_Start(&htim3, TIM_CHANNEL_1 + ch);
        HAL_Delay(50);  /* Measure for 50ms */

        uint32_t ic_value = HAL_TIM_ReadCapturedValue(&htim3, TIM_CHANNEL_1 + ch);
        HAL_TIM_IC_Stop(&htim3, TIM_CHANNEL_1 + ch);

        /* Convert frequency to %VWC using calibration */
        float freq_hz = (float)ic_value;
        float vwc_pct;
        float f_dry = g_cal.moist[ch].freq_dry;
        float f_wet = g_cal.moist[ch].freq_wet;

        if (freq_hz <= f_dry) {
            vwc_pct = 0.0f;
        } else if (freq_hz >= f_wet) {
            vwc_pct = 100.0f;
        } else {
            vwc_pct = ((freq_hz - f_dry) / (f_wet - f_dry)) * 100.0f;
        }

        data->vwc[ch] = vwc_pct;
        data->freq_hz[ch] = freq_hz;
    }
    return 0;
}

/* ── Temperature reading (3 × DS18B20 on 1-Wire) ─────────────────── */

#define DS18B20_SKIP_ROM    0xCC
#define DS18B20_CONVERT_T  0x44
#define DS18B20_READ_SCRATCH 0xBE

static void onewire_reset(void)
{
    /* PC13 — open-drain, pull-low 480µs, release, wait 70µs, read presence */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
    /* Configure as output */
    GPIO_InitTypeDef g = {0};
    g.Pin = GPIO_PIN_13;
    g.Mode = GPIO_MODE_OUTPUT_OD;
    g.Pull = GPIO_PULLUP;
    g.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOC, &g);

    HAL_DelayMicroseconds(480);

    /* Release — float high */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
    HAL_DelayMicroseconds(70);

    /* Reconfigure as input to read presence */
    g.Mode = GPIO_MODE_INPUT;
    HAL_GPIO_Init(GPIOC, &g);
    HAL_DelayMicroseconds(410);
}

static void onewire_write_byte(uint8_t byte)
{
    GPIO_InitTypeDef g = {0};
    g.Pin = GPIO_PIN_13;
    g.Mode = GPIO_MODE_OUTPUT_OD;
    g.Pull = GPIO_PULLUP;
    g.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOC, &g);

    for (int i = 0; i < 8; i++) {
        if (byte & (1 << i)) {
            /* Write 1: pull low 6µs, release, wait 64µs */
            HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
            HAL_DelayMicroseconds(6);
            HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
            HAL_DelayMicroseconds(64);
        } else {
            /* Write 0: pull low 60µs, release, wait 10µs */
            HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
            HAL_DelayMicroseconds(60);
            HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);
            HAL_DelayMicroseconds(10);
        }
    }
}

static uint8_t onewire_read_byte(void)
{
    uint8_t byte = 0;
    GPIO_InitTypeDef g = {0};
    g.Pin = GPIO_PIN_13;
    g.Pull = GPIO_PULLUP;

    for (int i = 0; i < 8; i++) {
        g.Mode = GPIO_MODE_OUTPUT_OD;
        g.Speed = GPIO_SPEED_FREQ_HIGH;
        HAL_GPIO_Init(GPIOC, &g);

        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_RESET);
        HAL_DelayMicroseconds(6);
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_13, GPIO_PIN_SET);

        g.Mode = GPIO_MODE_INPUT;
        HAL_GPIO_Init(GPIOC, &g);
        HAL_DelayMicroseconds(9);

        if (HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13) == GPIO_PIN_SET) {
            byte |= (1 << i);
        }
        HAL_DelayMicroseconds(55);
    }
    return byte;
}

static int ds18b20_read_all(temp_data_t *data)
{
    /* Power on DS18B20 via MOSFET */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_12, GPIO_PIN_SET);
    HAL_Delay(10);  /* Power-up time */

    /* Issue skip ROM + convert T to all devices */
    onewire_reset();
    onewire_write_byte(DS18B20_SKIP_ROM);
    onewire_write_byte(DS18B20_CONVERT_T);

    HAL_Delay(750);  /* 12-bit conversion: 750 ms max */

    /* Now read scratchpad 3 times (sequentially on bus) */
    for (int i = 0; i < 3; i++) {
        onewire_reset();
        onewire_write_byte(DS18B20_SKIP_ROM);
        onewire_write_byte(DS18B20_READ_SCRATCH);

        uint8_t scratch[9];
        for (int j = 0; j < 9; j++) {
            scratch[j] = onewire_read_byte();
        }

        /* CRC check could go here — simplified for now */
        int16_t raw = (int16_t)((scratch[1] << 8) | scratch[0]);
        data->celsius[i] = (float)raw / 16.0f;
    }

    /* Power off DS18B20 */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_12, GPIO_PIN_RESET);

    return 0;
}

static int temperature_read_all(temp_data_t *data)
{
    return ds18b20_read_all(data);
}

/* ── NPK reading via MUX + ADS1115 ────────────────────────────────── */

#define ADS1115_ADDR        0x48
#define ADS1115_REG_CONFIG  0x01
#define ADS1115_REG_CONV    0x00

/* MUX channel mapping:
 *   S0-S3 select one of 16 analog inputs:
 *   CH0: NO3⁻ ISE
 *   CH1: H2PO4⁻ ISE
 *   CH2: K⁺ ISE
 *   CH3: pH glass electrode
 *   CH4-CH7: Moisture analog (fallback)
 *   CH8-CH15: Unused
 */

static void mux_select(uint8_t channel)
{
    /* CD74HC4067: S0=PA8, S1=PA9, S2=PA10, S3=PA11 */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_8,  (channel & 0x01) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_9,  (channel & 0x02) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_10, (channel & 0x04) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    /* Note: PA11 is used for MUX S3 but also shared — on STM32WL55JC we repurpose
       a different pin. For this design we use PB9 as MUX S3 instead. */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_9,  (channel & 0x08) ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static int16_t ads1115_read_single(uint8_t channel)
{
    /* Configure ADS1115 for single-ended input on AIN[channel] */
    uint16_t config = 0;
    config |= (1 << 15);          /* Start single conversion */
    config |= (4 + channel) << 12; /* MUX = AIN[channel] vs GND */
    config |= (0 << 9);           /* PGA = ±6.144V */
    config |= (0 << 8);           /* Mode = single-shot */
    config |= (4 << 5);           /* Data rate = 128 SPS */
    config |= (0 << 4);           /* Comparator disabled */

    uint8_t buf[3] = { ADS1115_REG_CONFIG, (config >> 8) & 0xFF, config & 0xFF };
    HAL_I2C_Master_Transmit(&hi2c1, ADS1115_ADDR << 1, buf, 3, 100);

    /* Wait for conversion */
    HAL_Delay(8);

    /* Read conversion register */
    buf[0] = ADS1115_REG_CONV;
    HAL_I2C_Master_Transmit(&hi2c1, ADS1115_ADDR << 1, buf, 1, 100);
    HAL_I2C_Master_Receive(&hi2c1, ADS1115_ADDR << 1, buf, 2, 100);

    return (int16_t)((buf[0] << 8) | buf[1]);
}

static float adc_to_ppm_nitrate(int16_t raw_adc)
{
    /* Convert ADS1115 reading to mV */
    float mv = (float)raw_adc * 6144.0f / 32767.0f;

    /* Nernst equation: E = E0 - slope * log10(C)
     * For NO3⁻ ISE: slope ≈ 54 mV/decade at 25°C
     * Using calibration offset stored in g_cal.npk[0]
     */
    float e0 = g_cal.npk[0].offset_mv;
    float slope = g_cal.npk[0].slope_mv_per_decade;

    if (slope == 0.0f) slope = -54.0f;  /* Default */

    /* E = E0 + slope * log10(C)
     * C = 10^((E - E0) / slope)
     */
    float concentration = powf(10.0f, (mv - e0) / slope);
    if (concentration < 0) concentration = 0;
    if (concentration > 2000) concentration = 2000;

    return concentration;
}

static float adc_to_ppm_phosphate(int16_t raw_adc)
{
    float mv = (float)raw_adc * 6144.0f / 32767.0f;
    float e0 = g_cal.npk[1].offset_mv;
    float slope = g_cal.npk[1].slope_mv_per_decade;
    if (slope == 0.0f) slope = -50.0f;
    float concentration = powf(10.0f, (mv - e0) / slope);
    if (concentration < 0) concentration = 0;
    if (concentration > 600) concentration = 600;
    return concentration;
}

static float adc_to_ppm_potassium(int16_t raw_adc)
{
    float mv = (float)raw_adc * 6144.0f / 32767.0f;
    float e0 = g_cal.npk[2].offset_mv;
    float slope = g_cal.npk[2].slope_mv_per_decade;
    if (slope == 0.0f) slope = -56.0f;
    float concentration = powf(10.0f, (mv - e0) / slope);
    if (concentration < 0) concentration = 0;
    if (concentration > 2500) concentration = 2500;
    return concentration;
}

static int npk_read_all(npk_data_t *data)
{
    mux_select(0);  /* NO3⁻ */
    int16_t raw = ads1115_read_single(0);
    data->no3_ppm = adc_to_ppm_nitrate(raw);

    mux_select(1);  /* H2PO4⁻ */
    raw = ads1115_read_single(0);
    data->po4_ppm = adc_to_ppm_phosphate(raw);

    mux_select(2);  /* K⁺ */
    raw = ads1115_read_single(0);
    data->k_ppm = adc_to_ppm_potassium(raw);

    return 0;
}

/* ── pH reading ──────────────────────────────────────────────────── */

static int ph_read(float *ph_val)
{
    mux_select(3);  /* pH glass electrode */
    int16_t raw = ads1115_read_single(0);

    float mv = (float)raw * 6144.0f / 32767.0f;

    /* pH = (mV - offset) / slope
     * slope is negative (mV decreases with increasing pH)
     * Using 2-point calibration stored in g_cal.ph_offset, g_cal.ph_slope
     */
    float slope = g_cal.ph_slope;
    float offset = g_cal.ph_offset;
    if (slope == 0.0f) slope = -59.16f;

    *ph_val = (mv - offset) / slope;

    /* Clamp to valid range */
    if (*ph_val < 0.0f) *ph_val = 0.0f;
    if (*ph_val > 14.0f) *ph_val = 14.0f;

    return 0;
}

/* ── SHT40 humidity reading (I2C) ─────────────────────────────────── */

#define SHT40_ADDR 0x44

static int humidity_read(float *rh, float *temp)
{
    uint8_t cmd[2] = { 0xFD };  /* High-precision measurement */
    HAL_I2C_Master_Transmit(&hi2c1, SHT40_ADDR << 1, cmd, 1, 100);
    HAL_Delay(10);  /* Measurement takes ~8ms */

    uint8_t data[6];
    HAL_I2C_Master_Receive(&hi2c1, SHT40_ADDR << 1, data, 6, 100);

    /* Convert raw ticks to physical values */
    uint16_t temp_ticks = (data[0] << 8) | data[1];
    uint16_t rh_ticks   = (data[3] << 8) | data[4];

    *temp = -45.0f + 175.0f * ((float)temp_ticks / 65535.0f);
    *rh   = -6.0f + 125.0f * ((float)rh_ticks / 65535.0f);

    /* Clamp humidity */
    if (*rh < 0.0f) *rh = 0.0f;
    if (*rh > 100.0f) *rh = 100.0f;

    return 0;
}

/* ── Battery voltage reading ──────────────────────────────────────── */

static int vbat_read(float *voltage)
{
    /* Read PC1 (ADC1_IN2) — voltage divider on supercap */
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = ADC_CHANNEL_2;
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);

    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 100);
    uint32_t raw = HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);

    /* Voltage divider: VBAT---[1MΩ]---PC1---[1MΩ]---GND
     * So PC1 voltage = VBAT / 2
     * ADC value = (Vpc1 / 3.3) * 4095
     * VBAT = (raw / 4095) * 3.3 * 2
     */
    *voltage = ((float)raw / 4095.0f) * 3.3f * 2.0f;

    return 0;
}

/* ── LoRaWAN ──────────────────────────────────────────────────────── */

/* LoRaWAN ABP credentials (configure per-device in production) */
#define LORA_DEV_ADDR    0x260BFFA1
#define LORA_NWK_SKEY   { 0x2B, 0x7E, 0x15, 0x16, 0x28, 0xAE, 0xD2, 0xA6, \
                          0xAB, 0xF7, 0x15, 0x88, 0x09, 0xCF, 0x4F, 0x3C }
#define LORA_APP_SKEY   { 0x2B, 0x7E, 0x15, 0x16, 0x28, 0xAE, 0xD2, 0xA6, \
                          0xAB, 0xF7, 0x15, 0x88, 0x09, 0xCF, 0x4F, 0x3C }

static int lora_init_and_join(void)
{
    /* ABP join — just configure keys */
    g_lora.dev_addr = LORA_DEV_ADDR;
    /* In production, keys come from secure provisioning */
    return 0;
}

static int lora_transmit(const uint8_t *payload, uint8_t len, uint8_t port)
{
    /* Configure Sub-GHz radio for LoRa modulation */
    SUBGHZ_InitTypeDef subghz_init = {0};
    subghz_init.Mode = SUBGHZ_MODE_TX;
    /* EU868 default: SF7, BW125, CR4/5 */
    HAL_SUBGHZ_ExecSetCmd(&hsubghz, RADIO_SET_POWER, (uint8_t[]){0x0E}, 1);  /* +14 dBm */

    /* Transmit payload (simplified — production uses full LoRaWAN MAC) */
    HAL_SUBGHZ_ExecSetCmd(&hsubghz, RADIO_SET_PACKETTYPE, (uint8_t[]){0x01}, 1);  /* LoRa */
    HAL_SUBGHZ_ExecSetCmd(&hsubghz, RADIO_SET_MODULATIONPARAMS,
        (uint8_t[]){0x07, 0x04, 0x01, 0x00}, 4);  /* SF7, BW125, CR4/5, LDRO off */

    uint8_t irq_cfg[] = {0x01, 0x00, 0x00};  /* TX done IRQ */
    HAL_SUBGHZ_ExecSetCmd(&hsubghz, RADIO_SET_DIOIRQPARAMS, irq_cfg, 3);

    /* Write payload to FIFO */
    HAL_SUBGHZ_ExecSetCmd(&hsubghz, RADIO_SET_BUFFERBASEADDRESS, (uint8_t[]){0x00, 0x00}, 2);
    HAL_SUBGHZ_WriteBuffer(&hsubghz, 0x00, (uint8_t *)payload, len);

    /* Set TX */
    HAL_SUBGHZ_ExecSetCmd(&hsubghz, RADIO_SET_TX, (uint8_t[]){0x00, 0x00, 0x10}, 3);  /* timeout */

    /* Wait for TX done */
    uint32_t timeout = HAL_GetTick() + 5000;
    while (HAL_GetTick() < timeout) {
        uint16_t irq_status;
        HAL_SUBGHZ_ExecGetCmd(&hsubghz, RADIO_GET_IRQSTATUS, (uint8_t *)&irq_status, 2);
        if (irq_status & 0x0001) {  /* TX done */
            HAL_SUBGHZ_ExecSetCmd(&hsubghz, RADIO_CLR_IRQSTATUS, (uint8_t[]){0xFF, 0xFF}, 2);
            return 0;
        }
        HAL_Delay(1);
    }

    return -1;  /* Timeout */
}

/* ── Payload formatting ───────────────────────────────────────────── */

static void format_payload(const sensor_data_t *s, uint8_t *buf, uint8_t *len)
{
    *len = 21;
    memset(buf, 0, 21);

    /* Byte 0: Flags */
    buf[0] = s->flags;

    /* Bytes 1-6: Moisture (×100 for 0.01% resolution) */
    buf[1] = (uint16_t)(s->moist.vwc[0] * 100) & 0xFF;
    buf[2] = ((uint16_t)(s->moist.vwc[0] * 100) >> 8) & 0xFF;
    buf[3] = (uint16_t)(s->moist.vwc[1] * 100) & 0xFF;
    buf[4] = ((uint16_t)(s->moist.vwc[1] * 100) >> 8) & 0xFF;
    buf[5] = (uint16_t)(s->moist.vwc[2] * 100) & 0xFF;
    buf[6] = ((uint16_t)(s->moist.vwc[2] * 100) >> 8) & 0xFF;

    /* Bytes 7-12: Temperature (×100, offset +40°C for -40 to +85 range) */
    int16_t t;
    for (int i = 0; i < 3; i++) {
        t = (int16_t)((s->temp.celsius[i] + 40.0f) * 100.0f);
        buf[7 + i*2]     = t & 0xFF;
        buf[7 + i*2 + 1] = (t >> 8) & 0xFF;
    }

    /* Bytes 13-14: NO3 (×10 for 0.1 ppm resolution) */
    uint16_t no3 = (uint16_t)(s->npk.no3_ppm * 10.0f);
    buf[13] = no3 & 0xFF;
    buf[14] = (no3 >> 8) & 0xFF;

    /* Byte 15: PO4 (×2 for 2 ppm resolution, 0-510 range) */
    buf[15] = (uint8_t)(s->npk.po4_ppm * 0.5f);

    /* Bytes 16-17: K (×10 for 0.1 ppm resolution) */
    uint16_t k = (uint16_t)(s->npk.k_ppm * 10.0f);
    buf[16] = k & 0xFF;
    buf[17] = (k >> 8) & 0xFF;

    /* Byte 18: pH (×10 for 0.1 resolution) */
    buf[18] = (uint8_t)(s->ph * 10.0f);

    /* Byte 19: Humidity (×0.4 for 0-100 range in 8 bits) */
    buf[19] = (uint8_t)(s->humidity * 2.5f);

    /* Byte 20: Battery voltage (×0.02V for 0-5.1V range) */
    buf[20] = (uint8_t)(s->vbat / 0.02f);
}

/* ── Power gating ──────────────────────────────────────────────────── */

static void power_gate_init(void)
{
    /* All power gates OFF initially */
    power_gate_off(PWR_MOISTURE);
    power_gate_off(PWR_NPK_PH);
    power_gate_off(PWR_ONEWIRE);
}

static void power_gate_on(sensor_power_domain_t domain)
{
    switch (domain) {
        case PWR_MOISTURE:
            /* Enable MUX via PA4 (active low) */
            HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);
            break;
        case PWR_NPK_PH:
            /* Enable NPK/pH op-amps via PB0 */
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_SET);
            break;
        case PWR_ONEWIRE:
            /* Enable DS18B20 power via PA12 */
            HAL_GPIO_WritePin(GPIOA, GPIO_PIN_12, GPIO_PIN_SET);
            break;
    }
}

static void power_gate_off(sensor_power_domain_t domain)
{
    switch (domain) {
        case PWR_MOISTURE:
            HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
            break;
        case PWR_NPK_PH:
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_RESET);
            break;
        case PWR_ONEWIRE:
            HAL_GPIO_WritePin(GPIOA, GPIO_PIN_12, GPIO_PIN_RESET);
            break;
    }
}

/* ── Calibration storage (last flash page) ────────────────────────── */

#define CAL_FLASH_PAGE  ((FLASH_PAGE_SIZE * (FLASH_PAGE_NB - 1)))

static int load_calibration(void)
{
    uint32_t *addr = (uint32_t *)CAL_FLASH_PAGE;
    uint32_t magic = *addr;

    if (magic != 0x5O1LC4L) {  /* "SOILCAL" truncated */
        return -1;  /* No calibration stored */
    }

    memcpy(&g_cal, (void *)addr, sizeof(cal_data_t));
    return 0;
}

static int save_calibration(const cal_data_t *cal)
{
    HAL_FLASH_Unlock();

    /* Erase last page */
    FLASH_EraseInitTypeDef erase = {0};
    erase.TypeErase = FLASH_TYPEERASE_PAGES;
    erase.Page = FLASH_PAGE_NB - 1;
    erase.NbPages = 1;

    uint32_t err;
    if (HAL_FLASHEx_Erase(&erase, &err) != HAL_OK) {
        HAL_FLASH_Lock();
        return -1;
    }

    /* Write calibration data */
    const uint8_t *data = (const uint8_t *)cal;
    for (uint32_t i = 0; i < sizeof(cal_data_t); i += 8) {
        uint64_t word = 0;
        memcpy(&word, &data[i], (sizeof(cal_data_t) - i) < 8 ? sizeof(cal_data_t) - i : 8);
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_DOUBLEWORD, CAL_FLASH_PAGE + i, word) != HAL_OK) {
            HAL_FLASH_Lock();
            return -1;
        }
    }

    HAL_FLASH_Lock();
    return 0;
}

/* ── Debug UART ───────────────────────────────────────────────────── */

static void debug_print(const char *msg)
{
    HAL_UART_Transmit(&huart2, (uint8_t *)msg, strlen(msg), 100);
}

static void debug_printf(const char *fmt, ...)
{
    char buf[128];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    debug_print(buf);
}

/* ── HAL MSP and peripheral init ──────────────────────────────────── */

/* Simplified peripheral initialization — production code uses CubeMX-generated init */

static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};

    /* MSI 4 MHz default, will boost after wake from STOP */
    osc.OscillatorType = RCC_OSCILLATORTYPE_MSI;
    osc.MSIState = RCC_MSI_ON;
    osc.MSIClockRange = RCC_MSIRANGE_6;  /* 4 MHz */
    osc.MSICalibrationValue = RCC_MSICALIBRATION_DEFAULT;
    osc.PLL.PLLState = RCC_PLL_NONE;
    HAL_RCC_OscConfig(&osc);

    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                    RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_MSI;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV1;
    clk.APB2CLKDivider = RCC_HCLK_DIV1;
    HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_0);
}

static void MX_GPIO_Init(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    GPIO_InitTypeDef g = {0};

    /* Debug UART TX/RX */
    g.Pin = GPIO_PIN_2 | GPIO_PIN_3;
    g.Mode = GPIO_MODE_AF_PP;
    g.Pull = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    g.Alternate = GPIO_AF4_USART2;
    HAL_GPIO_Init(GPIOA, &g);

    /* MUX select lines: PA8, PA9, PA10, PB9 */
    g.Pin = GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10;
    g.Mode = GPIO_MODE_OUTPUT_PP;
    g.Pull = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOA, &g);

    g.Pin = GPIO_PIN_9;
    HAL_GPIO_Init(GPIOB, &g);

    /* Power gates: PA4 (MUX EN), PA12 (1-Wire PWR), PB0 (NPK PWR) */
    g.Pin = GPIO_PIN_4 | GPIO_PIN_12;
    HAL_GPIO_Init(GPIOA, &g);

    g.Pin = GPIO_PIN_0;
    HAL_GPIO_Init(GPIOB, &g);

    /* Status LEDs: PB2 (green), PB3 (red) */
    g.Pin = GPIO_PIN_2 | GPIO_PIN_3;
    HAL_GPIO_Init(GPIOB, &g);

    /* 1-Wire data: PC13 */
    g.Pin = GPIO_PIN_13;
    g.Mode = GPIO_MODE_OUTPUT_OD;
    g.Pull = GPIO_PULLUP;
    g.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOC, &g);

    /* I2C: PB6 (SCL), PB7 (SDA) */
    g.Pin = GPIO_PIN_6 | GPIO_PIN_7;
    g.Mode = GPIO_MODE_AF_OD;
    g.Pull = GPIO_PULLUP;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    g.Alternate = GPIO_AF4_I2C1;
    HAL_GPIO_Init(GPIOB, &g);
}

static void MX_ADC1_Init(void)
{
    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV4;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc1.Init.LowPowerAutoWait = DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
    hadc1.Init.DMAContinuousRequests = DISABLE;
    hadc1.Init.Overrun = ADC_OVR_DATA_PRESERVED;
    HAL_ADC_Init(&hadc1);
}

static void MX_I2C1_Init(void)
{
    hi2c1.Instance = I2C1;
    hi2c1.Init.Timing = 0x0060A3F2;  /* 100 kHz at 4 MHz MSI */
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    HAL_I2C_Init(&hi2c1);
}

static void MX_TIM3_Init(void)
{
    htim3.Instance = TIM3;
    htim3.Init.Prescaler = 0;
    htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim3.Init.Period = 0xFFFF;
    htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    HAL_TIM_Base_Init(&htim3);
}

static void MX_USART2_UART_Init(void)
{
    huart2.Instance = USART2;
    huart2.Init.BaudRate = 115200;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    HAL_UART_Init(&huart2);
}

static void MX_RTC_Init(void)
{
    hrtc.Instance = RTC;
    hrtc.Init.HourFormat = RTC_HOURFORMAT_24;
    hrtc.Init.AsynchPrediv = 127;   /* 32.768 kHz / 128 = 256 Hz */
    hrtc.Init.SynchPrediv = 255;    /* 256 Hz / 256 = 1 Hz */
    hrtc.Init.OutPut = RTC_OUTPUT_DISABLE;
    hrtc.Init.OutPutRemap = RTC_OUTPUT_REMAP_NONE;
    hrtc.Init.OutPutPolarity = RTC_OUTPUT_POLARITY_HIGH;
    hrtc.Init.OutPutType = RTC_OUTPUT_TYPE_OPENDRAIN;
    HAL_RTC_Init(&hrtc);
}

static void MX_SUBGHZ_Init(void)
{
    hsubghz.Init.Mode = SUBGHZ_MODE_STDBY_RC;
    HAL_SUBGHZ_Init(&hsubghz);
}

/* ── Interrupt handlers ────────────────────────────────────────────── */

void HAL_RTCEx_WakeUpTimerEventCallback(RTC_HandleTypeDef *hrtc)
{
    /* Wakeup from STOP2 mode — main loop continues */
}

void SysTick_Handler(void)
{
    HAL_IncTick();
}