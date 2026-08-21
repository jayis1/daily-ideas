/*
 * gossamer-spin / firmware / main.h
 * Global types, constants, and declarations for the STM32G474 core.
 */
#ifndef GOSSAMER_SPIN_MAIN_H
#define GOSSAMER_SPIN_MAIN_H

#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* ---- System constants ---- */
#define SYS_CLK_HZ        170000000

/* ---- HV supply ---- */
#define HV_MAX_KV         30.0f         /* max output voltage */
#define HV_MAX_UA         33.0f         /* max output current (safety-limited) */
#define HV_PID_RATE_HZ    1000          /* PID loop at 1 kHz */
#define HV_BOOST_PWM_HZ   50000         /* flyback at 50 kHz */
#define HV_BLEEDER_R      100.0e6f      /* 100 MΩ bleeder */
#define HV_SERIES_R       910.0e6f      /* 910 MΩ current limit */
#define HV_DIVIDER_RATIO  1000.0f       /* 1000:1 voltage divider */

/* ---- Jet current monitoring ---- */
#define TIA_RFB           100.0e6f      /* 100 MΩ transimpedance */
#define TIA_DIVIDER       10.0f         /* 1/10 voltage divider at TIA out */
#define I_SAFE_UA         10.0f         /* hardware comparator cutoff threshold */
#define JET_SAMPLE_RATE   100           /* ADC samples per second */
#define JET_WINDOW_S      5             /* 5-second rolling window */
#define JET_WINDOW_N      (JET_SAMPLE_RATE * JET_WINDOW_S) /* 500 samples */

/* ---- Syringe pump ---- */
#define SYRINGE_STEPS_PER_REV   200
#define SYRINGE_MICROSTEPS      16
#define SYRINGE_LEAD_MM         0.35f    /* M4×0.35 leadscrew */
#define SYRINGE_DEFAULT_R_MM    6.0f     /* 5 mL syringe, 12 mm dia */
#define SYRINGE_MIN_MLH         0.1f
#define SYRINGE_MAX_MLH         10.0f

/* ---- Collector drum ---- */
#define DRUM_STEPS_PER_REV      200
#define DRUM_MICROSTEPS         16
#define DRUM_BELT_RATIO         1.0f
#define DRUM_MIN_RPM            100
#define DRUM_MAX_RPM            3000

/* ---- Process states (jet current classifier) ---- */
typedef enum {
    JET_IDLE = 0,
    JET_STABLE,
    JET_INTERRUPTED,
    JET_UNSTABLE,
    JET_DRIPPING,
} jet_state_t;

/* ---- System states ---- */
typedef enum {
    ST_BOOT = 0,
    ST_IDLE,         /* powered, no HV, steppers off */
    ST_READY,        /* HV off, steppers homed, recipe loaded */
    ST_RUNNING,      /* full power, electrospinning */
    ST_SAFE,         /* safety trip, everything off */
    ST_ERROR,
} sys_state_t;

/* ---- Recipe ---- */
#define NUM_RECIPES      8
#define MAX_RECIPE_NAME  24

typedef struct {
    char     name[MAX_RECIPE_NAME];
    float    voltage_kv;
    float    flow_mlh;
    float    drum_rpm;
    float    distance_cm;
    float    target_rh_min;
    float    target_rh_max;
    float    target_temp_c;
    uint32_t duration_s;
} recipe_t;

/* ---- Process data (current readings) ---- */
typedef struct {
    float    voltage_kv;        /* measured HV */
    float    current_na;        /* jet current */
    float    flow_mlh;          /* current flow rate */
    float    drum_rpm;          /* current drum speed */
    float    temp_c;            /* chamber temperature */
    float    rh_pct;            /* chamber humidity */
    jet_state_t jet_state;      /* classified jet state */
    float    jet_sigma_na;      /* rolling std dev of jet current */
    uint32_t elapsed_s;         /* elapsed seconds in run */
    uint32_t unix_ts;           /* timestamp (from ESP32/GPS if available) */
} process_t;

/* ---- Run context ---- */
typedef struct {
    sys_state_t  state;
    recipe_t     recipe;
    int          recipe_idx;
    process_t    proc;
    float        battery_mv;
    uint32_t     run_start_ms;
    bool         safety_tripped;
    uint8_t      safety_source;  /* 0=none, 1=door, 2=tilt, 3=comparator, 4=wdg */
} spin_ctx_t;

/* ---- Safety sources ---- */
#define SAF_NONE       0
#define SAF_DOOR       1
#define SAF_TILT       2
#define SAF_CURRENT    3
#define SAF_WATCHDOG   4

/* ---- Class declarations ---- */
extern const char *const JET_STATE_NAMES[5];
extern const char *const RECIPE_NAMES[NUM_RECIPES];

/* ---- Module functions ---- */
void     hv_supply_init(void);
void     hv_set_target(float kv);
void     hv_enable(bool on);
float    hv_read_voltage(void);       /* measured kV */
void     hv_pid_update(void);          /* called at 1 kHz */

void     syringe_pump_init(void);
void     syringe_set_flow(float mlh);
void     syringe_start(void);
void     syringe_stop(void);
bool     syringe_empty(void);

void     collector_init(void);
void     collector_set_rpm(float rpm);
void     collector_start(void);
void     collector_stop(void);

void     jet_current_init(void);
float    jet_current_read(void);      /* nA, averaged */
void     jet_current_update(float *out_na, float *out_sigma, jet_state_t *out_state);

void     safety_init(void);
bool     safety_check(void);          /* returns false if tripped */
uint8_t  safety_get_source(void);
void     safety_reset(void);

void     env_monitor_init(void);
void     env_read(float *temp_c, float *rh_pct);

void     oled_init(void);
void     oled_update(spin_ctx_t *ctx);

void     sd_log_init(void);
void     sd_log_write(process_t *p);
void     sd_log_close(void);

void     uart_link_init(void);
void     uart_link_poll(void);
void     uart_link_send(process_t *p);

void     recipe_init(void);
void     recipe_load(int idx, recipe_t *r);

#endif /* GOSSAMER_SPIN_MAIN_H */