/*
 * hall-puck / firmware / Core / Src / measurement.c
 * Van der Pauw + Hall effect measurement engine
 *
 * Van der Pauw method (ASTM F76):
 *   exp(-π·R_A/R_s) + exp(-π·R_B/R_s) = 1
 *   Solved iteratively (Newton-Raphson) for sheet resistance R_s
 *
 * Hall effect (4-point field-reversal):
 *   V_H = (V_{+I,+B} - V_{-I,+B} - V_{+I,-B} + V_{-I,-B}) / 4
 *   R_H = V_H · d / (I · B)
 *   n = 1/(|R_H| · e)
 *   μ = |R_H| / R_s
 *
 * MIT License.
 */
#include "measurement.h"
#include "ads122u04.h"
#include "current_source.h"
#include "vdp_switch.h"
#include "magnet.h"
#include "oled_display.h"
#include "sd_logger.h"
#include "esp32_link.h"
#include "flash_store.h"
#include "database.h"
#include "main.h"
#include <math.h>
#include <string.h>

#define PI  3.14159265359f
#define LN2 0.69314718056f

/* Measurement state */
static volatile meas_state_t state = MEAS_IDLE;
static meas_result_t result;
static meas_point_t points[MEAS_MAX_POINTS];
static volatile int point_count = 0;
static meas_params_t current_params;
static float calibration_b = MAGNETIC_FIELD_T;

/* ---- Van der Pauw iterative solver ---- */
float vdp_solve_rs(float ra, float rb)
{
    /* Solve: exp(-π·R_A/R_s) + exp(-π·R_B/R_s) = 1
     * Newton-Raphson iteration on R_s.
     * Initial guess: R_s = (π / ln(2)) · (R_A + R_B) / 2
     */
    if (ra <= 0 || rb <= 0) return 0.0f;

    float rs = (PI / LN2) * (ra + rb) / 2.0f;
    if (rs <= 0) rs = 1.0f;

    for (int i = 0; i < 50; i++) {
        float x = -PI * ra / rs;
        float y = -PI * rb / rs;
        /* Guard against overflow */
        if (x < -50.0f) x = -50.0f;
        if (y < -50.0f) y = -50.0f;

        float f = expf(x) + expf(y) - 1.0f;
        float df = (PI * ra / (rs * rs)) * expf(x)
                 + (PI * rb / (rs * rs)) * expf(y);

        if (fabsf(df) < 1e-15f) break;

        float delta = f / df;
        rs -= delta;

        if (rs < 0.001f) rs = 0.001f;
        if (fabsf(delta) < rs * 1e-7f) break;
    }

    return rs;
}

/* ---- Hall coefficient computation ---- */
float hall_compute_rh(float v_fwd_bp, float v_rev_bp,
                      float v_fwd_bm, float v_rev_bm,
                      float current_ma, float b_field_t,
                      float thickness_mm)
{
    /* V_H in µV, I in mA, B in T, d in mm
     * V_H = (V_{+I,+B} - V_{-I,+B} - V_{+I,-B} + V_{-I,-B}) / 4
     * R_H = V_H · d / (I · B)
     * Units: µV · mm / (mA · T) → need conversion to cm³/C
     *
     * V_H [V] = V_H_uV × 1e-6
     * d [cm]  = d_mm × 0.1
     * I [A]   = I_mA × 1e-3
     * R_H [cm³/C] = (V_H × 1e-6 × d_mm × 0.1) / (I_mA × 1e-3 × B_T)
     *             = (V_H_uV × d_mm × 0.1) / (I_mA × B_T × 1e3)
     *             = V_H_uV × d_mm / (I_mA × B_T × 1e4)
     */
    if (current_ma == 0 || b_field_t == 0 || thickness_mm == 0)
        return 0.0f;

    float v_h_uv = (v_fwd_bp - v_rev_bp - v_fwd_bm + v_rev_bm) / 4.0f;
    float rh = (v_h_uv * thickness_mm) / (current_ma * b_field_t * 1e4f);
    return rh;  /* cm³/C */
}

float hall_compute_conc(float rh)
{
    if (fabsf(rh) < 1e-20f) return 0.0f;
    return 1.0f / (fabsf(rh) * ELECTRON_CHARGE);  /* cm⁻³ */
}

float hall_compute_mobility(float rh, float rs)
{
    if (rs <= 0) return 0.0f;
    /* μ = |R_H| / R_s
     * R_H in cm³/C, R_s in Ω/□ → μ in cm²/V·s
     */
    return fabsf(rh) / rs;
}

/* ---- Measurement control ---- */
void measurement_init(void)
{
    state = MEAS_IDLE;
    point_count = 0;
    memset(&result, 0, sizeof(result));
    memset(points, 0, sizeof(points));
    memset(&current_params, 0, sizeof(current_params));
    current_params.current_ma = 1.0f;
    current_params.sample_thickness_mm = 0.5f;
    current_params.mode = MODE_SINGLE;
}

void measurement_start(const meas_params_t *params)
{
    if (state != MEAS_IDLE && state != MEAS_DONE && state != MEAS_ERROR) {
        return;
    }

    current_params = *params;
    point_count = 0;
    memset(&result, 0, sizeof(result));
    memset(points, 0, sizeof(points));
    state = MEAS_CONTACT_CHECK;
}

void measurement_cancel(void)
{
    current_source_disable();
    vdp_switch_all_open();
    magnet_park();
    state = MEAS_IDLE;
}

meas_state_t measurement_get_state(void) { return state; }
const meas_result_t *measurement_get_result(void) { return &result; }

const meas_point_t *measurement_get_points(int *count)
{
    *count = point_count;
    return points;
}

void measurement_set_thickness(float mm)
{
    if (mm > 0 && mm < 10.0f)
        current_params.sample_thickness_mm = mm;
}

float measurement_get_thickness(void)
{
    return current_params.sample_thickness_mm;
}

void measurement_set_current(float ma)
{
    if (ma >= I_MIN_UA / 1000.0f && ma <= I_MAX_MA)
        current_params.current_ma = ma;
}

float measurement_get_current(void)
{
    return current_params.current_ma;
}

void measurement_set_b_calibration(float b_t)
{
    calibration_b = b_t;
}

/* ---- Single voltage measurement with current reversal ----
 * Measures voltage with forward and reverse current,
 * returns average |V| to cancel thermoelectric offsets.
 * Also stores raw values in points[].
 */
static float measure_voltage_with_reversal(vdp_config_t fwd, vdp_config_t rev,
                                            float current_ma, float b_field_t,
                                            float temp_c)
{
    float v_fwd_uv = 0, v_rev_uv = 0;

    /* Forward current */
    vdp_switch_set_config(fwd);
    current_source_set(current_ma);
    current_source_enable();
    delay_ms(10);  /* settle */

    /* Auto-range INA333 */
    ads122u04_read_voltage_uv(&v_fwd_uv);
    uint8_t gain = ads122u04_auto_range(v_fwd_uv);
    ads122u04_read_voltage_uv(&v_fwd_uv);

    /* Store point */
    if (point_count < MEAS_MAX_POINTS) {
        points[point_count].config = fwd;
        points[point_count].current_ma = current_ma;
        points[point_count].voltage_uv = v_fwd_uv;
        points[point_count].b_field_t = b_field_t;
        points[point_count].temperature_c = temp_c;
        point_count++;
    }

    /* Reverse current */
    vdp_switch_set_config(rev);
    delay_ms(10);
    ads122u04_read_voltage_uv(&v_rev_uv);

    if (point_count < MEAS_MAX_POINTS) {
        points[point_count].config = rev;
        points[point_count].current_ma = -current_ma;
        points[point_count].voltage_uv = v_rev_uv;
        points[point_count].b_field_t = b_field_t;
        points[point_count].temperature_c = temp_c;
        point_count++;
    }

    current_source_disable();

    /* Average (V_fwd - V_rev) / 2 cancels offset */
    return (v_fwd_uv - v_rev_uv) / 2.0f;
}

/* ---- Read sample temperature (DS18B20 via 1-wire) ---- */
static float read_temperature(void)
{
    /* Simplified: would call ds18b20_read() */
    return 24.3f;  /* placeholder — real impl reads DS18B20 */
}

/* ---- Main measurement task ---- */
void measurement_task(void)
{
    static int contact_check_idx = 0;

    switch (state) {
    case MEAS_IDLE:
    case MEAS_DONE:
    case MEAS_ERROR:
        break;

    case MEAS_CONTACT_CHECK:
    {
        /* Check all 4 contacts have valid connection */
        bool all_ok = true;
        for (int c = 0; c < 4; c++) {
            bool ok = vdp_switch_check_contact(c);
            oled_show_contact_check(c + 1, ok);
            if (!ok) all_ok = false;
        }

        if (!all_ok) {
            result.status = 1;  /* error */
            result.final_state = MEAS_ERROR;
            state = MEAS_ERROR;
            break;
        }

        /* Auto-zero the INA333 */
        vdp_switch_set_config(SHORT_ZERO);
        delay_ms(50);
        float offset_uv;
        ads122u04_read_voltage_uv(&offset_uv);
        flash_store_set_voltage_offset(offset_uv);

        state = MEAS_VDP;
        break;
    }

    case MEAS_VDP:
    {
        float current = current_params.current_ma;
        float temp = read_temperature();
        float b_field = 0.0f;  /* no field for VdP */

        /* R_A: I→1,2; V→3,4 (forward + reverse) */
        float v_ra = measure_voltage_with_reversal(
            VDP_RA_FWD, VDP_RA_REV, current, b_field, temp);

        /* R_A = V / I  (V in µV, I in mA → R in Ω: µV/mA = Ω × 1e-6/1e-3 = Ω × 1e-3)
         * R = V[V] / I[A] = (V_uV × 1e-6) / (I_mA × 1e-3) = V_uV / (I_mA × 1e3)
         * But V_ra already = (V_fwd - V_rev)/2 which gives the true V drop.
         * R_A = |V_ra_uV| / (I_mA × 1000)  [in Ohms]  -- wait, that's mΩ
         * Actually: V[µV] / I[mA] = (V×1e-6)/(I×1e-3) = V/(I×1e3) [Ω] = V_uV/I_mA × 1e-3 [Ω]
         * So R[Ω] = V_uV / (I_mA × 1000) → no, that's wrong.
         * V[V] = V_uV × 1e-6, I[A] = I_mA × 1e-3
         * R[Ω] = V[V]/I[A] = (V_uV × 1e-6)/(I_mA × 1e-3) = V_uV/(I_mA) × 1e-3
         * So R_A = V_ra_uV / (current_mA * 1e-3) ... no:
         * R_A = (V_uV × 1e-6) / (I_mA × 1e-3) = V_uV / I_mA × 1e-3 Ω = V_uV / (I_mA × 1000) Ω
         * Hmm that gives mΩ. Let me just compute: 1µV / 1mA = 1e-6/1e-3 = 1e-3 Ω = 1 mΩ
         * So R[Ω] = V_uV / I_mA / 1000.0  — no, 1µV/1mA = 0.001 Ω
         * R_ohm = (V_uV * 1e-6) / (I_mA * 1e-3) = V_uV / I_mA * 1e-3
         */
        float ra = (v_ra * 1e-3f) / current;  /* Ω (V_uV→V ×1e-6, I_mA→A ×1e-3, ratio ×1e-3) */

        /* R_B: I→2,3; V→4,1 (forward + reverse) */
        float v_rb = measure_voltage_with_reversal(
            VDP_RB_FWD, VDP_RB_REV, current, b_field, temp);
        float rb = (v_rb * 1e-3f) / current;

        /* Solve Van der Pauw for sheet resistance */
        float rs = vdp_solve_rs(ra, rb);

        result.ra_ohm = ra;
        result.rb_ohm = rb;
        result.sheet_resistance = rs;
        result.resistivity = rs * current_params.sample_thickness_mm * 0.1f;  /* mm→cm */
        result.temperature_c = temp;
        result.current_ma = current;

        oled_show_vdp_progress(ra, rb, rs);

        state = MEAS_HALL_BP;
        break;
    }

    case MEAS_HALL_BP:
    {
        float current = current_params.current_ma;
        float temp = read_temperature();

        /* Rotate magnet to B+ */
        magnet_set_b_plus();
        delay_ms(500);  /* mechanical settle */
        float b_field = magnet_get_b_field();

        /* Hall measurement: I→1,3; V→2,4 */
        float v_fwd = 0, v_rev = 0;

        vdp_switch_set_config(HALL_BP_FWD);
        current_source_set(current);
        current_source_enable();
        delay_ms(10);
        ads122u04_read_voltage_uv(&v_fwd);
        ads122u04_auto_range(v_fwd);
        ads122u04_read_voltage_uv(&v_fwd);

        if (point_count < MEAS_MAX_POINTS) {
            points[point_count].config = HALL_BP_FWD;
            points[point_count].current_ma = current;
            points[point_count].voltage_uv = v_fwd;
            points[point_count].b_field_t = b_field;
            points[point_count].temperature_c = temp;
            point_count++;
        }

        vdp_switch_set_config(HALL_BP_REV);
        delay_ms(10);
        ads122u04_read_voltage_uv(&v_rev);

        if (point_count < MEAS_MAX_POINTS) {
            points[point_count].config = HALL_BP_REV;
            points[point_count].current_ma = -current;
            points[point_count].voltage_uv = v_rev;
            points[point_count].b_field_t = b_field;
            points[point_count].temperature_c = temp;
            point_count++;
        }

        current_source_disable();

        oled_show_hall_progress("B+", v_fwd, b_field);

        /* Store for Hall computation */
        result.vhall_uv = v_fwd;  /* temp store, will compute in ANALYZE */
        /* Save B+ readings in result fields temporarily */
        result.b_field_t = b_field;

        state = MEAS_HALL_BM;
        break;
    }

    case MEAS_HALL_BM:
    {
        float current = current_params.current_ma;
        float temp = read_temperature();

        /* Rotate magnet 180° to B- */
        magnet_set_b_minus();
        delay_ms(800);  /* mechanical settle (180° rotation) */
        float b_field = magnet_get_b_field();  /* negative */

        float v_fwd = 0, v_rev = 0;

        vdp_switch_set_config(HALL_BM_FWD);
        current_source_set(current);
        current_source_enable();
        delay_ms(10);
        ads122u04_read_voltage_uv(&v_fwd);
        ads122u04_auto_range(v_fwd);
        ads122u04_read_voltage_uv(&v_fwd);

        if (point_count < MEAS_MAX_POINTS) {
            points[point_count].config = HALL_BM_FWD;
            points[point_count].current_ma = current;
            points[point_count].voltage_uv = v_fwd;
            points[point_count].b_field_t = b_field;
            points[point_count].temperature_c = temp;
            point_count++;
        }

        vdp_switch_set_config(HALL_BM_REV);
        delay_ms(10);
        ads122u04_read_voltage_uv(&v_rev);

        if (point_count < MEAS_MAX_POINTS) {
            points[point_count].config = HALL_BM_REV;
            points[point_count].current_ma = -current;
            points[point_count].voltage_uv = v_rev;
            points[point_count].b_field_t = b_field;
            points[point_count].temperature_c = temp;
            point_count++;
        }

        current_source_disable();
        oled_show_hall_progress("B-", v_fwd, b_field);

        state = MEAS_ANALYZING;
        break;
    }

    case MEAS_ANALYZING:
    {
        /* Extract the 4 Hall voltage readings from points[] */
        float v_bp_fwd = 0, v_bp_rev = 0, v_bm_fwd = 0, v_bm_rev = 0;
        float b_field = 0;

        for (int i = 0; i < point_count; i++) {
            switch (points[i].config) {
            case HALL_BP_FWD: v_bp_fwd = points[i].voltage_uv; break;
            case HALL_BP_REV: v_bp_rev = points[i].voltage_uv; break;
            case HALL_BM_FWD: v_bm_fwd = points[i].voltage_uv; b_field = fabsf(points[i].b_field_t); break;
            case HALL_BM_REV: v_bm_rev = points[i].voltage_uv; break;
            default: break;
            }
        }

        float current = current_params.current_ma;
        float thickness = current_params.sample_thickness_mm;

        /* Compute Hall coefficient */
        float rh = hall_compute_rh(v_bp_fwd, v_bp_rev, v_bm_fwd, v_bm_rev,
                                    current, b_field, thickness);

        /* Compute carrier concentration */
        float n = hall_compute_conc(rh);

        /* Compute mobility */
        float mu = hall_compute_mobility(rh, result.sheet_resistance);

        /* Determine carrier type */
        carrier_type_t ctype = (rh > 0) ? CARRIER_P_TYPE : CARRIER_N_TYPE;
        if (fabsf(rh) < 1e-15f) ctype = CARRIER_UNKNOWN;

        /* Store results */
        result.hall_coefficient = rh;
        result.carrier_conc = n;
        result.mobility = mu;
        result.carrier_type = ctype;
        result.vhall_uv = (v_bp_fwd - v_bp_rev - v_bm_fwd + v_bm_rev) / 4.0f;
        result.b_field_t = b_field;
        result.sample_thickness_mm = thickness;
        result.n_points = point_count;
        result.final_state = MEAS_DONE;
        result.status = 0;

        /* Park magnet */
        magnet_park();

        /* Display result */
        oled_show_result(&result);

        /* Log to SD */
        if (sd_logger_is_mounted()) {
            sd_logger_start(&result, &current_params);
            for (int i = 0; i < point_count; i++) {
                sd_logger_write_point(&points[i], i + 1);
            }
            sd_logger_write_result(&result);
            sd_logger_close();
        }

        /* Send to ESP32-C3 for BLE/WiFi streaming */
        esp32_link_send_result(&result);

        /* Increment measurement counter */
        flash_store_increment_measurements();

        state = MEAS_DONE;
        break;
    }
    }
}