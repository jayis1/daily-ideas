/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * main.c — Application entry point, scheduler loop, sleep management
 *
 * The firmware uses a lightweight cooperative scheduler (no FreeRTOS —
 * the duty cycle is dominated by STOP-mode sleep between measurements).
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "probe.h"
#include "heat_ratio.h"
#include "sensors.h"
#include "lorawan.h"
#include "power.h"
#include "storage.h"
#include <math.h>
#include <string.h>

/* ---- Platform HAL stubs (implemented in port / Cube-generated code) ---- */
extern void hal_init(void);
extern void gpio_write(int pin, int val);
extern int  gpio_read(int pin);
extern void delay_ms(uint32_t ms);
extern uint32_t rtc_get_time_s(void);
extern void rtc_set_wakeup(uint32_t seconds);
extern void enter_stop_mode(void);
extern void wake_from_stop(void);
extern uint16_t adc_read(int channel);
extern int  i2c_write(uint8_t addr, const uint8_t *data, uint8_t len);
extern int  i2c_read(uint8_t addr, uint8_t *data, uint8_t len);
extern int  i2c_write_reg(uint8_t addr, uint8_t reg, uint8_t *data, uint8_t len);
extern int  i2c_read_reg(uint8_t addr, uint8_t reg, uint8_t *data, uint8_t len);
extern int  onewire_reset(void);
extern void onewire_write_byte(uint8_t byte);
extern uint8_t onewire_read_byte(void);
extern void uart2_send(const uint8_t *buf, uint16_t len);
extern uint16_t uart2_recv(uint8_t *buf, uint16_t maxlen, uint32_t timeout_ms);
extern int  radio_init(uint8_t region);
extern int  radio_join_otaa(const uint8_t *appeui, const uint8_t *appkey,
                             const uint8_t *deveui, uint32_t timeout_ms);
extern int  radio_send(uint8_t port, const uint8_t *data, uint8_t len,
                       uint8_t confirmed);
extern int  radio_recv(uint8_t *port, uint8_t *data, uint8_t maxlen);
extern int  radio_is_joined(void);
extern int  flash_write(uint32_t addr, const uint8_t *data, uint16_t len);
extern int  flash_read(uint32_t addr, uint8_t *data, uint16_t len);
extern int  flash_erase_sector(uint32_t sector_addr);

/* ---- Scheduler state ---- */
static uint32_t last_measurement_s = 0;
static uint32_t last_sensor_poll_s = 0;
static uint32_t last_uplink_s = 0;
static uint32_t measurement_count = 0;
static uint16_t measurement_interval_s = MEASUREMENT_INTERVAL_S;

/* Daily transpiration accumulator (reset at midnight) */
static float daily_transpiration_L = 0.0f;
static float last_flow_Lh = 0.0f;
static uint32_t last_flow_time_s = 0;

/* Force-trigger flags (set by downlink or button) */
static int force_measurement_flag = 0;
static int force_zero_cal_flag = 0;

/* Flag set by scheduler_set_interval() */
void scheduler_set_interval(uint16_t minutes)
{
    measurement_interval_s = (uint32_t)minutes * 60U;
    storage_set_interval(minutes);
}

void scheduler_force_measurement(void) { force_measurement_flag = 1; }
void scheduler_trigger_zero_cal(void) { force_zero_cal_flag = 1; }

/* ---- Status LED helpers ---- */
static void led_set(int pin, int on)
{
    gpio_write(pin, on ? 1 : 0);
}

static void led_blink(int pin, int ms)
{
    led_set(pin, 1);
    delay_ms(ms);
    led_set(pin, 0);
}

/* ---- Measurement cycle ---- */

static void run_measurement(void)
{
    /* Check if battery can support a heat pulse */
    if (!power_can_fire_heater()) {
        led_blink(PIN_LED_RED, 100);
        return;
    }

    /* Initialize probe (power-gate ADC on) */
    probe_init();

    /* Run health check */
    int health = probe_check_health();
    if (health != PROBE_OK) {
        led_blink(PIN_LED_RED, 200);
        /* Send alert if heater fault */
        if (health == PROBE_HEATER_FAULT) {
            lorawan_send_alert(ALERT_HEATER_FAULT, 0, 0, 0, 0);
        }
        probe_power_down();
        return;
    }

    /* Run heat-pulse cycle */
    probe_result_t result;
    if (probe_run_cycle(&result) != 0) {
        led_blink(PIN_LED_RED, 200);
        probe_power_down();
        return;
    }

    /* Compute sap-flux velocity */
    float v_sap = heat_ratio_compute_velocity(&result);
    if (isnan(v_sap))
        v_sap = 0.0f;

    /* Convert to whole-tree flow rate (L/h) */
    float flow_Lh = heat_ratio_velocity_to_flow(v_sap);

    /* Accumulate daily transpiration (trapezoidal) */
    uint32_t now_s = rtc_get_time_s();
    if (last_flow_time_s > 0) {
        float dt_h = (float)(now_s - last_flow_time_s) / 3600.0f;
        daily_transpiration_L += (flow_Lh + last_flow_Lh) * 0.5f * dt_h;
    }
    last_flow_Lh = flow_Lh;
    last_flow_time_s = now_s;

    /* Read environmental sensors */
    sensor_data_t sensors;
    sensors_read_all(&sensors);

    /* Log to flash */
    log_entry_t log;
    log.timestamp_min = (uint16_t)(now_s / 60);
    log.sap_flux_cmh = v_sap;
    log.sapwood_temp = sensors.sapwood_temp_c;
    log.air_temp = sensors.air_temp_c;
    log.humidity = sensors.rh_pct;
    log.battery_pct = (uint8_t)sensors.battery_pct;
    log.flags = 0;
    storage_log_add(&log);

    /* Drought-stress detection (check if midday) */
    uint32_t hour = (now_s / 3600) % 24;
    int drought = 0;
    if (hour >= 11 && hour <= 15) {
        drought = heat_ratio_detect_drought_stress(v_sap);
        if (drought) {
            float baseline = heat_ratio_predawn_baseline();
            uint8_t ratio = (uint8_t)((baseline > 0) ?
                            (v_sap / baseline * 100.0f) : 0);
            lorawan_send_alert(ALERT_DROUGHT_STRESS, v_sap, baseline, v_sap, ratio);
        }
    }

    /* Predawn zero-flow calibration check */
    if (hour == ZERO_CAL_PREDAWN_HOUR && !heat_ratio_is_zero_cal_valid()) {
        /* Collect zero-cal data over the next hour */
        /* (In production, a separate task accumulates; here we just
         *  record one point — the full calibration runs over a week) */
        heat_ratio_record_predawn(v_sap);
    }

    /* Check for midnight → reset daily transpiration */
    if (hour == 0 && (now_s % 3600) < (uint32_t)measurement_interval_s) {
        daily_transpiration_L = 0.0f;
    }

    measurement_count++;

    /* Power down probe between cycles */
    probe_power_down();

    led_blink(PIN_LED_GREEN, 50);
}

/* ---- Uplink cycle ---- */

static void run_uplink(void)
{
    if (!lorawan_is_joined())
        return;

    /* Read sensors for the report */
    sensor_data_t sensors;
    sensors_read_all(&sensors);

    /* Get the latest sap-flow reading from the log */
    /* (In production, we cache the last measurement; here we use 0 as
     *  placeholder if no measurement yet this cycle) */
    report_data_t rpt;
    memset(&rpt, 0, sizeof(rpt));
    rpt.sap_flux_cmh = last_flow_Lh > 0 ?
                        (last_flow_Lh / heat_ratio_get_sapwood_area() * 1000.0f) : 0;
    rpt.daily_transpiration_L = daily_transpiration_L;
    rpt.sapwood_temp = sensors.sapwood_temp_c;
    rpt.air_temp = sensors.air_temp_c;
    rpt.humidity = sensors.rh_pct;
    rpt.light_lux = sensors.light_lux;
    rpt.vpd_kpa = sensors.vpd_kpa;
    rpt.battery_pct = sensors.battery_pct;
    rpt.heater_ok = 1;
    rpt.adc_ok = 1;
    rpt.therm1_ok = 1;
    rpt.therm2_ok = 1;
    rpt.zero_cal_ok = heat_ratio_is_zero_cal_valid();
    rpt.drought_stress = 0;
    rpt.heater_fault = 0;
    rpt.low_battery = power_is_low();
    rpt.measurement_count = measurement_count;

    lorawan_send_report(&rpt);

    /* Check for downlink config commands */
    lorawan_check_downlink();
}

/* ---- Provisioning (via program button + serial) ---- */

static void handle_provisioning(void)
{
    /* When the PROG button is held for 3 s, enter provisioning mode:
     * read LoRaWAN credentials from serial console, store to flash.
     * (Simplified — production code uses a serial menu)
     */
    uint8_t deveui[8], appeui[8], appkey[16];
    extern int serial_read_credentials(uint8_t *deveui, uint8_t *appeui,
                                        uint8_t *appkey);
    if (serial_read_credentials(deveui, appeui, appkey) == 0) {
        storage_set_credentials(deveui, appeui, appkey);
        led_blink(PIN_LED_GREEN, 500);
    }
}

/* ---- Button handling ---- */

static void check_buttons(void)
{
    static int prog_held_s = 0;

    if (gpio_read(PIN_BTN_PROG) == 0) {  /* active low */
        prog_held_s++;
        if (prog_held_s >= 3) {
            handle_provisioning();
            prog_held_s = 0;
        }
    } else {
        prog_held_s = 0;
    }

    if (gpio_read(PIN_BTN_MODE) == 0) {
        /* Force an immediate measurement */
        force_measurement_flag = 1;
    }
}

/* ---- Main scheduler loop ---- */

int main(void)
{
    /* Hardware init */
    hal_init();

    /* Initialize storage (load config from flash) */
    storage_init();

    /* Apply stored config to computation modules */
    heat_ratio_set_sapwood_area(storage_get_sapwood_area());
    heat_ratio_set_wound_factor(storage_get_wound_factor());
    heat_ratio_set_k_xylem(storage_get_k_xylem());

    /* Initialize subsystems */
    power_init();
    tsl2591_init();
    lorawan_init();

    /* Attempt LoRaWAN join */
    led_blink(PIN_LED_GREEN, 200);
    if (lorawan_join() == 0) {
        led_blink(PIN_LED_GREEN, 100);
        delay_ms(100);
        led_blink(PIN_LED_GREEN, 100);
    } else {
        led_blink(PIN_LED_RED, 500);
        /* Continue without LoRa — will retry on next uplink cycle */
    }

    /* Main loop */
    while (1) {
        uint32_t now = rtc_get_time_s();

        /* Check buttons */
        check_buttons();

        /* Measurement task */
        if (force_measurement_flag ||
            (now - last_measurement_s) >= measurement_interval_s) {
            force_measurement_flag = 0;
            run_measurement();
            last_measurement_s = now;
        }

        /* Sensor polling task (every 60 s) */
        if ((now - last_sensor_poll_s) >= (SENSOR_POLL_MS / 1000)) {
            power_update();
            last_sensor_poll_s = now;
        }

        /* Uplink task (every 15 min) */
        if ((now - last_uplink_s) >= LORA_UPLINK_INTERVAL_S) {
            run_uplink();
            last_uplink_s = now;
        }

        /* Check if we should enter deep sleep (low battery) */
        if (power_should_deep_sleep()) {
            led_blink(PIN_LED_RED, 1000);
            power_enter_deep_sleep();
            /* On wake, loop continues */
            now = rtc_get_time_s();
            last_measurement_s = now;
            last_sensor_poll_s = now;
            continue;
        }

        /* Normal sleep: enter STOP mode until next event (RTC or button) */
        /* Calculate sleep time until next measurement */
        uint32_t next_meas = last_measurement_s + measurement_interval_s;
        uint32_t sleep_s = (next_meas > now) ? (next_meas - now) : 1;
        if (sleep_s > 60) sleep_s = 60;  /* wake every 60s to check buttons */

        rtc_set_wakeup(sleep_s);
        enter_stop_mode();
        wake_from_stop();
    }

    return 0;
}