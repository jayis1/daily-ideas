/*
 * Melody Sprite — RP2040 FM Synthesizer
 * synth_engine.c — FM synthesis voice implementation
 */

#include "synth_engine.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define TWO_PI (2.0f * M_PI)
#define MIN_FREQ  20.0f
#define MAX_FREQ  20000.0f

/* MIDI note to frequency (A440 tuning) */
float midi_to_freq(uint8_t note)
{
    if (note < MIDI_NOTE_MIN) note = MIDI_NOTE_MIN;
    if (note > MIDI_NOTE_MAX) note = MIDI_NOTE_MAX;
    return 440.0f * powf(2.0f, (float)(note - 69) / 12.0f);
}

/* --- ADSR envelope --- */

static void adsr_init(adsr_t *env, float attack, float decay,
                       float sustain, float release)
{
    env->state    = ENV_IDLE;
    env->attack   = attack;
    env->decay    = decay;
    env->sustain  = sustain;
    env->release  = release;
    env->level    = 0.0f;
    env->phase    = 0.0f;
}

static void adsr_trigger(adsr_t *env)
{
    env->state = ENV_ATTACK;
    env->phase = 0.0f;
}

static void adsr_release(adsr_t *env)
{
    if (env->state != ENV_IDLE) {
        env->state = ENV_RELEASE;
        env->phase = 0.0f;
    }
}

static float adsr_process(adsr_t *env)
{
    if (env->state == ENV_IDLE) return 0.0f;

    float dt = 1.0f / (float)SAMPLE_RATE;

    switch (env->state) {
    case ENV_ATTACK:
        env->phase += dt / fmaxf(env->attack, 0.001f);
        if (env->phase >= 1.0f) {
            env->level = 1.0f;
            env->state = ENV_DECAY;
            env->phase = 0.0f;
        } else {
            env->level = env->phase; /* linear attack */
        }
        break;

    case ENV_DECAY:
        env->phase += dt / fmaxf(env->decay, 0.001f);
        if (env->phase >= 1.0f) {
            env->level = env->sustain;
            env->state = ENV_SUSTAIN;
        } else {
            env->level = 1.0f - (1.0f - env->sustain) * env->phase;
        }
        break;

    case ENV_SUSTAIN:
        env->level = env->sustain;
        break;

    case ENV_RELEASE:
        env->phase += dt / fmaxf(env->release, 0.001f);
        if (env->phase >= 1.0f) {
            env->level = 0.0f;
            env->state = ENV_IDLE;
        } else {
            env->level = env->sustain * (1.0f - env->phase);
        }
        break;

    default:
        env->level = 0.0f;
        env->state = ENV_IDLE;
        break;
    }

    return env->level;
}

/* --- FM operator --- */

static void fm_op_init(fm_operator_t *op)
{
    op->ratio       = 1.0f;
    op->mod_index   = 0.0f;
    op->feedback    = 0.0f;
    op->phase       = 0.0f;
    op->phase_inc   = 0.0f;
    op->last_output = 0.0f;
    adsr_init(&op->envelope, 0.01f, 0.1f, 0.7f, 0.2f);
}

static float fm_op_process(fm_operator_t *op, float modulation_in)
{
    /* Phase increment = base_freq * ratio * 2π / sample_rate */
    float output = sinf(op->phase + modulation_in + op->feedback * op->last_output);
    op->last_output = output;

    /* Advance phase */
    op->phase += op->phase_inc;
    if (op->phase >= TWO_PI) {
        op->phase -= TWO_PI;
    }

    return output;
}

/* --- Voice management --- */

static void voice_init(fm_voice_t *voice)
{
    voice->active      = false;
    voice->note        = 60;
    voice->velocity    = 0;
    voice->base_freq   = 0.0f;
    voice->volume      = 0.0f;
    voice->trigger_time = 0;

    fm_op_init(&voice->modulator);
    fm_op_init(&voice->carrier);

    /* Default: modulator has ratio 1.0, carrier ratio 1.0 (basic sine) */
    voice->modulator.ratio     = 1.0f;
    voice->modulator.mod_index = 0.0f;
    voice->modulator.feedback  = 0.0f;

    voice->carrier.ratio       = 1.0f;
    voice->carrier.mod_index   = 0.0f;
    voice->carrier.feedback    = 0.0f;

    /* Default envelopes */
    adsr_init(&voice->modulator.envelope, 0.005f, 0.1f, 0.8f, 0.15f);
    adsr_init(&voice->carrier.envelope, 0.01f, 0.15f, 0.7f, 0.3f);
}

static void voice_update_phase_inc(fm_voice_t *voice)
{
    float base_freq = voice->base_freq;
    voice->modulator.phase_inc = base_freq * voice->modulator.ratio * TWO_PI / (float)SAMPLE_RATE;
    voice->carrier.phase_inc   = base_freq * voice->carrier.ratio   * TWO_PI / (float)SAMPLE_RATE;
}

/* --- Effect processing --- */

static void fx_init(fx_chain_t *fx)
{
    memset(fx, 0, sizeof(fx_chain_t));

    fx->delay_on       = false;
    fx->delay_time     = 250.0f;
    fx->delay_feedback = 0.4f;
    fx->delay_mix      = 0.3f;
    fx->delay_write_idx = 0;
    fx->delay_read_offset = (int)(250.0f * (float)SAMPLE_RATE / 1000.0f);

    fx->crush_on        = false;
    fx->crush_bits      = 16;
    fx->crush_downsample = 1;
    fx->crush_counter   = 0;
    fx->crush_last      = 0.0f;

    fx->lpf_on        = false;
    fx->lpf_cutoff    = 8000.0f;
    fx->lpf_resonance = 0.7f;
    fx->lpf_low       = 0.0f;
    fx->lpf_high      = 0.0f;
    fx->lpf_band      = 0.0f;
}

static float fx_process_delay(fx_chain_t *fx, float input)
{
    if (!fx->delay_on) return input;

    int read_idx = fx->delay_write_idx - fx->delay_read_offset;
    if (read_idx < 0) read_idx += SAMPLE_RATE;

    float delayed = fx->delay_buffer[read_idx];

    /* Write: input + feedback */
    fx->delay_buffer[fx->delay_write_idx] = input + delayed * fx->delay_feedback;

    fx->delay_write_idx = (fx->delay_write_idx + 1) % SAMPLE_RATE;

    return input * (1.0f - fx->delay_mix) + delayed * fx->delay_mix;
}

static float fx_process_bitcrush(fx_chain_t *fx, float input)
{
    if (!fx->crush_on) return input;

    /* Downsample */
    fx->crush_counter++;
    if (fx->crush_counter >= fx->crush_downsample) {
        fx->crush_counter = 0;

        /* Bit crush */
        int levels = 1 << fx->crush_bits;
        if (levels < 2) levels = 2;
        float crushed = roundf(input * (float)levels) / (float)levels;
        fx->crush_last = crushed;
    }

    return fx->crush_last;
}

static float fx_process_lpf(fx_chain_t *fx, float input)
{
    if (!fx->lpf_on) return input;

    /* State variable filter (SVF) */
    float f = 2.0f * sinf(M_PI * fx->lpf_cutoff / (float)SAMPLE_RATE);
    float q = fmaxf(1.0f / fx->lpf_resonance, 0.01f);

    fx->lpf_low  += f * fx->lpf_band;
    fx->lpf_high  = input - fx->lpf_low - q * fx->lpf_band;
    fx->lpf_band += f * fx->lpf_high;

    return fx->lpf_low;
}

/* --- Engine API --- */

void synth_init(synth_engine_t *engine)
{
    memset(engine, 0, sizeof(synth_engine_t));

    for (int i = 0; i < NUM_VOICES; i++) {
        voice_init(&engine->voices[i]);
    }

    fx_init(&engine->fx);

    engine->master_volume = 0.7f;
    engine->active_voices = 0;
    engine->octave_offset = 0;
    engine->hold_active   = false;
    engine->buffer_ready  = false;
}

void synth_note_on(synth_engine_t *engine, uint8_t note, uint8_t velocity)
{
    if (note < MIDI_NOTE_MIN || note > MIDI_NOTE_MAX) return;

    /* Find a free voice (or steal the oldest) */
    int best = -1;
    int64_t oldest_time = INT64_MAX;

    for (int i = 0; i < NUM_VOICES; i++) {
        /* Re-trigger if same note already playing */
        if (engine->voices[i].active && engine->voices[i].note == note) {
            best = i;
            break;
        }
        /* Find idle voice */
        if (!engine->voices[i].active ||
            engine->voices[i].carrier.envelope.state == ENV_IDLE) {
            best = i;
            break;
        }
        /* Track oldest for voice stealing */
        if (engine->voices[i].trigger_time < oldest_time) {
            oldest_time = engine->voices[i].trigger_time;
            best = i;
        }
    }

    if (best < 0) best = 0;

    fm_voice_t *v = &engine->voices[best];
    v->active       = true;
    v->note         = note;
    v->velocity     = velocity;
    v->base_freq    = midi_to_freq(note);
    v->volume       = (float)velocity / 127.0f;
    v->trigger_time = (int64_t)note * 1000 + velocity; /* simplified timestamp */

    /* Reset phases for clean attack */
    v->modulator.phase = 0.0f;
    v->carrier.phase   = 0.0f;

    /* Trigger envelopes */
    adsr_trigger(&v->modulator.envelope);
    adsr_trigger(&v->carrier.envelope);

    /* Update phase increments */
    voice_update_phase_inc(v);

    engine->active_voices++;
}

void synth_note_off(synth_engine_t *engine, uint8_t note)
{
    for (int i = 0; i < NUM_VOICES; i++) {
        if (engine->voices[i].active && engine->voices[i].note == note) {
            if (!engine->hold_active) {
                adsr_release(&engine->voices[i].modulator.envelope);
                adsr_release(&engine->voices[i].carrier.envelope);
            }
            /* Voice will be freed when envelope reaches IDLE */
        }
    }
}

void synth_note_all_off(synth_engine_t *engine)
{
    for (int i = 0; i < NUM_VOICES; i++) {
        adsr_release(&engine->voices[i].modulator.envelope);
        adsr_release(&engine->voices[i].carrier.envelope);
        engine->hold_active = false;
    }
}

void synth_set_voice_param(synth_engine_t *engine, int voice,
                            const char *param, float value)
{
    if (voice < 0 || voice >= NUM_VOICES) return;
    fm_voice_t *v = &engine->voices[voice];

    if (strcmp(param, "mod_ratio") == 0) {
        v->modulator.ratio = fmaxf(0.25f, fminf(8.0f, value));
        voice_update_phase_inc(v);
    } else if (strcmp(param, "mod_index") == 0) {
        v->modulator.mod_index = fmaxf(0.0f, fminf(1023.0f, value));
    } else if (strcmp(param, "feedback") == 0) {
        v->carrier.feedback = fmaxf(0.0f, fminf(15.0f, value));
    } else if (strcmp(param, "attack") == 0) {
        v->carrier.envelope.attack = fmaxf(0.001f, fminf(5.0f, value / 1000.0f));
        v->modulator.envelope.attack = v->carrier.envelope.attack * 0.5f;
    } else if (strcmp(param, "release") == 0) {
        v->carrier.envelope.release = fmaxf(0.001f, fminf(5.0f, value / 1000.0f));
        v->modulator.envelope.release = v->carrier.envelope.release * 0.7f;
    } else if (strcmp(param, "volume") == 0) {
        v->volume = fmaxf(0.0f, fminf(1.0f, value));
    }
}

void synth_set_fx_param(synth_engine_t *engine, const char *fx_name,
                          const char *param, float value)
{
    fx_chain_t *fx = &engine->fx;

    if (strcmp(fx_name, "delay") == 0) {
        if (strcmp(param, "time") == 0) {
            fx->delay_time = fmaxf(10.0f, fminf(1000.0f, value));
            fx->delay_read_offset = (int)(fx->delay_time * (float)SAMPLE_RATE / 1000.0f);
        } else if (strcmp(param, "feedback") == 0) {
            fx->delay_feedback = fmaxf(0.0f, fminf(0.9f, value));
        } else if (strcmp(param, "mix") == 0) {
            fx->delay_mix = fmaxf(0.0f, fminf(1.0f, value));
        }
    } else if (strcmp(fx_name, "crush") == 0) {
        if (strcmp(param, "bits") == 0) {
            fx->crush_bits = (int)fmaxf(1, fminf(16, value));
        } else if (strcmp(param, "downsample") == 0) {
            fx->crush_downsample = (int)fmaxf(1, fminf(64, value));
        }
    } else if (strcmp(fx_name, "lpf") == 0) {
        if (strcmp(param, "cutoff") == 0) {
            fx->lpf_cutoff = fmaxf(100.0f, fminf(20000.0f, value));
        } else if (strcmp(param, "resonance") == 0) {
            fx->lpf_resonance = fmaxf(0.1f, fminf(8.0f, value));
        }
    }
}

void synth_toggle_fx(synth_engine_t *engine, const char *fx_name, bool on)
{
    if (strcmp(fx_name, "delay") == 0) engine->fx.delay_on = on;
    else if (strcmp(fx_name, "crush") == 0) engine->fx.crush_on = on;
    else if (strcmp(fx_name, "lpf") == 0) engine->fx.lpf_on = on;
}

void synth_process(synth_engine_t *engine)
{
    float mix_buf[BUFFER_SIZE];
    memset(mix_buf, 0, sizeof(mix_buf));

    /* Render each active voice */
    for (int v = 0; v < NUM_VOICES; v++) {
        fm_voice_t *voice = &engine->voices[v];
        if (!voice->active) continue;

        /* Check if voice is done */
        if (voice->carrier.envelope.state == ENV_IDLE &&
            voice->modulator.envelope.state == ENV_IDLE) {
            voice->active = false;
            continue;
        }

        for (int s = 0; s < BUFFER_SIZE; s++) {
            /* Modulator: produces modulation signal */
            float mod_env = adsr_process(&voice->modulator.envelope);
            float mod_out = fm_op_process(&voice->modulator, 0.0f);
            float mod_signal = mod_out * voice->modulator.mod_index * mod_env;

            /* Carrier: produces audio output, modulated by modulator */
            float car_env = adsr_process(&voice->carrier.envelope);
            float car_out = fm_op_process(&voice->carrier, mod_signal);

            /* Mix voice into buffer */
            mix_buf[s] += car_out * car_env * voice->volume;
        }
    }

    /* Normalize by number of active voices */
    float norm = 1.0f / fmaxf(1.0f, (float)engine->active_voices);

    /* Apply effects chain */
    for (int s = 0; s < BUFFER_SIZE; s++) {
        float sample = mix_buf[s] * norm * engine->master_volume;

        /* Delay */
        sample = fx_process_delay(&engine->fx, sample);

        /* Bit-crusher */
        sample = fx_process_bitcrush(&engine->fx, sample);

        /* Low-pass filter */
        sample = fx_process_lpf(&engine->fx, sample);

        /* Soft clip (tanh approximation) */
        sample = tanhf(sample * 1.5f) / 1.5f;

        /* Clamp and convert to 16-bit stereo interleaved */
        int16_t val = (int16_t)(fmaxf(-1.0f, fminf(1.0f, sample)) * 32767.0f);
        engine->audio_buffer[s * 2]     = val; /* Left */
        engine->audio_buffer[s * 2 + 1] = val; /* Right */
    }

    engine->buffer_ready = true;
}