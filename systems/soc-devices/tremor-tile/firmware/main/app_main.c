/*
 * Tremor Tile — Structural Vibration Monitor
 * app_main.c — Entry point, dual-core launch, NVS init
 *
 * SoC: RP2040 (Dual ARM Cortex-M0+, 264KB SRAM, 16MB QSPI Flash)
 * Platform: Pico SDK
 */

#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/spi.h"
#include "hardware/i2c.h"
#include "hardware/adc.h"
#include "hardware/pwm.h"
#include "hardware/gpio.h"
#include "hardware/flash.h"
#include "hardware/sync.h"

#include "sensor_acq.h"
#include "env_sensor.h"
#include "rtc_manager.h"
#include "fft_engine.h"
#include "anomaly_detect.h"
#include "lora_radio.h"
#include "data_logger.h"
#include "power_manager.h"
#include "status_led.h"
#include "buzzer.h"
#include "tamper_detect.h"
#include "intercore_fifo.h"
#include "config.h"

// Forward declarations
void core1_entry(void);
void core0_main(void);

int main(void) {
    // Initialize stdio (USB CDC for field service)
    stdio_init_all();

    // Small delay for USB enumeration
    sleep_ms(1000);

    printf("=== Tremor Tile v1.0 ===\n");
    printf("RP2040 dual-core structural vibration monitor\n");
    printf("Build: %s %s\n", __DATE__, __TIME__);

    // Initialize power manager first (configure LDO, check battery)
    power_manager_init();
    float battery_pct = power_manager_read_battery_pct();
    printf("Battery: %.1f%%\n", battery_pct);

    // Initialize status LED (show boot progress)
    status_led_init();
    status_led_set(LED_STARTUP);

    // Initialize SPI buses
    // SPI0: ADXL355 (accelerometer)
    spi_init(spi0, 4000000);  // 4 MHz
    gpio_set_function(PICO_SPI0_RX_PIN, GPIO_FUNC_SPI);
    gpio_set_function(PICO_SPI0_SCK_PIN, GPIO_FUNC_SPI);
    gpio_set_function(PICO_SPI0_CSN_PIN, GPIO_FUNC_SPI);
    gpio_set_function(PICO_SPI0_TX_PIN, GPIO_FUNC_SPI);

    // SPI1: SX1262 (LoRa)
    spi_init(spi1, 4000000);
    gpio_set_function(PICO_SPI1_RX_PIN, GPIO_FUNC_SPI);
    gpio_set_function(PICO_SPI1_SCK_PIN, GPIO_FUNC_SPI);
    gpio_set_function(PICO_SPI1_CSN_PIN, GPIO_FUNC_SPI);
    gpio_set_function(PICO_SPI1_TX_PIN, GPIO_FUNC_SPI);

    // Initialize I2C0: BME280 + DS3231
    i2c_init(i2c0, 400000);  // 400 kHz
    gpio_set_function(I2C0_SDA_PIN, GPIO_FUNC_I2C);
    gpio_set_function(I2C0_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(I2C0_SDA_PIN);
    gpio_pull_up(I2C0_SCL_PIN);

    // Initialize ADC for battery monitoring
    adc_init();
    adc_gpio_init(BATTERY_ADC_PIN);
    adc_gpio_init(SOLAR_ADC_PIN);

    // Initialize GPIO outputs
    gpio_init(ADXL355_RANGE_PIN);
    gpio_set_dir(ADXL355_RANGE_PIN, GPIO_OUT);
    gpio_put(ADXL355_RANGE_PIN, 0);  // ±2g range

    gpio_init(SENSOR_RAIL_EN_PIN);
    gpio_set_dir(SENSOR_RAIL_EN_PIN, GPIO_OUT);
    gpio_put(SENSOR_RAIL_EN_PIN, 1);  // Enable sensor rail

    // Initialize inter-core FIFO
    intercore_fifo_init();

    // Launch Core 1 for signal processing
    multicore_launch_core1(core1_entry);

    // Run Core 0 main loop
    core0_main();

    return 0;
}

// Core 0: Sensor acquisition and communications
void core0_main(void) {
    // Initialize subsystems
    sensor_acq_init();     // ADXL355: 400 Hz ODR, ±2g range, FIFO watermark=32
    env_sensor_init();     // BME280: forced mode, 1Hz oversample
    rtc_manager_init();    // DS3231: precise RTC, set periodic alarm
    lora_radio_init();     // SX1262: SF7, 125kHz BW, +22dBm, 868MHz
    data_logger_init();    // W25Q128: mount flash, check log area
    buzzer_init();         // PWM buzzer on GPIO18

    // Set RTC alarm for periodic acquisition
    rtc_manager_set_periodic(ALARM_EVERY_10_SEC);

    // Announce on LoRa
    lora_radio_send_heartbeat(DEVICE_ID, (uint8_t)battery_pct, 0);
    printf("Core 0: Initialization complete, entering main loop\n");

    // Environmental read timer
    absolute_time_t last_env_read = get_absolute_time();
    absolute_time_t last_heartbeat = get_absolute_time();

    // Main acquisition loop
    while (true) {
        bool did_work = false;

        // 1. Check ADXL355 FIFO
        if (sensor_acq_fifo_ready()) {
            sample_batch_t batch = sensor_acq_read_fifo();
            batch.timestamp = rtc_manager_get_unix_time();

            // Push to Core 1 for FFT processing
            intercore_fifo_push(&batch);

            // Log raw data (selective — every Nth batch)
            if (batch.seq_num % RAW_LOG_INTERVAL == 0) {
                data_logger_log_raw(&batch);
            }

            did_work = true;
        }

        // 2. Handle LoRa TX queue
        if (lora_radio_tx_pending()) {
            lora_radio_send_next();
            did_work = true;
        }

        // 3. Check for anomalies flagged by Core 1
        if (anomaly_detect_alert_pending()) {
            alert_t alert = anomaly_detect_get_alert();

            printf("ANOMALY DETECTED: type=%d severity=%d bands=0x%04x\n",
                   alert.type, alert.severity, alert.affected_bands);

            // Enqueue LoRa alert (high priority, SF12 for max range)
            lora_radio_enqueue_alert(&alert);

            // Audible + visual alert
            buzzer_play(ALERT_PATTERN);
            status_led_set(LED_ALERT);

            // Log alert
            data_logger_log_alert(&alert);

            did_work = true;
        }

        // 4. Environmental context (every 60 seconds)
        if (absolute_time_diff_us(last_env_read, get_absolute_time()) > 60000000) {
            env_data_t env = env_sensor_read();
            data_logger_log_env(&env);
            last_env_read = get_absolute_time();

            // Check for extreme temperature (ADXL355 operating range)
            if (env.temperature < -40.0f || env.temperature > 85.0f) {
                printf("WARNING: Temperature out of range: %.1f C\n", env.temperature);
                status_led_set(LED_WARNING);
            }

            did_work = true;
        }

        // 5. LoRa heartbeat (every 1 hour)
        if (absolute_time_diff_us(last_heartbeat, get_absolute_time()) > HEARTBEAT_INTERVAL_US) {
            battery_pct = power_manager_read_battery_pct();
            lora_radio_send_heartbeat(DEVICE_ID, (uint8_t)battery_pct, 0);
            last_heartbeat = get_absolute_time();
            did_work = true;
        }

        // 6. Check tamper switch
        if (tamper_detect_triggered()) {
            printf("TAMPER: Case opened!\n");
            alert_t tamper_alert = {
                .type = ALERT_TAMPER,
                .severity = 10,
                .affected_bands = 0,
                .timestamp = rtc_manager_get_unix_time(),
            };
            lora_radio_enqueue_alert(&tamper_alert);
            buzzer_play(TAMPER_PATTERN);
            did_work = true;
        }

        // 7. Power management — sleep if nothing to do
        if (!did_work) {
            // Deep sleep until next interrupt (DRDY, RTC alarm, or LoRa DIO)
            power_manager_sleep_until_next_event();
        }
    }
}

// Core 1 entry point — signal processing
void core1_entry(void) {
    printf("Core 1: Signal processing starting\n");

    // Initialize FFT engine
    fft_engine_init();  // 1024-point FFT, Hann window, CMSIS-DSP

    // Initialize anomaly detection
    anomaly_detect_init();  // Load baseline from flash or start learning

    // Sample buffer for FFT
    sample_buffer_t buf;
    fft_engine_reset_buffer(&buf);

    uint32_t fft_count = 0;

    while (true) {
        // Wait for samples from Core 0
        sample_batch_t batch;
        if (intercore_fifo_pop(&batch)) {
            // Append samples to rolling buffer
            fft_engine_append(&buf, &batch);

            // When we have enough samples, run FFT
            if (buf.count >= FFT_SIZE) {
                // Compute FFT and extract features
                spectral_features_t features;
                fft_engine_compute(&buf, &features);

                // Run anomaly detection
                anomaly_result_t result = anomaly_detect_evaluate(&features);

                if (result.is_anomaly) {
                    // Flag alert for Core 0 to transmit
                    anomaly_detect_flag_alert(&result);
                }

                // Log spectral summary to flash
                data_logger_log_spectrum(&features);

                // Reset buffer (50% overlap for continuous monitoring)
                fft_engine_overlap_reset(&buf);

                fft_count++;
                if (fft_count % 100 == 0) {
                    printf("Core 1: %lu FFTs computed\n", fft_count);
                }
            }
        } else {
            // No data available — brief sleep
            tight_loop_contents();
        }
    }
}