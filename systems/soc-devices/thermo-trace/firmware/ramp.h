/*
 * ramp.h — Temperature program (header)
 */
#ifndef RAMP_H
#define RAMP_H

#include <stdint.h>
#include <stdbool.h>

#define MAX_SEGMENTS 16

typedef enum {
    SEG_RAMP,
    SEG_HOLD,
} seg_type_t;

typedef struct {
    seg_type_t type;
    float      target_temp;  /* °C (for RAMP: end temp, for HOLD: hold temp) */
    float      rate;         /* °C/min (for RAMP) */
    float      duration;     /* seconds (for HOLD) */
} ramp_seg_t;

typedef struct {
    ramp_seg_t segments[MAX_SEGMENTS];
    uint8_t    num_segments;
    uint8_t    current_seg;
    float      current_setpoint;
    float      start_temp;
    float      seg_elapsed;
    float      total_elapsed;
    bool       active;
    bool       complete;
} ramp_program_t;

void    ramp_init(ramp_program_t *prog);
void    ramp_add_segment(ramp_program_t *prog, seg_type_t type,
                          float target, float rate, float duration);
void    ramp_start(ramp_program_t *prog, float start_temp);
float   ramp_update(ramp_program_t *prog, float dt);
void    ramp_abort(ramp_program_t *prog);
void    ramp_set_default(ramp_program_t *prog, float max_temp, float rate);

#endif /* RAMP_H */