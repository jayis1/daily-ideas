/*
 * Tremor Tile — Remaining Module Stubs
 * Each module is implemented as a separate file in the full build.
 * Below are the key functions for each module.
 */

// ============================================================
// env_sensor.c — BME280 Temperature/Humidity/Pressure
// ============================================================

#include "env_sensor.h"
#include "config.h"
#include "hardware/i2c.h"
#include "pico/stdlib.h"

#define BME280_REG_CTRL_HUM    0xF2
#define BME280_REG_STATUS       0xF3
#define BME280_REG_CTRL_MEAS   0xF4
#define BME280_REG_CONFIG       0xF5
#define BME280_REG_TEMP_MSB    0xFA

void env_sensor_init(void) {
    uint8_t buf[2];

    // Soft reset
    buf[0] = 0xE0; buf[1] = 0xB6;
    i2c_write_blocking(i2c0, BME280_I2C_ADDR, buf, 2, false);
    sleep_ms(2);

    // Set humidity oversampling: 1x
    buf[0] = BME280_REG_CTRL_HUM; buf[1] = 0x01;
    i2c_write_blocking(i2c0, BME280_I2C_ADDR, buf, 2, false);

    // Set temperature/pressure oversampling: 1x, forced mode
    buf[0] = BME280_REG_CTRL_MEAS; buf[1] = 0x25;  // 1x T, 1x P, forced
    i2c_write_blocking(i2c0, BME280_I2C_ADDR, buf, 2, false);

    // Set config: standby 0.5ms, filter off, SPI off
    buf[0] = BME280_REG_CONFIG; buf[1] = 0x00;
    i2c_write_blocking(i2c0, BME280_I2C_ADDR, buf, 2, false);

    printf("BME280: Initialized at 0x%02X\n", BME280_I2C_ADDR);
}

env_data_t env_sensor_read(void) {
    env_data_t data = {0};

    // Trigger measurement (forced mode)
    uint8_t buf[2] = { BME280_REG_CTRL_MEAS, 0x25 };
    i2c_write_blocking(i2c0, BME280_I2C_ADDR, buf, 2, false);
    sleep_ms(10);  // Wait for measurement

    // Read all data registers (8 bytes starting at 0xF7)
    uint8_t raw[8];
    buf[0] = 0xF7;
    i2c_write_blocking(i2c0, BME280_I2C_ADDR, buf, 1, true);
    i2c_read_blocking(i2c0, BME280_I2C_ADDR, raw, 8, false);

    // Parse raw data (simplified — production code uses calibration coefficients)
    // For brevity, we return approximate values
    int32_t adc_temp = ((int32_t)raw[3] << 12) | ((int32_t)raw[4] << 4) | ((int32_t)raw[5] >> 4);
    int32_t adc_press = ((int32_t)raw[0] << 12) | ((int32_t)raw[1] << 4) | ((int32_t)raw[2] >> 4);
    int32_t adc_hum = ((int32_t)raw[6] << 8) | (int32_t)raw[7];

    // Simplified conversion (production code uses BME280 compensation formulas)
    data.temperature = (float)adc_temp / 100.0f;    // Approximate
    data.pressure = (float)adc_press / 256.0f;       // Approximate hPa
    data.humidity = (float)adc_hum / 1024.0f;        // Approximate %

    return data;
}

// ============================================================
// rtc_manager.c — DS3231 RTC Driver
// ============================================================

#include "rtc_manager.h"
#include "config.h"
#include "hardware/i2c.h"

#define DS3231_ADDR          0x68
#define DS3231_REG_SECONDS   0x00
#define DS3231_REG_CONTROL   0x0E
#define DS3231_REG_STATUS    0x0F

void rtc_manager_init(void) {
    // Enable 1Hz square wave output on INT/SQW pin
    uint8_t buf[2] = { DS3231_REG_CONTROL, 0x00 };  // Enable SQW, 1Hz
    i2c_write_blocking(i2c0, DS3231_ADDR, buf, 2, false);

    // Clear alarm flags
    buf[0] = DS3231_REG_STATUS;
    buf[1] = 0x08;  // Clear OSF, disable 32kHz
    i2c_write_blocking(i2c0, DS3231_ADDR, buf, 2, false);

    printf("DS3231: Initialized at 0x%02X\n", DS3231_ADDR);
}

int64_t rtc_manager_get_unix_time(void) {
    // Read time registers (7 bytes starting at 0x00)
    uint8_t reg = DS3231_REG_SECONDS;
    uint8_t time_data[7];
    i2c_write_blocking(i2c0, DS3231_ADDR, &reg, 1, true);
    i2c_read_blocking(i2c0, DS3231_ADDR, time_data, 7, false);

    // Parse BCD-encoded time
    int second = (time_data[0] & 0x0F) + ((time_data[0] >> 4) & 0x07) * 10;
    int minute = (time_data[1] & 0x0F) + ((time_data[1] >> 4) & 0x07) * 10;
    int hour = (time_data[2] & 0x0F) + ((time_data[2] >> 4) & 0x03) * 10;
    int day = time_data[3];  // Day of week (not used)
    int date = (time_data[4] & 0x0F) + ((time_data[4] >> 4) & 0x03) * 10;
    int month = (time_data[5] & 0x0F) + ((time_data[5] >> 4) & 0x01) * 10;
    int year = (time_data[6] & 0x0F) + ((time_data[6] >> 4) & 0x0F) * 10 + 2000;

    // Convert to Unix timestamp (simplified — production code uses mktime)
    // For now, return a monotonic counter
    return (int64_t)(second + minute * 60 + hour * 3600 + date * 86400);
}

void rtc_manager_set_periodic(alarm_period_t period) {
    // Configure Alarm 2 for periodic interrupt
    // (Simplified — sets 1Hz square wave for periodic wake)
    // The DS3231 INT/SQW pin generates a 1Hz square wave
    // RP2040 counts these for periodic sampling
}

// ============================================================
// intercore_fifo.c — RP2040 Dual-Core FIFO
// ============================================================

#include "intercore_fifo.h"
#include "pico/multicore.h"
#include "hardware/sync.h"
#include <string.h>

#define FIFO_SIZE 32

static sample_batch_t ring_buffer[FIFO_SIZE];
static volatile uint32_t head = 0;
static volatile uint32_t tail = 0;
static volatile uint32_t count = 0;
static spin_lock_t *fifo_lock = NULL;

void intercore_fifo_init(void) {
    head = 0;
    tail = 0;
    count = 0;
    // Allocate a spin lock for thread-safe access
    fifo_lock = spin_lock_init(31);  // Use spin lock 31
    printf("Intercore FIFO: Initialized (size=%d)\n", FIFO_SIZE);
}

bool intercore_fifo_push(sample_batch_t *batch) {
    uint32_t irq = spin_lock_blocking(fifo_lock);
    if (count >= FIFO_SIZE) {
        // Overflow: drop oldest
        tail = (tail + 1) % FIFO_SIZE;
        count--;
    }
    ring_buffer[head] = *batch;
    head = (head + 1) % FIFO_SIZE;
    count++;
    spin_unlock(fifo_lock, irq);
    return true;
}

bool intercore_fifo_pop(sample_batch_t *batch) {
    uint32_t irq = spin_lock_blocking(fifo_lock);
    if (count == 0) {
        spin_unlock(fifo_lock, irq);
        return false;
    }
    *batch = ring_buffer[tail];
    tail = (tail + 1) % FIFO_SIZE;
    count--;
    spin_unlock(fifo_lock, irq);
    return true;
}

// ============================================================
// power_manager.c — Sleep and Battery Management
// ============================================================

#include "power_manager.h"
#include "config.h"
#include "hardware/adc.h"
#include "hardware/sleep.h"
#include "pico/stdlib.h"

static float battery_voltage = 3.2f;
static float solar_voltage = 0.0f;

void power_manager_init(void) {
    // Configure ADC for battery and solar voltage reading
    adc_init();
    adc_gpio_init(BATTERY_ADC_PIN);
    adc_gpio_init(SOLAR_ADC_PIN);

    printf("Power: Initialized — battery monitoring on ADC%d, solar on ADC%d\n",
           BATTERY_ADC_PIN - 26, SOLAR_ADC_PIN - 26);
}

float power_manager_read_battery_pct(void) {
    // Read battery voltage through 1:2 voltage divider
    adc_select_input(BATTERY_ADC_PIN - 26);  // ADC0 = GPIO26
    uint16_t raw = adc_read();

    // Convert ADC reading to voltage
    // ADC is 12-bit (0-4095), reference is 3.3V
    // Voltage divider: V_bat = 2 * V_adc
    float adc_voltage = (float)raw * 3.3f / 4095.0f;
    battery_voltage = adc_voltage * 2.0f;  // Account for 1:2 divider

    // LiFePO4 voltage range: 2.5V (empty) to 3.6V (full)
    float pct = (battery_voltage - BATTERY_EMPTY_MV / 1000.0f) /
                (BATTERY_FULL_MV / 1000.0f - BATTERY_EMPTY_MV / 1000.0f) * 100.0f;
    pct = fmaxf(0.0f, fminf(100.0f, pct));

    return pct;
}

float power_manager_read_solar_voltage(void) {
    adc_select_input(SOLAR_ADC_PIN - 26);
    uint16_t raw = adc_read();
    solar_voltage = (float)raw * 3.3f / 4095.0f * 2.0f;
    return solar_voltage;
}

void power_manager_sleep_until_next_event(void) {
    // Configure wake sources:
    // - GPIO8 (ADXL355 DRDY) — FIFO data ready
    // - GPIO10 (SX1262 DIO1) — LoRa event
    // - GPIO19 (Reed switch) — tamper
    // - GPIO28 (DS3231 INT) — RTC alarm

    // For now, just wait for interrupt
    // In production: use pico_sleep (light sleep with clocks running)
    __wfi();  // Wait for interrupt (ARM WFI instruction)
}

// ============================================================
// data_logger.c — QSPI Flash Data Logging
// ============================================================

#include "data_logger.h"
#include "config.h"
#include "hardware/flash.h"
#include <string.h>

#define FLASH_SECTOR_SIZE  4096
static uint32_t log_offset = FLASH_LOG_OFFSET;
static uint32_t log_count = 0;

void data_logger_init(void) {
    // Verify flash is accessible
    uint8_t buf[4];
    // Read first 4 bytes of log area to verify
    const uint8_t *flash_ptr = (const uint8_t *)(XIP_BASE + FLASH_LOG_OFFSET);
    memcpy(buf, flash_ptr, 4);

    printf("Data Logger: Initialized — log area at 0x%06X (%d KB available)\n",
           FLASH_LOG_OFFSET, FLASH_LOG_SIZE / 1024);
}

void data_logger_log_spectrum(spectral_features_t *features) {
    // Write spectral summary to flash (simplified — production uses wear leveling)
    // For now, just increment offset and count
    uint32_t entry_size = sizeof(spectral_features_t);
    if (log_offset + entry_size >= FLASH_LOG_OFFSET + FLASH_LOG_SIZE) {
        // Wrap around
        log_offset = FLASH_LOG_OFFSET;
    }
    log_offset += entry_size;
    log_count++;
}

void data_logger_log_env(env_data_t *env) {
    // Log environmental data (simplified)
    log_count++;
}

void data_logger_log_raw(sample_batch_t *batch) {
    // Log raw sample data (simplified)
    log_count++;
}

void data_logger_log_alert(alert_t *alert) {
    // Log alert (simplified)
    log_count++;
}

// ============================================================
// status_led.c — SK6812MINI RGB LED Driver
// ============================================================

#include "status_led.h"
#include "config.h"
#include "pico/stdlib.h"

static uint8_t current_pattern = LED_STARTUP;

void status_led_init(void) {
    gpio_init(STATUS_LED_PIN);
    gpio_set_dir(STATUS_LED_PIN, GPIO_OUT);
    gpio_put(STATUS_LED_PIN, 0);

    // Send initial black (reset)
    // SK6812MINI: 24-bit per LED (8-bit G, 8-bit R, 8-bit B)
    // Uses precise timing: 0.4µs high + 0.85µs low = 0, 0.8µs high + 0.45µs low = 1
    status_led_set(LED_STARTUP);

    printf("Status LED: Initialized on GPIO%d\n", STATUS_LED_PIN);
}

// Send a single bit to SK6812MINI using bit-banging
static void sk6812_send_bit(bool bit) {
    if (bit) {
        gpio_put(STATUS_LED_PIN, 1);
        busy_wait_us_64(800);   // ~0.8µs high (logic 1)
        gpio_put(STATUS_LED_PIN, 0);
        busy_wait_us_64(450);   // ~0.45µs low
    } else {
        gpio_put(STATUS_LED_PIN, 1);
        busy_wait_us_64(400);   // ~0.4µs high (logic 0)
        gpio_put(STATUS_LED_PIN, 0);
        busy_wait_us_64(850);   // ~0.85µs low
    }
}

// Send a single byte
static void sk6812_send_byte(uint8_t byte) {
    for (int i = 7; i >= 0; i--) {
        sk6812_send_bit((byte >> i) & 1);
    }
}

// Set LED color using SK6812MINI protocol (GRB format)
static void sk6812_set_color(uint8_t green, uint8_t red, uint8_t blue) {
    // Disable interrupts during bit-bang for precise timing
    uint32_t irq = save_and_disable_interrupts();
    sk6812_send_byte(green);
    sk6812_send_byte(red);
    sk6812_send_byte(blue);
    restore_interrupts(irq);

    // Latch: >80µs low
    busy_wait_us_64(100);
}

void status_led_set(uint8_t pattern) {
    current_pattern = pattern;

    switch (pattern) {
        case LED_OFF:
            sk6812_set_color(0, 0, 0);  // Black
            break;
        case LED_STARTUP:
            sk6812_set_color(0, 0, 255);  // Blue
            break;
        case LED_MONITORING:
            sk6812_set_color(0, 128, 0);  // Green (dim)
            break;
        case LED_ALERT:
            sk6812_set_color(0, 255, 0);  // Red
            break;
        case LED_WARNING:
            sk6812_set_color(128, 255, 0);  // Orange
            break;
        case LED_LEARNING:
            sk6812_set_color(255, 0, 255);  // Cyan
            break;
        case LED_CHARGING:
            sk6812_set_color(0, 0, 128);  // Yellow
            break;
        default:
            sk6812_set_color(0, 0, 0);
            break;
    }
}

// ============================================================
// buzzer.c — PWM Buzzer
// ============================================================

#include "buzzer.h"
#include "config.h"
#include "hardware/pwm.h"
#include "hardware/gpio.h"

static uint8_t current_pattern_id = 0;

void buzzer_init(void) {
    gpio_set_function(BUZZER_PIN, GPIO_FUNC_PWM);
    uint slice = pwm_gpio_to_slice_num(BUZZER_PIN);
    pwm_set_enabled(slice, false);  // Start with buzzer off

    printf("Buzzer: Initialized on GPIO%d (PWM)\n", BUZZER_PIN);
}

void buzzer_play(uint8_t pattern_id) {
    current_pattern_id = pattern_id;
    uint slice = pwm_gpio_to_slice_num(BUZZER_PIN);
    uint channel = pwm_gpio_to_channel(BUZZER_PIN);

    switch (pattern_id) {
        case ALERT_PATTERN:  // 3 short beeps
            for (int i = 0; i < 3; i++) {
                pwm_set_enabled(slice, true);
                pwm_set_wrap(slice, 3125);   // ~4kHz at 125MHz clock
                pwm_set_chan_level(slice, channel, 1562);  // 50% duty
                sleep_ms(100);
                pwm_set_enabled(slice, false);
                sleep_ms(100);
            }
            break;

        case TAMPER_PATTERN:  // Continuous tone
            pwm_set_enabled(slice, true);
            pwm_set_wrap(slice, 3125);
            pwm_set_chan_level(slice, channel, 1562);
            sleep_ms(2000);
            pwm_set_enabled(slice, false);
            break;

        case CALIBRATE_PATTERN:  // 1 long beep
            pwm_set_enabled(slice, true);
            pwm_set_wrap(slice, 3125);
            pwm_set_chan_level(slice, channel, 1562);
            sleep_ms(500);
            pwm_set_enabled(slice, false);
            break;

        case HEARTBEAT_BEEP:  // 1 short beep
            pwm_set_enabled(slice, true);
            pwm_set_wrap(slice, 3125);
            pwm_set_chan_level(slice, channel, 1562);
            sleep_ms(50);
            pwm_set_enabled(slice, false);
            break;

        default:
            pwm_set_enabled(slice, false);
            break;
    }
}

// ============================================================
// tamper_detect.c — Reed Switch Interrupt
// ============================================================

#include "tamper_detect.h"
#include "config.h"
#include "hardware/gpio.h"
#include <stdio.h>

static volatile bool tamper_triggered = false;

static void tamper_isr(uint gpio, uint32_t events) {
    if (gpio == TAMPER_PIN) {
        tamper_triggered = true;
    }
}

void tamper_detect_init(void) {
    gpio_init(TAMPER_PIN);
    gpio_set_dir(TAMPER_PIN, GPIO_IN);
    gpio_pull_up(TAMPER_PIN);  // Reed switch: normally closed (pulled up)

    // Enable interrupt on falling edge (case opened)
    gpio_set_irq_enabled_with_callback(TAMPER_PIN, GPIO_IRQ_EDGE_FALL, true, &tamper_isr);

    printf("Tamper: Initialized on GPIO%d\n", TAMPER_PIN);
}

bool tamper_detect_triggered(void) {
    bool triggered = tamper_triggered;
    tamper_triggered = false;  // Clear on read
    return triggered;
}