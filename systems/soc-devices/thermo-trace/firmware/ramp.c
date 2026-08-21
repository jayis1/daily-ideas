/*
 * ramp.c — Temperature program generator
 *
 * Generates the temperature setpoint vs. time profile for a DSC scan.
 * A program consists of up to 16 segments, each being either:
 *   - RAMP: linear temperature ramp from current temp to target at rate (°C/min)
 *   - HOLD: isothermal hold at target temp for duration (seconds)
 *
 * Example program (default):
 *   1. RAMP from RT to 300°C at 5°C/min  (35 min)
 *   2. HOLD at 300°C for 60 seconds
 *   3. (Cool naturally to <50°C for next scan)
 */

#include "ramp.h"

void ramp_init(ramp_program_t *prog) {
    for (int i = 0; i < MAX_SEGMENTS; i++) {
        prog->segments[i].type = SEG_RAMP;
        prog->segments[i].target_temp = 0.0f;
        prog->segments[i].rate = 0.0f;
        prog->segments[i].duration = 0.0f;
    }
    prog->num_segments = 0;
    prog->current_seg = 0;
    prog->current_setpoint = 0.0f;
    prog->start_temp = 0.0f;
    prog->seg_elapsed = 0.0f;
    prog->total_elapsed = 0.0f;
    prog->active = false;
    prog->complete = false;
}

void ramp_add_segment(ramp_program_t *prog, seg_type_t type,
                       float target, float rate, float duration) {
    if (prog->num_segments >= MAX_SEGMENTS) return;
    ramp_seg_t *seg = &prog->segments[prog->num_segments];
    seg->type = type;
    seg->target_temp = target;
    seg->rate = rate;
    seg->duration = duration;
    prog->num_segments++;
}

void ramp_set_default(ramp_program_t *prog, float max_temp, float rate) {
    ramp_init(prog);
    ramp_add_segment(prog, SEG_RAMP, max_temp, rate, 0.0f);
    ramp_add_segment(prog, SEG_HOLD, max_temp, 0.0f, 60.0f);
}

void ramp_start(ramp_program_t *prog, float start_temp) {
    prog->current_seg = 0;
    prog->current_setpoint = start_temp;
    prog->start_temp = start_temp;
    prog->seg_elapsed = 0.0f;
    prog->total_elapsed = 0.0f;
    prog->active = true;
    prog->complete = false;
}

float ramp_update(ramp_program_t *prog, float dt) {
    if (!prog->active || prog->complete) return prog->current_setpoint;

    prog->seg_elapsed += dt;
    prog->total_elapsed += dt;

    if (prog->current_seg >= prog->num_segments) {
        prog->complete = true;
        prog->active = false;
        return prog->current_setpoint;
    }

    ramp_seg_t *seg = &prog->segments[prog->current_seg];

    if (seg->type == SEG_RAMP) {
        /* Linear ramp: dT/dt = rate/60 °C/s */
        float rate_per_s = seg->rate / 60.0f;
        float delta = rate_per_s * dt;
        if (seg->target_temp > prog->start_temp) {
            prog->current_setpoint += delta;
            if (prog->current_setpoint >= seg->target_temp) {
                prog->current_setpoint = seg->target_temp;
                prog->current_seg++;
                prog->seg_elapsed = 0.0f;
                prog->start_temp = prog->current_setpoint;
            }
        } else {
            prog->current_setpoint += delta;  /* negative delta for cooling */
            if (prog->current_setpoint <= seg->target_temp) {
                prog->current_setpoint = seg->target_temp;
                prog->current_seg++;
                prog->seg_elapsed = 0.0f;
                prog->start_temp = prog->current_setpoint;
            }
        }
    } else { /* SEG_HOLD */
        prog->current_setpoint = seg->target_temp;
        if (prog->seg_elapsed >= seg->duration) {
            prog->current_seg++;
            prog->seg_elapsed = 0.0f;
            prog->start_temp = prog->current_setpoint;
        }
    }

    if (prog->current_seg >= prog->num_segments) {
        prog->complete = true;
        prog->active = false;
    }

    return prog->current_setpoint;
}

void ramp_abort(ramp_program_t *prog) {
    prog->active = false;
    prog->complete = false;
    prog->current_setpoint = prog->start_temp;
}