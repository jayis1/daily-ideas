/*
 * ads1256.c — ADS1256 24-bit delta-sigma ADC driver
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * SPI1 with DMA, DRDY EXTI interrupt for 1 kSPS continuous sampling.
 */

#include "ads1256.h"
#include "main.h"    /* HAL includes from STM32CubeMX */
#include <string.h>

extern SPI_HandleTypeDef hspi1;

/* ---- Private state ---- */
static volatile ads1256_state_t g_state = ADS1256_STATE_IDLE;
static volatile int32_t  g_last_raw;        /* most recent 24-bit signed sample */
static volatile bool      g_new_sample;     /* flag: new sample ready */
static volatile uint32_t  g_sample_count;   /* total samples this session */
static uint8_t  g_pga = ADS1256_PGA_64;
static float    g_ina_gain = 101.0f;

/* SPI DMA buffers */
static uint8_t g_spi_tx[4];
static uint8_t g_spi_rx[4];

/* ---- Low-level SPI helpers ---- */

static void spi_wait(void)
{
    /* Wait for SPI1 to be ready */
    while (hspi1.State != HAL_SPI_STATE_READY) { }
}

static void spi_cs_low(void)
{
    HAL_GPIO_WritePin(ADC_CS_GPIO_Port, ADC_CS_Pin, GPIO_PIN_RESET);
}

static void spi_cs_high(void)
{
    HAL_GPIO_WritePin(ADC_CS_GPIO_Port, ADC_CS_Pin, GPIO_PIN_SET);
}

/* Send a single command byte */
static void ads1256_cmd(uint8_t cmd)
{
    spi_wait();
    spi_cs_low();
    HAL_SPI_Transmit(&hspi1, &cmd, 1, 10);
    spi_cs_high();
    HAL_Delay(1);  /* tSCLKCS: min 24 tCLK ≈ 0.4 us, but conservative */
}

/* Write a register: WREG reg | 0x00 (n-1), data */
static void ads1256_wreg(uint8_t reg, uint8_t val)
{
    uint8_t tx[3];
    tx[0] = ADS1256_CMD_WREG | (reg << 2);  /* WREG reg, n=1 → 0x00 */
    tx[1] = 0x00;
    tx[2] = val;
    spi_wait();
    spi_cs_low();
    HAL_SPI_Transmit(&hspi1, tx, 3, 10);
    spi_cs_high();
    HAL_Delay(1);
}

/* Read a register */
static uint8_t ads1256_rreg(uint8_t reg)
{
    uint8_t tx[3] = {0};
    uint8_t rx[3] = {0};
    tx[0] = ADS1256_CMD_RREG | (reg << 2);
    tx[1] = 0x00;
    spi_wait();
    spi_cs_low();
    HAL_SPI_TransmitReceive(&hspi1, tx, rx, 3, 10);
    spi_cs_high();
    return rx[2];
}

/* ---- Public API ---- */

int ads1256_init(void)
{
    g_sample_count = 0;
    g_new_sample = false;
    g_state = ADS1256_STATE_IDLE;

    /* Hardware reset via command (assume power-on already done) */
    ads1256_cmd(ADS1256_CMD_RESET);
    HAL_Delay(5);

    /* Configure STATUS: order = MSB first, buffer disabled */
    ads1256_wreg(ADS1256_REG_STATUS, 0x00);  /* MSB first, no buffer */

    /* MUX: AIN0 single-ended (AIN0 + AINCOM) */
    ads1256_wreg(ADS1256_REG_MUX, 0x08);  /* AIN0 = +, AINCOM = − */

    /* ADCON: PGA = 64, clock out off, sensor detect off */
    ads1256_wreg(ADS1256_REG_ADCON, ADS1256_PGA_64);

    /* DRATE: 1000 SPS */
    ads1256_wreg(ADS1256_REG_DRATE, ADS1256_DRATE_1000SPS);

    /* IO: all outputs low */
    ads1256_wreg(ADS1256_REG_IO, 0x00);

    HAL_Delay(10);

    /* Self-calibration (offset + full-scale) */
    ads1256_cmd(ADS1256_CMD_SELFCAL);
    HAL_Delay(700);  /* self-cal takes ~640 ms at 1 kSPS */

    /* Verify STATUS register */
    uint8_t status = ads1256_rreg(ADS1256_REG_STATUS);
    if (status & 0x04) {
        /* CAL bit should be clear after calibration */
        return -1;
    }

    return 0;
}

int ads1256_set_drate(uint8_t drate_reg)
{
    ads1256_wreg(ADS1256_REG_DRATE, drate_reg);
    HAL_Delay(1);
    return 0;
}

int ads1256_set_pga(uint8_t pga)
{
    /* Clock-out disabled, sensor-detect off */
    ads1256_wreg(ADS1256_REG_ADCON, pga & 0x07);
    g_pga = pga;
    HAL_Delay(1);
    ads1256_cmd(ADS1256_CMD_SELFCAL);
    HAL_Delay(700);
    return 0;
}

void ads1256_set_ina_gain(float gain)
{
    g_ina_gain = gain;
}

int ads1256_start_continuous(void)
{
    /* Issue SYNC to align sampling */
    ads1256_cmd(ADS1256_CMD_SYNC);
    HAL_Delay(1);
    /* Issue RDATAC — continuous read mode */
    ads1256_cmd(ADS1256_CMD_RDATAC);
    g_sample_count = 0;
    g_new_sample = false;
    g_state = ADS1256_STATE_ACQUIRING;
    return 0;
}

int ads1256_stop_continuous(void)
{
    ads1256_cmd(ADS1256_CMD_SDATAC);
    g_state = ADS1256_STATE_IDLE;
    return 0;
}

void ads1256_drdy_isr(void)
{
    /* Called from EXTI on DRDY falling edge.
     * Start SPI DMA to read 3 bytes (24-bit sample). */
    if (g_state != ADS1256_STATE_ACQUIRING) return;

    /* In RDATAC mode, DRDY low means data is ready.
     * Pull CS low and issue a SPI receive of 3 bytes. */
    spi_cs_low();
    g_spi_tx[0] = 0x00;  /* dummy */
    g_spi_tx[1] = 0x00;
    g_spi_tx[2] = 0x00;
    HAL_SPI_Receive_DMA(&hspi1, g_spi_rx, 3);
}

void ads1256_spi_dma_complete(void)
{
    /* DMA complete: we have 3 bytes of sample data */
    spi_cs_high();

    /* Assemble 24-bit signed value (MSB first) */
    int32_t raw = ((int32_t)g_spi_rx[0] << 16) |
                  ((int32_t)g_spi_rx[1] << 8)  |
                   (int32_t)g_spi_rx[2];

    /* Sign-extend from 24 to 32 bits */
    if (raw & 0x800000) {
        raw |= 0xFF000000;
    }

    g_last_raw = raw;
    g_new_sample = true;
    g_sample_count++;
}

bool ads1256_sample_available(void)
{
    bool avail = g_new_sample;
    g_new_sample = false;
    return avail;
}

int32_t ads1256_read_sample(uint32_t timeout_ms)
{
    uint32_t start = HAL_GetTick();
    while (!g_new_sample) {
        if (HAL_GetTick() - start > timeout_ms) return 0;
    }
    g_new_sample = false;
    return g_last_raw;
}

float ads1256_to_volts(int32_t raw, uint8_t pga, float ina_gain)
{
    /* ADS1256: V = (raw / 2^23) × Vref / PGA
     * Then divide by INA gain to get input-referred voltage. */
    float v_adc = ((float)raw / ADS1256_FULLSCALE) * ADS1256_VREF / (float)(1 << pga);
    float v_in = v_adc / ina_gain;
    return v_in;
}

uint32_t ads1256_sample_count(void)
{
    return g_sample_count;
}

int ads1256_self_cal(void)
{
    ads1256_cmd(ADS1256_CMD_SELFCAL);
    HAL_Delay(700);
    return 0;
}

int ads1256_reset(void)
{
    ads1256_cmd(ADS1256_CMD_RESET);
    HAL_Delay(5);
    return 0;
}

int ads1256_standby(void)
{
    ads1256_cmd(ADS1256_CMD_STANDBY);
    g_state = ADS1256_STATE_IDLE;
    return 0;
}

/* ---- DMA interrupt callback (called by HAL) ---- */
void HAL_SPI_RxCpltCallback(SPI_HandleTypeDef *hspi)
{
    if (hspi == &hspi1) {
        ads1256_spi_dma_complete();
    }
}

/* ---- EXTI callback for DRDY ---- */
void HAL_GPIO_EXTI_Callback(uint16_t pin)
{
    if (pin == ADC_DRDY_Pin) {
        ads1256_drdy_isr();
    }
}