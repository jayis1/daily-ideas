/*
 * Melody Sprite — RP2040 FM Synthesizer
 * sequencer.c — Step sequencer implementation
 */

#include "sequencer.h"
#include <string.h>

/* Calculate step interval from tempo (in microseconds) */
static void seq_update_interval(sequencer_t *seq)
{
    /* 4 steps per beat at 16th note resolution */
    float bps = (float)seq->pattern.tempo / 60.0f;
    seq->step_interval_us = (uint32_t)(1000000.0f / (bps * 4.0f));
}

void seq_init(sequencer_t *seq)
{
    memset(seq, 0, sizeof(sequencer_t));

    seq->mode = SEQ_MODE_LIVE;
    seq->recording = false;
    seq->playing = false;
    seq->current_step = 0;
    seq->last_step_time = 0;
    seq->step_changed = false;
    seq->pending_note = 0xFF;
    seq->pending_vel = 0;

    /* Default pattern */
    seq->pattern.tempo = SEQ_DEFAULT_TEMPO;
    seq->pattern.swing = 0;
    seq->pattern.current_bank = 0;
    seq->pattern.pattern_num = 0;

    /* All steps empty */
    for (int i = 0; i < SEQ_TOTAL_STEPS; i++) {
        seq->pattern.steps[i].note = 0xFF;
        seq->pattern.steps[i].velocity = 0;
        seq->pattern.steps[i].gate = 100;
        seq->pattern.steps[i].accent = false;
    }

    seq_update_interval(seq);
}

void seq_set_tempo(sequencer_t *seq, uint16_t bpm)
{
    if (bpm < SEQ_MIN_TEMPO) bpm = SEQ_MIN_TEMPO;
    if (bpm > SEQ_MAX_TEMPO) bpm = SEQ_MAX_TEMPO;
    seq->pattern.tempo = bpm;
    seq_update_interval(seq);
}

void seq_set_swing(sequencer_t *seq, uint8_t swing)
{
    seq->pattern.swing = swing > 100 ? 100 : swing;
}

void seq_play(sequencer_t *seq)
{
    seq->playing = true;
    seq->current_step = 0;
    seq->last_step_time = 0;
    seq->mode = SEQ_MODE_PLAY;
}

void seq_stop(sequencer_t *seq)
{
    seq->playing = false;
    seq->recording = false;
    /* Send note-off for any playing notes */
    synth_note_all_off(NULL); /* will need engine ref */
}

void seq_record_start(sequencer_t *seq)
{
    seq->recording = true;
    seq->mode = SEQ_MODE_LIVE;
    seq->current_step = 0;
    seq->last_step_time = 0;
    seq->playing = true;

    /* Clear pattern for new recording */
    for (int i = 0; i < SEQ_TOTAL_STEPS; i++) {
        seq->pattern.steps[i].note = 0xFF;
        seq->pattern.steps[i].velocity = 0;
    }
}

void seq_record_stop(sequencer_t *seq)
{
    seq->recording = false;
    if (seq->mode == SEQ_MODE_LIVE) {
        seq->mode = SEQ_MODE_EDIT;
    }
}

void seq_tick(sequencer_t *seq, synth_engine_t *synth)
{
    if (!seq->playing) return;

    /* Advance step based on tempo */
    int64_t now = 0; /* Will use rp2040 timer in real firmware */
    now += seq->step_interval_us; /* Simplified: called once per step */

    /* Apply swing: even steps are shortened, odd steps are lengthened */
    uint32_t interval = seq->step_interval_us;
    if (seq->pattern.swing > 0) {
        float swing_factor = (float)seq->pattern.swing / 100.0f;
        if (seq->current_step % 2 == 0) {
            interval = (uint32_t)((float)interval * (1.0f - swing_factor * 0.33f));
        } else {
            interval = (uint32_t)((float)interval * (1.0f + swing_factor * 0.33f));
        }
    }

    seq_step_t *step = &seq->pattern.steps[seq->current_step];

    if (step->note != 0xFF && step->velocity > 0) {
        /* Note on for this step */
        synth_note_on(synth, step->note, step->velocity);

        /* Schedule note-off based on gate length */
        /* For now, note-off at next step (simplified) */
    } else {
        /* Rest step — send all-notes-off if previous had notes */
        synth_note_all_off(synth);
    }

    /* If recording, capture pending note */
    if (seq->recording && seq->pending_note != 0xFF) {
        step->note = seq->pending_note;
        step->velocity = seq->pending_vel;
        step->gate = 80; /* default gate */
        step->accent = false;
        seq->pending_note = 0xFF;
    }

    /* Advance to next step */
    seq->current_step = (seq->current_step + 1) % SEQ_TOTAL_STEPS;
    seq->step_changed = true;
}

void seq_set_step(sequencer_t *seq, uint8_t step, uint8_t note,
                   uint8_t velocity, uint8_t gate, bool accent)
{
    if (step >= SEQ_TOTAL_STEPS) return;
    seq->pattern.steps[step].note = note;
    seq->pattern.steps[step].velocity = velocity;
    seq->pattern.steps[step].gate = gate;
    seq->pattern.steps[step].accent = accent;
}

void seq_clear_step(sequencer_t *seq, uint8_t step)
{
    if (step >= SEQ_TOTAL_STEPS) return;
    seq->pattern.steps[step].note = 0xFF;
    seq->pattern.steps[step].velocity = 0;
    seq->pattern.steps[step].gate = 100;
    seq->pattern.steps[step].accent = false;
}

void seq_clear_pattern(sequencer_t *seq)
{
    for (int i = 0; i < SEQ_TOTAL_STEPS; i++) {
        seq_clear_step(seq, i);
    }
}

/* Pattern serialization for flash storage */
void seq_pattern_to_bytes(const seq_pattern_t *pat, uint8_t *buf)
{
    int offset = 0;

    /* Tempo (2 bytes) */
    buf[offset++] = (uint8_t)(pat->tempo & 0xFF);
    buf[offset++] = (uint8_t)(pat->tempo >> 8);

    /* Swing (1 byte) */
    buf[offset++] = pat->swing;

    /* Current bank (1 byte) */
    buf[offset++] = pat->current_bank;

    /* Steps: 4 bytes each × 64 steps = 256 bytes */
    for (int i = 0; i < SEQ_TOTAL_STEPS; i++) {
        buf[offset++] = pat->steps[i].note;
        buf[offset++] = pat->steps[i].velocity;
        buf[offset++] = pat->steps[i].gate;
        buf[offset++] = pat->steps[i].accent ? 0x01 : 0x00;
    }
}

void seq_bytes_to_pattern(const uint8_t *buf, seq_pattern_t *pat)
{
    int offset = 0;

    pat->tempo = (uint16_t)buf[offset] | ((uint16_t)buf[offset + 1] << 8);
    offset += 2;

    pat->swing = buf[offset++];
    pat->current_bank = buf[offset++];

    for (int i = 0; i < SEQ_TOTAL_STEPS; i++) {
        pat->steps[i].note = buf[offset++];
        pat->steps[i].velocity = buf[offset++];
        pat->steps[i].gate = buf[offset++];
        pat->steps[i].accent = (buf[offset++] != 0);
    }
}

int seq_save_pattern(sequencer_t *seq, uint8_t pattern_num)
{
    /* In real firmware, this writes to W25Q16 SPI flash */
    /* For now, stub that would call flash_write() */
    (void)seq;
    (void)pattern_num;
    return 0; /* Success */
}

int seq_load_pattern(sequencer_t *seq, uint8_t pattern_num)
{
    /* In real firmware, this reads from W25Q16 SPI flash */
    /* For now, stub that would call flash_read() */
    (void)seq;
    (void)pattern_num;
    return 0; /* Success */
}