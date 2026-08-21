/*
 * hall-puck / firmware / Core / Src / ads122u04.c
 * ADS122U04 24-bit delta-sigma ADC driver (SPI1)
 *
 * Configured for differential voltage measurement (AIN0-AIN1) with
 * INA333 instrumentation amplifier front-end.
 *
 * PGA gain 1-128, data rate 20-1000 SPS, internal Vref 2.048V.
 *
 * MIT License.
 */
#include "ads122u04.h"
#include "main.h"
#include "flash_store.h"
#include <math.h>

/* SPI1 handle (STM32 HAL SPI) */
extern SPI_HandleTypeDef hspi1;

/* INA333 gain resistor values (external) */
static const float ina_gain_values[4] = {
    1.0f,       /* INA_GAIN_1X */
    10.0f,      /* INA_GAIN_10X */
    100.0f,     /* INA_GAIN_100X */
    1000.0f,    /* INA_GAIN_1000X */
};

static uint8_t current_ina_gain = INA_GAIN_1X;
static uint8_t current_pga_gain = ADC_GAIN_1;

/* ADS122U04 Vref = 2.048V internal, full-scale = Vref/PGA */
#define ADC_VREF        2.048f
#define ADC_FULLSCALE   8388608.0f  /* 2^23 */

/* ---- SPI helpers ---- */
static void spi_cs_low(uint8_t cs_pin)
{
    /* GPIOA or GPIOB based on pin number */
    if (cs_pin < 16) GPIOA->BSRR = (1 << cs_pin) << 16;
    else GPIOB->BSRR = (1 << (cs_pin - 16)) << 16;
}

static void spi_cs_high(uint8_t cs_pin)
{
    if (cs_pin < 16) GPIOA->BSRR = (1 << cs_pin);
    else GPIOB->BSRR = (1 << (cs_pin - 16));
}

static void spi_write(uint8_t cs_pin, uint8_t *data, int len)
{
    spi_cs_low(cs_pin);
    /* HAL_SPI_Transmit(&hspi1, data, len, 100); */
    /* Simplified direct register access */
    for (int i = 0; i < len; i++) {
        /* Wait for TX empty, write data, wait for RX not empty */
        while (!(SPI1->SR & SPI_SR_TXE));
        *(volatile uint8_t *)&SPI1->DR = data[i];
        while (!(SPI1->SR & SPI_SR_RXNE));
        (void)SPI1->DR;  /* flush RX */
    }
    spi_cs_high(cs_pin);
}

static void spi_read(uint8_t cs_pin, uint8_t *cmd, int cmd_len,
                     uint8_t *rx, int rx_len)
{
    spi_cs_low(cs_pin);
    /* Send command */
    for (int i = 0; i < cmd_len; i++) {
        while (!(SPI1->SR & SPI_SR_TXE));
        *(volatile uint8_t *)&SPI1->DR = cmd[i];
        while (!(SPI1->SR & SPI_SR_RXNE));
        (void)SPI1->DR;
    }
    /* Read response */
    for (int i = 0; i < rx_len; i++) {
        while (!(SPI1->SR & SPI_SR_TXE));
        *(volatile uint8_t *)&SPI1->DR = 0x00;
        while (!(SPI1->SR & SPI_SR_RXNE));
        rx[i] = SPI1->DR;
    }
    spi_cs_high(cs_pin);
}

/* ---- Register access ---- */
static adc_err_t adc_write_reg(uint8_t reg, uint8_t value)
{
    uint8_t cmd[2] = { 0x40 | (reg & 0x0F), value };
    spi_write(ADC_CS_PIN, cmd, 2);
    return ADC_OK;
}

static adc_err_t adc_read_reg(uint8_t reg, uint8_t *value)
{
    uint8_t cmd[1] = { 0x20 | (reg & 0x0F) };
    uint8_t rx[1];
    spi_read(ADC_CS_PIN, cmd, 1, rx, 1);
    *value = rx[0];
    return ADC_OK;
}

static adc_err_t adc_send_cmd(uint8_t cmd)
{
    spi_write(ADC_CS_PIN, &cmd, 1);
    return ADC_OK;
}

/* ---- Public API ---- */
adc_err_t ads122u04_init(void)
{
    /* Configure CS and DRDY pins as GPIO */
    /* CS pins: output, high */
    /* (GPIO init done in main HAL setup) */

    /* Reset ADC */
    delay_ms(10);
    adc_send_cmd(0x06);  /* RESET */
    delay_ms(5);

    /* Config0: MUX = AIN0-AIN1 (0000), PGA gain = 1, PGA enabled */
    adc_write_reg(ADC_REG_CONFIG0, 0x00 | (ADC_GAIN_1 << 1));

    /* Config1: 20 SPS, normal mode, continuous */
    adc_write_reg(ADC_REG_CONFIG1, 0x00 | (ADC_DR_20SPS << 2));

    /* Config2: Vref = internal 2.048V, 50/60Hz reject */
    adc_write_reg(ADC_REG_CONFIG2, 0x00 | (ADC_VREF_INTERNAL << 6));

    /* Config3: IDAC off (not needed for voltage measurement) */
    adc_write_reg(ADC_REG_CONFIG3, 0x00);

    /* Start continuous conversions */
    adc_send_cmd(0x08);

    return ADC_OK;
}

adc_err_t ads122u04_read_raw(int32_t *raw)
{
    /* Wait for DRDY (active low) with timeout */
    uint32_t timeout = sys_tick_ms + 100;  /* 100ms timeout */
    while (GPIOB->IDR & (1 << (ADC_DRDY_PIN - 16))) {
        if (sys_tick_ms > timeout) return ADC_ERR_TIMEOUT;
    }

    /* Read 3 bytes (24-bit data) using RDATA command */
    uint8_t cmd[1] = { 0x10 };
    uint8_t rx[3];
    spi_read(ADC_CS_PIN, cmd, 1, rx, 3);

    /* Convert to signed 24-bit */
    uint32_t val = ((uint32_t)rx[0] << 16) | ((uint32_t)rx[1] << 8) | rx[2];
    if (val & 0x800000) val |= 0xFF000000;
    *raw = (int32_t)val;

    return ADC_OK;
}

adc_err_t ads122u04_read_voltage(float *voltage)
{
    int32_t raw;
    adc_err_t err = ads122u04_read_raw(&raw);
    if (err != ADC_OK) return err;

    /* V = (raw / 2^23) * (Vref / PGA_gain) */
    float pga_gain = (float)(1 << current_pga_gain);
    *voltage = ((float)raw / ADC_FULLSCALE) * (ADC_VREF / pga_gain);

    return ADC_OK;
}

adc_err_t ads122u04_read_voltage_uv(float *voltage_uv)
{
    float v_adc;
    adc_err_t err = ads122u04_read_voltage(&v_adc);
    if (err != ADC_OK) return err;

    /* Divide by INA333 gain to get sample-terminal voltage */
    float ina_gain = ina_gain_values[current_ina_gain];
    *voltage_uv = (v_adc / ina_gain) * 1e6f;  /* V → µV */

    /* Subtract zero offset */
    const flash_config_t *cfg = flash_store_get();
    *voltage_uv -= cfg->voltage_offset_uv;

    return ADC_OK;
}

adc_err_t ads122u04_set_gain(uint8_t gain)
{
    if (gain > ADC_GAIN_128) return ADC_ERR_SPI;
    current_pga_gain = gain;

    uint8_t cfg0;
    adc_read_reg(ADC_REG_CONFIG0, &cfg0);
    cfg0 = (cfg0 & 0xF1) | (gain << 1);
    adc_write_reg(ADC_REG_CONFIG0, cfg0);

    return ADC_OK;
}

adc_err_t ads122u04_set_data_rate(uint8_t rate)
{
    if (rate > ADC_DR_1000SPS) return ADC_ERR_SPI;
    uint8_t cfg1;
    adc_read_reg(ADC_REG_CONFIG1, &cfg1);
    cfg1 = (cfg1 & 0x83) | (rate << 2);
    adc_write_reg(ADC_REG_CONFIG1, cfg1);
    return ADC_OK;
}

void ads122u04_set_ina_gain(uint8_t gain)
{
    if (gain > INA_GAIN_1000X) gain = INA_GAIN_1000X;
    current_ina_gain = gain;

    /* Control INA333 gain via external analog switch (GPIO) */
    if (gain & 1) GPIOA->BSRR = (1 << INA_GAIN_SEL_PIN);
    else GPIOA->BSRR = (1 << INA_GAIN_SEL_PIN) << 16;

    if (gain & 2) GPIOA->BSRR = (1 << INA_GAIN_CLK_PIN);
    else GPIOA->BSRR = (1 << INA_GAIN_CLK_PIN) << 16;

    /* Adjust PGA to complement INA gain:
     * INA 1×  → PGA 128 (for µV signals)
     * INA 10× → PGA 32
     * INA 100× → PGA 8
     * INA 1000× → PGA 1
     */
    static const uint8_t pga_for_ina[4] = {
        ADC_GAIN_128, ADC_GAIN_32, ADC_GAIN_8, ADC_GAIN_1
    };
    ads122u04_set_gain(pga_for_ina[gain]);
}

uint8_t ads122u04_auto_range(float voltage_uv)
{
    /* Auto-range INA333 gain for optimal ADC utilization.
     * Target: ADC input between 50mV and 2V (within 2.048V Vref).
     * INA gain = V_adc / V_sample, so:
     *   V_sample = 50mV → INA gain ≤ 40 (use 10×)
     *   V_sample = 5mV → INA gain ≤ 400 (use 100×)
     *   V_sample = 0.5mV → INA gain ≤ 4000 (use 1000×)
     */
    float v_abs = fabsf(voltage_uv);

    if (v_abs > 50000.0f) {       /* > 50 mV */
        ads122u04_set_ina_gain(INA_GAIN_1X);
        return INA_GAIN_1X;
    } else if (v_abs > 5000.0f) { /* > 5 mV */
        ads122u04_set_ina_gain(INA_GAIN_10X);
        return INA_GAIN_10X;
    } else if (v_abs > 500.0f) {  /* > 0.5 mV */
        ads122u04_set_ina_gain(INA_GAIN_100X);
        return INA_GAIN_100X;
    } else {
        ads122u04_set_ina_gain(INA_GAIN_1000X);
        return INA_GAIN_1000X;
    }
}

adc_err_t ads122u04_start_sync(void)
{
    return adc_send_cmd(0x08);
}

adc_err_t ads122u04_reset(void)
{
    delay_ms(5);
    adc_send_cmd(0x06);
    delay_ms(5);
    return ADC_OK;
}