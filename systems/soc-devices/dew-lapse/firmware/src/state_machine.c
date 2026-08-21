/* state_machine.c — top-level measurement cycle coordinator.
 *
 * States: IDLE → RAMP_DOWN → TRACK → VALID → DEFROST → IDLE
 *
 * IDLE       — TEC off, sensors sampled at low rate, waiting for user
 * RAMP_DOWN  — TEC at high cooling power to reach coarse dew-point estimate
 * TRACK      — PID engaged to hold film at setpoint |ΔT|
 * VALID      — film stable for N samples → record dew/frost point
 * DEFROST    — reverse TEC for 2 s to clear mirror
 */
#include "config.h"
#include "state_machine.h"
#include "tec.h"
#include "mirror.h"
#include "pid.h"
#include "dewpoint.h"
#include "sensors.h"
#include "oled.h"
#include "ble.h"
#include "flash_log.h"
#include <stdio.h>

static meas_state_t state = ST_IDLE;
static pid_t pid;
static float ramp_target_c;
static float t_mirror, t_ref, dt_mirror;
static float t_air, rh_ref, p_pa;
static uint16_t co2;
static humidity_t humidity;
static uint32_t state_enter_ms;

extern uint32_t hal_millis(void);

const char *state_name(meas_state_t s)
{
    switch (s) {
    case ST_IDLE:      return "IDLE";
    case ST_RAMP_DOWN: return "RAMP";
    case ST_TRACK:     return "TRACK";
    case ST_VALID:     return "VALID";
    case ST_DEFROST:   return "DEFROST";
    }
    return "?";
}

void sm_init(void)
{
    pid_init(&pid, PID_KP, PID_KI, PID_KD, PID_OUT_MIN, PID_OUT_MAX);
    state = ST_IDLE;
    state_enter_ms = hal_millis();
}

void sm_start_measurement(void)
{
    /* Coarse estimate from SHT45 */
    sht45_read(&t_air, &rh_ref);
    ramp_target_c = coarse_dew_point(t_air, rh_ref) - 2.0f;
    state = ST_RAMP_DOWN;
    state_enter_ms = hal_millis();
    pid_reset(&pid);
    mirror_reset();
}

/* Called at 10 Hz from the controller task. */
void sm_controller_tick(float dt)
{
    /* Read mirror thermistors (20 SPS → downsampled to 10 Hz) */
    ads122_read_mirror(&t_mirror, &t_ref, &dt_mirror);
    tec_sense_update();

    float hot_t = 0.0f;
    /* (read hot-side temp from BME280 on heatsink spreader) */

    switch (state) {
    case ST_IDLE:
        tec_set(0.0f);
        break;

    case ST_RAMP_DOWN: {
        /* Hard cool until T_m within 1 °C of coarse estimate */
        if (t_mirror > ramp_target_c + 1.0f) {
            tec_set(0.7f);
        } else {
            state = ST_TRACK;
            state_enter_ms = hal_millis();
            pid_reset(&pid);
        }
        /* Safety */
        if (!tec_safety_ok(hot_t)) { tec_off(); state = ST_IDLE; }
        break;
    }

    case ST_TRACK: {
        /* PID drives |ΔT| toward film setpoint. The PID's measurement
         * is dt_mirror (negative when film present), setpoint is the
         * negative film setpoint (e.g. -0.10 K). */
        float setpoint;
        int stable = mirror_track(t_mirror, t_ref, &setpoint);
        float pid_out = pid_step(&pid, setpoint, dt_mirror, dt);
        tec_set(pid_out);
        if (stable) {
            state = ST_VALID;
            state_enter_ms = hal_millis();
        }
        if (!tec_safety_ok(hot_t)) { tec_off(); state = ST_IDLE; }
        break;
    }

    case ST_VALID: {
        /* Hold PID for a few seconds, record dew point, then defrost. */
        float setpoint;
        mirror_track(t_mirror, t_ref, &setpoint);
        float pid_out = pid_step(&pid, setpoint, dt_mirror, dt);
        tec_set(pid_out);
        if (hal_millis() - state_enter_ms > 2000) {
            int is_ice = mirror_phase();
            humidity_compute(&humidity, t_mirror, t_air, p_pa, is_ice);
            state = ST_DEFROST;
            state_enter_ms = hal_millis();
        }
        break;
    }

    case ST_DEFROST: {
        tec_defrost_start();
        if (hal_millis() - state_enter_ms > TEC_DEFROST_S * 1000) {
            tec_defrost_stop();
            state = ST_IDLE;
            state_enter_ms = hal_millis();
        }
        break;
    }
    }
}

/* Called at 1 Hz from the application task. */
void sm_application_tick(void)
{
    /* Read auxiliary sensors */
    bme280_read(&t_air, &p_pa, &rh_ref);
    scd41_read(&co2);
    /* (MS5837 provides the precise pressure; BME280 is the backup.) */

    /* Update OLED & BLE */
    oled_update(&humidity, t_mirror, t_air, tec_current(),
                state, state_name(state));
    ble_notify(&humidity, t_mirror, state, (int8_t)(tec_current() * 25));

    /* Log if VALID */
    if (state == ST_VALID || state == ST_TRACK) {
        log_record_t rec = {
            .ts_ms = hal_millis(),
            .dew_c = humidity.dew_c,
            .rh_pct = humidity.rh_pct,
            .ah_gm3 = humidity.ah_gm3,
            .w_gkg = humidity.w_gkg,
            .pressure_pa = p_pa,
            .co2_ppm = co2,
            .mirror_c = t_mirror,
            .tec_i = tec_current(),
            .tec_v = tec_voltage(),
            .phase = humidity.phase,
            .state = (int)state,
        };
        log_append(&rec);
    }
}

meas_state_t sm_state(void) { return state; }