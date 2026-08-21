/*
 * main.c — Thermo Trace pocket DSC main firmware
 *
 * State machine:
 *   IDLE → SET_MASS → SET_RAMP → HEATING → COOLDOWN → MATCH → IDLE
 *
 * The main loop runs at 100 Hz (10 ms cycle). Each iteration:
 *   1. Poll buttons (UI)
 *   2. Read ADS122U04 (temperature, power)
 *   3. Update PID control loops (heater PWM)
 *   4. Update temperature ramp setpoint
 *   5. Compute heat flow (DSC)
 *   6. Check safety (over-temp watchdog)
 *   7. Log to SD card (1 Hz)
 *   8. Stream BLE data (1 Hz)
 *   9. Update display (5 Hz)
 */

#include "stm32g491_conf.h"
#include "ads122.h"
#include "rtd.h"
#include "heater.h"
#include "ramp.h"
#include "dsc.h"
#include "library.h"
#include "display.h"
#include "sd_log.h"
#include "ble_bridge.h"
#include "safety.h"
#include "battery.h"
#include "ui.h"
#include <math.h>
#include <string.h>

/* ---- Clock configuration ---- */
static void clock_init(void) {
    /* Enable HSI16 */
    RCC_CR |= (1U << 8);   /* HSION */
    while (!(RCC_CR & (1U << 10))) ;  /* wait HSIRDY */

    /* Configure PLL: HSI16 / 2 × 85 / 1 = 170 MHz (approx) */
    /* PLLM=2, PLLN=85, PLLR=2, PLLPEN, PLLREN */
    RCC_PLLCFGR = (1U << 0)     /* PLLM = 2 */
                | (85U << 8)    /* PLLN = 85 */
                | (0U << 25)   /* PLLR = 2 */
                | (1U << 24);  /* PLLREN */
    RCC_CR |= (1U << 24);  /* PLLON */
    while (!(RCC_CR & (1U << 25))) ;  /* wait PLLRDY */

    /* Flash latency = 8 wait states for 170 MHz */
    *(volatile uint32_t *)(0x40022000 + 0x00) = 8U;  /* FLASH_ACR */
    /* Use PLLR as system clock */
    RCC_CFGR = (3U << 0);  /* SW = PLLR */
    while (((RCC_CFGR >> 3) & 3U) != 3U) ;  /* wait SWS = PLLR */
}

/* ---- SysTick 1 ms tick ---- */
static volatile uint32_t sys_ms = 0;

static void systick_init(void) {
    SYSTICK_RVR = SYS_CLK_HZ / 1000U - 1U;
    SYSTICK_CVR = 0;
    SYSTICK_CSR = (1U << 2)   /* CLKSOURCE = processor clock */
                | (1U << 1)    /* TICKINT: generate interrupt */
                | (1U << 0);   /* ENABLE */
}

void SysTick_Handler(void) {
    sys_ms++;
}

static uint32_t get_ms(void) { return sys_ms; }
static float get_seconds(void) { return (float)sys_ms / 1000.0f; }

/* ---- Globals ---- */
static pid_t pid_sample;
static pid_t pid_ref;
static ramp_program_t ramp_prog;
static dsc_scan_t scan;
static ads_data_t ads_data;
static ui_state_t state = UI_IDLE;
static float scan_start_time = 0.0f;
static float last_display_update = 0.0f;
static float last_log_time = 0.0f;
static float last_ble_time = 0.0f;
static uint32_t loop_count = 0;
static bool scan_started = false;
static bool scan_complete = false;

/* ---- Forward declarations ---- */
static void state_machine_run(void);
static void start_scan(void);
static void abort_scan(void);
static void finish_scan(void);
static void do_match(void);
static void cooldown_check(void);
static void update_display(void);

int main(void) {
    clock_init();
    systick_init();

    /* Enable GPIO clocks */
    RCC_AHB2ENR |= (1U << 0)  /* GPIOAEN */
                |  (1U << 1)  /* GPIOBEN */
                |  (1U << 2); /* GPIOCEN */

    /* Initialize peripherals */
    display_init();
    ui_init();
    ads_init();
    heater_init();
    safety_init();
    battery_init();
    sd_init();
    ble_init();
    library_init();

    /* PID gains tuned for ~0.5W heater, ~0.5g thermal mass */
    /* Sample PID: aggressive for small thermal mass */
    pid_init(&pid_sample, 0.08f, 0.005f, 0.15f, HEATER_MAX_DUTY, 0.5f);
    pid_init(&pid_ref,    0.08f, 0.005f, 0.15f, HEATER_MAX_DUTY, 0.5f);

    /* Default temperature program: RT→300°C @ 5°C/min, hold 60s */
    ramp_set_default(&ramp_prog, DSC_MAX_TEMP, DSC_RAMP_DEFAULT);

    /* Initialize DSC scan buffer */
    dsc_init(&scan);

    /* Show idle screen */
    display_idle();
    ui_led_green(true);

    /* Main loop: 10 ms cycle (100 Hz) */
    uint32_t last_loop_ms = 0;
    while (1) {
        uint32_t now = get_ms();

        /* Run at ~100 Hz */
        if (now - last_loop_ms >= 10) {
            last_loop_ms = now;
            float dt = 0.01f;  /* 10 ms */

            /* 1. Poll buttons */
            ui_poll();

            /* 2. Read ADS122U04 (all 4 channels) */
            ads_read_all(&ads_data);

            /* 3. Safety check (always first priority) */
            float pan_temp = ads_data.temp[0];  /* sample pan temp */
            if (safety_check(pan_temp)) {
                state = UI_ABORT;
                abort_scan();
                display_message("SAFETY CUTOFF", "Overtemp!", "Reset device");
                while (1) ;  /* halt */
            }

            /* 4. State machine */
            state_machine_run();

            /* 5. Heater PID control (only during HEATING) */
            if (state == UI_HEATING && ramp_prog.active) {
                /* Update ramp setpoint */
                float setpoint = ramp_update(&ramp_prog, dt);

                /* PID for sample heater */
                float duty_s = pid_update(&pid_sample, ads_data.temp[0],
                                           setpoint, dt);
                /* PID for reference heater (same setpoint) */
                float duty_r = pid_update(&pid_ref, ads_data.temp[1],
                                           setpoint, dt);

                heater_set_pwm(0, duty_s);
                heater_set_pwm(1, duty_r);

                /* Compute heat flow */
                float heat_flow_mw = 0.0f;
                dsc_compute_heat_flow(
                    heater_get_power(0), heater_get_power(1),
                    ads_data.v_supply, duty_s, duty_r,
                    &heat_flow_mw);

                /* Add data point to DSC buffer */
                float t = get_seconds() - scan_start_time;
                dsc_add_point(&scan, pan_temp, heat_flow_mw, t);

                /* Log to SD every 1 second */
                if (t - last_log_time >= 1.0f) {
                    sd_log_point(pan_temp, heat_flow_mw, t, setpoint);
                    last_log_time = t;
                }

                /* BLE stream every 1 second */
                if (t - last_ble_time >= 1.0f) {
                    ble_send_data(pan_temp, heat_flow_mw, t, setpoint);
                    last_ble_time = t;
                }

                /* Update display every 200 ms (5 Hz) */
                if (t - last_display_update >= 0.2f) {
                    display_status(pan_temp, setpoint, heat_flow_mw,
                                    ui_get_ramp(), battery_percent());
                    last_display_update = t;
                }

                /* Check if ramp program is complete */
                if (ramp_prog.complete) {
                    finish_scan();
                }
            }

            /* 6. Cooldown monitoring */
            if (state == UI_COOLDOWN) {
                cooldown_check();
            }

            /* 7. Button handling for state transitions */
            if (ui_button_a()) {
                switch (state) {
                case UI_IDLE:
                    state = UI_SET_MASS;
                    display_message("SET MASS (mg)", "B: +1  C: -1", "A: confirm");
                    break;
                case UI_SET_MASS:
                    state = UI_SET_RAMP;
                    display_message("SET RAMP C/min", "B: +1  C: -1", "A: confirm");
                    break;
                case UI_SET_RAMP:
                    start_scan();
                    break;
                case UI_HEATING:
                    abort_scan();
                    break;
                case UI_MATCH:
                    dsc_clear(&scan);
                    state = UI_IDLE;
                    display_idle();
                    break;
                default:
                    break;
                }
            }

            if (ui_button_b()) {
                if (state == UI_SET_MASS) {
                    ui_set_mass(ui_get_mass() + 1.0f);
                } else if (state == UI_SET_RAMP) {
                    ui_set_ramp(ui_get_ramp() + 1.0f);
                }
            }

            if (ui_button_c()) {
                if (state == UI_SET_MASS) {
                    if (ui_get_mass() > 1.0f) ui_set_mass(ui_get_mass() - 1.0f);
                } else if (state == UI_SET_RAMP) {
                    if (ui_get_ramp() > 1.0f) ui_set_ramp(ui_get_ramp() - 1.0f);
                }
            }

            loop_count++;
        }
    }
}

static void start_scan(void) {
    state = UI_HEATING;
    ui_led_red(true);
    ui_led_green(false);

    /* Set sample mass */
    scan.sample_mass = ui_get_mass();
    scan.count = 0;
    scan.num_peaks = 0;
    scan.num_transitions = 0;

    /* Configure ramp program */
    ramp_set_default(&ramp_prog, DSC_MAX_TEMP, ui_get_ramp());

    /* Read ambient temperature as starting point */
    float start_temp = ads_data.temp[0];
    if (start_temp < 1.0f) start_temp = TEMP_AMBIENT_C;

    ramp_start(&ramp_prog, start_temp);
    pid_reset(&pid_sample);
    pid_reset(&pid_ref);

    /* Enable heaters */
    heater_enable(true);
    safety_clear();

    /* Open SD logging session */
    sd_mount();
    sd_open_session(0);

    scan_start_time = get_seconds();
    last_log_time = 0.0f;
    last_ble_time = 0.0f;
    last_display_update = 0.0f;
    scan_started = true;
    scan_complete = false;

    display_message("HEATING", "Scan in progress", "A: abort");
}

static void abort_scan(void) {
    state = UI_ABORT;
    heater_off();
    ramp_abort(&ramp_prog);
    ui_led_red(false);
    sd_close_session();
    ble_send_done();
    display_message("ABORTED", "Heaters off", "A: return");
}

static void finish_scan(void) {
    /* Turn off heaters */
    heater_off();
    ui_led_red(false);

    /* Close SD log */
    sd_close_session();

    /* Detect peaks and transitions */
    dsc_detect_peaks(&scan);

    /* Match against library */
    do_match();

    state = UI_MATCH;
    scan_complete = true;

    /* Start cooldown */
    state = UI_COOLDOWN;
    display_message("SCAN COMPLETE", "Cooling down...", "Wait < 50C");
}

static void do_match(void) {
    /* Extract features from scan peaks */
    float features[NUM_FEATURES] = {-999.0f, -999.0f, -999.0f, -999.0f, -999.0f};

    /* Tg from transitions */
    if (scan.num_transitions > 0) {
        features[0] = scan.transitions[0].peak_temp;
    }

    /* Tm and ΔH_melt from first endothermic peak */
    for (uint8_t i = 0; i < scan.num_peaks; i++) {
        if (scan.peaks[i].type == PEAK_ENDOTHERMIC) {
            features[1] = scan.peaks[i].peak_temp;
            features[2] = scan.peaks[i].enthalpy;
            break;
        }
    }

    /* Tc and ΔH_cryst from first exothermic peak */
    for (uint8_t i = 0; i < scan.num_peaks; i++) {
        if (scan.peaks[i].type == PEAK_EXOTHERMIC) {
            features[3] = scan.peaks[i].peak_temp;
            features[4] = scan.peaks[i].enthalpy;
            break;
        }
    }

    /* k-NN match */
    dsc_match_t matches[MAX_MATCHES];
    uint8_t num_matches = 0;
    library_match(features, matches, &num_matches);

    /* Display best match */
    if (num_matches > 0) {
        display_match(matches[0].name, matches[0].confidence);
        ble_send_match(matches[0].name, matches[0].confidence);
    } else {
        display_message("NO MATCH", "Unknown material", "A: retry");
    }

    /* Send all match data over BLE */
    for (uint8_t i = 0; i < num_matches; i++) {
        ble_send_match(matches[i].name, matches[i].confidence);
    }
    ble_send_done();
}

static void cooldown_check(void) {
    float temp = ads_data.temp[0];
    if (temp <= TEMP_COOLDOWN_C) {
        state = UI_MATCH;
        ui_led_green(true);
        display_message("READY", "A: new scan", "B: view match");
    }
}

static void state_machine_run(void) {
    /* Additional state machine logic can be added here */
    /* Currently handled in main loop */
}

static void update_display(void) {
    /* Display update is handled in main loop based on state */
}

/* ---- Hard fault handler: cut heaters immediately ---- */
void HardFault_Handler(void) {
    heater_off();
    GPIO_CLR(HEATER_EN_PORT, HEATER_EN_PIN);
    while (1) ;
}