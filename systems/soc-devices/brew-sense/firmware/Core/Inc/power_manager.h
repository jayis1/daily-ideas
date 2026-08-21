/**
 * power_manager.h — Ultra-Low-Power Manager for Brew Sense
 * 
 * Manages STM32L476 power modes, duty cycling, and battery monitoring.
 * Target: 30 days on 2× AAA alkaline batteries.
 */

#ifndef POWER_MANAGER_H
#define POWER_MANAGER_H

#include <stdint.h>
#include <stdbool.h>

/* Power modes */
typedef enum {
    POWER_MODE_RUN       = 0,  /* Full speed, all peripherals active */
    POWER_MODE_LOW_RUN   = 1,  /* 80MHz, sensors active, display off */
    POWER_MODE_SLEEP     = 2,  /* CPU halted, peripherals on, fast wake */
    POWER_MODE_STOP      = 3,  /* Deep sleep, RTC only, 8µA quiescent */
    POWER_MODE_STANDBY   = 4,  /* Deepest sleep, only backup domain alive */
} power_mode_t;

/* Configuration */
typedef struct {
    uint32_t sample_interval_sec;    /* Seconds between sensor reads (default: 60) */
    uint32_t wifi_push_interval_sec; /* Seconds between Wi-Fi pushes (default: 300) */
    uint32_t display_timeout_sec;    /* Seconds before OLED turns off (default: 30) */
    bool enable_wifi;                /* Enable Wi-Fi uplink (uses more power) */
    bool enable_display;             /* Enable OLED display */
    bool enable_buzzer;              /* Enable alarm buzzer */
    float low_battery_threshold;     /* Battery voltage threshold for alerts (default: 2.2V) */
} power_config_t;

/**
 * Initialize power manager.
 * Configures RTC, wake-up timers, and battery ADC.
 * @param config Configuration (NULL for defaults)
 */
void power_manager_init(const power_config_t *config);

/**
 * Enter low-power mode until next sample time.
 * Wakes on RTC alarm or external interrupt.
 * @param mode Power mode to enter
 */
void power_manager_sleep(power_mode_t mode);

/**
 * Wake from low-power mode and restore clocks.
 * Call this after waking from STOP/STANDBY.
 */
void power_manager_wake(void);

/**
 * Get current battery voltage.
 * @return Battery voltage in V (0.0-6.0)
 */
float power_manager_get_battery_voltage(void);

/**
 * Get estimated battery percentage.
 * Based on voltage discharge curve for alkaline AAA.
 * @return Percentage (0-100)
 */
uint8_t power_manager_get_battery_percent(void);

/**
 * Check if USB power is connected.
 * @return true if VBUS detected
 */
bool power_manager_is_usb_connected(void);

/**
 * Set the sample interval for RTC wake-up.
 * @param seconds Interval in seconds (1-3600)
 */
void power_manager_set_sample_interval(uint32_t seconds);

/**
 * Get the current power mode.
 * @return Current power_mode_t
 */
power_mode_t power_manager_get_mode(void);

/**
 * Enable or disable the OLED display.
 * @param enable true to turn on, false to turn off
 */
void power_manager_set_display(bool enable);

/**
 * Enter the lowest power state (STANDBY) until button press.
 * Used for long-term storage or shipping.
 */
void power_manager_shutdown(void);

#endif /* POWER_MANAGER_H */