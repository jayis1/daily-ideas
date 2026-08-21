/*
 * ads122.h — ADS122U04 24-bit delta-sigma ADC driver (header)
 */
#ifndef ADS122_H
#define ADS122_H

#include <stdint.h>
#include <stdbool.h>

/* ADS122U04 register addresses */
#define ADS_REG_CONFIG0    0x00   /* Input multiplexer, gain, PGA */
#define ADS_REG_CONFIG1    0x01   /* Data rate, operating mode, conv mode, temp sensor */
#define ADS_REG_CONFIG2    0x02   /* Vref, IDAC, IDAC routing */
#define ADS_REG_CONFIG3    0x03   /* DRDY mode, status byte, CRC */
#define ADS_REG_MUX        0x00   /* mux config within config0 */

/* Channel mux settings (AINP, AINN) */
#define ADS_MUX_AIN0_AIN1   0x00  /* CH0: sample RTD (differential) */
#define ADS_MUX_AIN2_AIN3   0x01  /* CH1: ref RTD (differential) */
#define ADS_MUX_AIN4_AVSS   0x0A  /* CH2: current sense (single-ended) */
#define ADS_MUX_AVDD_AVSS   0x0B  /* CH3: supply voltage (single-ended) */

/* Gain settings */
#define ADS_GAIN_1   0x00
#define ADS_GAIN_2   0x01
#define ADS_GAIN_4   0x02
#define ADS_GAIN_8   0x03
#define ADS_GAIN_16  0x04
#define ADS_GAIN_32  0x05
#define ADS_GAIN_64  0x06
#define ADS_GAIN_128 0x07

/* Data rate (normal mode) */
#define ADS_DR_20SPS   0x00
#define ADS_DR_45SPS   0x01
#define ADS_DR_90SPS   0x02
#define ADS_DR_175SPS  0x03
#define ADS_DR_330SPS  0x04
#define ADS_DR_600SPS  0x05
#define ADS_DR_1000SPS 0x06

/* Vref */
#define ADS_VREF_INT    0x00  /* internal 2.048V */
#define ADS_VREF_EXT    0x40  /* external VREF pin */

/* IDAC current settings */
#define ADS_IDAC_OFF    0x00
#define ADS_IDAC_10UA   0x01
#define ADS_IDAC_50UA   0x02
#define ADS_IDAC_100UA  0x03
#define ADS_IDAC_250UA  0x04
#define ADS_IDAC_500UA  0x05
#define ADS_IDAC_1000UA 0x06
#define ADS_IDAC_1500UA 0x07

typedef struct {
    int32_t  raw[4];      /* raw 24-bit signed codes per channel */
    float    volt[4];     /* converted voltage per channel */
    float    temp[2];     /* RTD temperatures: [0]=sample, [1]=reference */
    float    i_heater;    /* heater current (A) */
    float    v_supply;    /* supply voltage (V) */
    bool     drdy;        /* data-ready flag */
} ads_data_t;

void     ads_init(void);
void     ads_read_all(ads_data_t *data);
void     ads_start_conversion(void);
bool     ads_is_drdy(void);
float    ads_raw_to_voltage(int32_t raw, uint8_t gain);
void     ads_set_idac(uint8_t idac_setting);
void     ads_calibrate_offset(void);

#endif /* ADS122_H */