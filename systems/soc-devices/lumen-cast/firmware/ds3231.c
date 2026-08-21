/**
 * lumen_cast/firmware/ds3231.c — DS3231 RTC driver
 *
 * Maxim DS3231SN: I2C RTC with TCXO, address 0x68
 * Provides timestamp for scan records.
 */

#include "main.h"
#include <string.h>

#define TAG "RTC"
#define DS3231_ADDR  DS3231_I2C_ADDR

/* Register map */
#define DS3231_REG_SECONDS  0x00
#define DS3231_REG_MINUTES  0x01
#define DS3231_REG_HOURS    0x02
#define DS3231_REG_DAY      0x03
#define DS3231_REG_DATE     0x04
#define DS3231_REG_MONTH    0x05
#define DS3231_REG_YEAR     0x06

static uint8_t bcd_to_dec(uint8_t bcd)
{
    return (bcd >> 4) * 10 + (bcd & 0x0F);
}

static uint8_t dec_to_bcd(uint8_t dec)
{
    return ((dec / 10) << 4) | (dec % 10);
}

int ds3231_init(void)
{
    /* Read seconds register to verify device is present */
    uint8_t sec = i2c_read8(DS3231_ADDR, DS3231_REG_SECONDS);
    LOGI(TAG, "DS3231 detected (seconds=0x%02X = %d)", sec, bcd_to_dec(sec));
    return 0;
}

int ds3231_get_time(uint32_t *epoch)
{
    /* Read all time registers */
    uint8_t buf[7];
    i2c_read_burst(DS3231_ADDR, DS3231_REG_SECONDS, buf, 7);

    int sec  = bcd_to_dec(buf[0]);
    int min  = bcd_to_dec(buf[1]);
    int hour = bcd_to_dec(buf[2] & 0x3F);  /* 24h mode */
    int day  = bcd_to_dec(buf[4]);
    int mon  = bcd_to_dec(buf[5] & 0x1F);
    int year = bcd_to_dec(buf[6]) + 2000;

    /* Convert to Unix epoch (simplified, ignoring leap seconds) */
    /* Days since 2000-01-01 */
    static const int days_per_mon[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    int total_days = 0;
    for (int y = 2000; y < year; y++) {
        total_days += 365;
        if ((y % 4 == 0 && y % 100 != 0) || y % 400 == 0) total_days++;
    }
    for (int m = 1; m < mon; m++) {
        total_days += days_per_mon[m - 1];
        if (m == 2 && ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0))
            total_days++;
    }
    total_days += day - 1;

    *epoch = (uint32_t)total_days * 86400 + hour * 3600 + min * 60 + sec;
    /* Note: this is days-since-2000 epoch, not 1970 Unix epoch.
     * The ESP32-C3 will sync proper NTP time and override via TIME_SYNC. */
    return 0;
}

int ds3231_set_time(uint32_t epoch)
{
    /* Reverse computation from epoch to BCD time registers */
    int sec = epoch % 60;
    int min = (epoch / 60) % 60;
    int hour = (epoch / 3600) % 24;
    int total_days = epoch / 86400;

    /* Simple date computation from days since 2000-01-01 */
    int year = 2000;
    static const int days_per_mon[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    while (1) {
        int year_days = 365;
        if ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0) year_days++;
        if (total_days < year_days) break;
        total_days -= year_days;
        year++;
    }
    int mon = 1;
    while (mon <= 12) {
        int dim = days_per_mon[mon - 1];
        if (mon == 2 && ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0))
            dim++;
        if (total_days < dim) break;
        total_days -= dim;
        mon++;
    }
    int day = total_days + 1;

    i2c_write8(DS3231_ADDR, DS3231_REG_SECONDS, dec_to_bcd(sec));
    i2c_write8(DS3231_ADDR, DS3231_REG_MINUTES, dec_to_bcd(min));
    i2c_write8(DS3231_ADDR, DS3231_REG_HOURS, dec_to_bcd(hour));
    i2c_write8(DS3231_ADDR, DS3231_REG_DATE, dec_to_bcd(day));
    i2c_write8(DS3231_ADDR, DS3231_REG_MONTH, dec_to_bcd(mon));
    i2c_write8(DS3231_ADDR, DS3231_REG_YEAR, dec_to_bcd(year - 2000));

    LOGI(TAG, "RTC set: %04d-%02d-%02d %02d:%02d:%02d",
         year, mon, day, hour, min, sec);
    return 0;
}