/*
 * ads1256.h — ADS1256 24-bit delta-sigma ADC driver
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * SPI interface, DRDY interrupt-driven sampling at 1 kSPS.
 */

#ifndef ADS1256_H
#define ADS1256_H

#include <stdint.h>
#include <stdbool.h>

/* ADS1256 register addresses */
#define ADS1256_REG_STATUS    0x00
#define ADS1256_REG_MUX       0x01
#define ADS1256_REG_ADCON     0x02
#define ADS1256_REG_DRATE     0x03
#define ADS1256_REG_IO        0x04
#define ADS1256_REG_OFC0      0x05
#define ADS1256_REG_OFC1      0x06
#define ADS1256_REG_OFC2      0x07
#define ADS1256_REG_FSC0      0x08
#define ADS1256_REG_FSC1      0x09
#define ADS1256_REG_FSC2      0x0A

/* ADS1256 commands */
#define ADS1256_CMD_WAKEUP    0x00
#define ADS1256_CMD_RDATA     0x01
#define ADS1256_CMD_RDATAC    0x03
#define ADS1256_CMD_SDATAC    0x0F
#define ADS1256_CMD_RREG      0x10
#define ADS1256_CMD_WREG      0x50
#define ADS1256_CMD_SELFCAL   0xF0
#define ADS1256_CMD_SYNC      0xFC
#define ADS1256_CMD_STANDBY   0xFD
#define ADS1256_CMD_RESET     0xFE

/* Data rates (DRATE register values) */
#define ADS1256_DRATE_30000SPS  0xF0
#define ADS1256_DRATE_15000SPS  0xE0
#define ADS1256_DRATE_7500SPS   0xD0
#define ADS1256_DRATE_1000SPS   0xA2  /* Our default: 1 kSPS */
#define ADS1256_DRATE_500SPS    0x92
#define ADS1256_DRATE_100SPS    0x62
#define ADS1256_DRATE_30SPS     0x22

/* PGA gain settings (ADCON register bits 3:0) */
#define ADS1256_PGA_1   0x00
#define ADS1256_PGA_2   0x01
#define ADS1256_PGA_4   0x02
#define ADS1256_PGA_8   0x03
#define ADS1256_PGA_16  0x04
#define ADS1256_PGA_32  0x05
#define ADS1256_PGA_64  0x06

/* Vref = 2.5V (internal reference) */
#define ADS1256_VREF     2.5f
#define ADS1256_FULLSCALE 8388607.0f  /* 2^23 - 1 */

/* Sampling state */
typedef enum {
    ADS1256_STATE_IDLE = 0,
    ADS1256_STATE_ACQUIRING,
    ADS1256_STATE_READY,
} ads1256_state_t;

/* Initialize the ADS1256 via SPI */
int ads1256_init(void);

/* Configure data rate and PGA gain */
int ads1256_set_drate(uint8_t drate_reg);
int ads1256_set_pga(uint8_t pga);

/* Start / stop continuous data acquisition mode */
int ads1256_start_continuous(void);
int ads1256_stop_continuous(void);

/* Called from DRDY EXTI ISR — triggers SPI DMA read of 24-bit sample */
void ads1256_drdy_isr(void);

/* Called from SPI DMA complete callback — stores sample in buffer */
void ads1256_spi_dma_complete(void);

/* Get the most recent sample (blocking, with timeout ms) */
int32_t ads1256_read_sample(uint32_t timeout_ms);

/* Convert raw 24-bit signed sample to voltage (Vmid-referenced, in volts) */
float ads1256_to_volts(int32_t raw, uint8_t pga, float ina_gain);

/* Non-blocking check: is a new sample available? */
bool ads1256_sample_available(void);

/* Get sample count since session start */
uint32_t ads1256_sample_count(void);

/* Perform self-calibration (offset + full-scale) */
int ads1256_self_cal(void);

/* Reset the ADC via SPI command */
int ads1256_reset(void);

/* Enter standby (low-power) mode */
int ads1256_standby(void);

#endif /* ADS1256_H */