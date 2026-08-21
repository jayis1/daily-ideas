/*
 * pyro-balance / Core/Src/bme280.c — minimal BME280 driver (I²C)
 */
#include "bme280.h"
extern I2C_HandleTypeDef hi2c1;
#define BME_ADDR (0x76 << 1)

static int16_t dig_T1; static int16_t dig_T2, dig_T3;
static uint16_t dig_P1; static int16_t dig_P2,dig_P3,dig_P4,dig_P5,dig_P6,dig_P7,dig_P8,dig_P9;
static uint8_t dig_H1; static int16_t dig_H2,dig_H3,dig_H4,dig_H5; static int8_t dig_H6;
static int32_t t_fine;

static uint8_t r8(uint8_t r){ uint8_t v; HAL_I2C_Master_Transmit(&hi2c1,BME_ADDR,&r,1,10); HAL_I2C_Master_Receive(&hi2c1,BME_ADDR,&v,1,10); return v; }
static void w8(uint8_t r,uint8_t v){ uint8_t b[2]={r,v}; HAL_I2C_Master_Transmit(&hi2c1,BME_ADDR,b,2,10); }
static uint16_t r16le(uint8_t r){ uint8_t b[2]; HAL_I2C_Master_Transmit(&hi2c1,BME_ADDR,&r,1,10); HAL_I2C_Master_Receive(&hi2c1,BME_ADDR,b,2,10); return b[0]|(b[1]<<8); }

void bme280_init(void){
    /* read calibration (simplified) */
    dig_T1=r16le(0x88); dig_T2=(int16_t)r16le(0x8A); dig_T3=(int16_t)r16le(0x8C);
    dig_P1=r16le(0x8E); dig_P2=(int16_t)r16le(0x90); dig_P3=(int16_t)r16le(0x92);
    dig_P4=(int16_t)r16le(0x94); dig_P5=(int16_t)r16le(0x96); dig_P6=(int16_t)r16le(0x98);
    dig_P7=(int16_t)r16le(0x9A); dig_P8=(int16_t)r16le(0x9C); dig_P9=(int16_t)r16le(0x9E);
    dig_H1=r8(0xA1); dig_H2=(int16_t)r16le(0xE1); dig_H3=r8(0xE3);
    int8_t e4=r8(0xE4), e5=r8(0xE5), e6=r8(0xE6);
    dig_H4=(e4<<4)|(e5&0x0F); dig_H5=((e5&0xF0)>>4)|(e6<<4); dig_H6=r8(0xE7);
    w8(0xF2,0x01); /* humidity x1 */
    w8(0xF4,0x27); /* T,P oversample x1, normal mode */
    w8(0xF5,0x08); /* 1000ms standby */
    w8(0xF4,0x27|0x01); /* forced */
}
static int32_t read_raw(uint8_t* d){
    HAL_I2C_Master_Transmit(&hi2c1,BME_ADDR,(uint8_t[]){0xF7},1,10);
    HAL_I2C_Master_Receive(&hi2c1,BME_ADDR,d,8,10);
    int32_t p=(d[0]<<12)|(d[1]<<4)|(d[2]>>4);
    int32_t t=(d[3]<<12)|(d[4]<<4)|(d[5]>>4);
    int32_t h=(d[6]<<8)|d[7];
    (void)p;(void)h; return t;
}
float bme280_temp(void){
    uint8_t d[8]; int32_t adc=read_raw(d);
    int32_t v=adc; int32_t X1=(v>>3)-((int32_t)dig_T1<<1);
    X1=(X1*(int32_t)dig_T2)>>11;
    int32_t X2=((v>>4)-(int32_t)dig_T1);
    X2=((X2*((int32_t)dig_T3))>>14);
    t_fine=X1+X2;
    return (t_fine*5+128)>>8;
}
float bme280_humidity(void){ uint8_t d[8]; read_raw(d); return ((d[6]<<8)|d[7])/1024.0f; }
float bme280_pressure(void){ uint8_t d[8]; read_raw(d); return ((d[0]<<12)|(d[1]<<4)|(d[2]>>4))/256.0f; }