/*
 * lode-sweep / firmware / audio.c
 * PWM audio synthesis for pitch-coded target identification.
 *
 * Uses TIM3 CH1 (PA7) as a PWM output to generate audio tones.
 * The pitch is mapped to the target class (low=iron, high=gold),
 * and the volume is proportional to signal strength (log-scaled).
 * In discrimination mode, iron and foil targets are silenced.
 */
#include "main.h"
#include <math.h>

/* Pitch per target class (Hz) */
static const float CLASS_PITCH[NUM_CLASSES] = {
    150.0f,   /* Iron     — low growl */
    220.0f,   /* Foil     — low buzz */
    330.0f,   /* Nickel   — medium */
    440.0f,   /* Pull-tab — medium */
    550.0f,   /* Zinc     — medium-high */
    880.0f,   /* Gold     — bright */
    990.0f,   /* Copper   — high */
    1100.0f,  /* Silver   — crisp bell */
};

/* PWM carrier frequency for audio (10 kHz) */
#define PWM_CARRIER_HZ  10000

/* Audio envelope for smooth click-free tones */
static float env_level = 0.0f;

void audio_init(void)
{
    /* TIM3 CH1 on PA7, PWM mode 1, 10 kHz carrier.
       In real build:
       HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
       ARR = 170MHz / 10000 = 17000 (10 kHz carrier)
       CCR = 0 (start silent)
    */
    env_level = 0.0f;
}

/*
 * Update the audio output based on the latest detection result.
 * Called once per sweep (1 kHz). The tone is continuous while a target
 * is present, with a smooth attack/decay envelope.
 */
void audio_update(const sweep_result_t *r)
{
    /* Determine if we should produce sound */
    bool make_sound = true;

    /* Discrimination mode: silence iron and foil */
    if (r->iron_discrim) {
        if (r->target_class == CL_IRON || r->target_class == CL_FOIL) {
            make_sound = false;
        }
    }

    /* No signal → silence */
    if (r->signal_strength < 0.02f) {
        make_sound = false;
    }

    if (!make_sound) {
        /* Smooth decay to silence */
        env_level *= 0.85f;
        if (env_level < 0.01f) env_level = 0.0f;
    } else {
        /* Smooth attack */
        float target_env = clampf(log10f(r->signal_strength * 10.0f + 1.0f) / 3.0f,
                                  0.0f, 1.0f);
        env_level = env_level * 0.7f + target_env * 0.3f;
    }

    if (env_level < 0.01f) {
        /* Set PWM duty to 0 (silence) */
        /* __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, 0) */
        return;
    }

    /* Set the PWM carrier frequency to the target class pitch.
       In real build: change TIM3 ARR to 170MHz / pitch.
       The duty cycle = 50% × envelope level for the tone amplitude. */
    float pitch = CLASS_PITCH[r->target_class];

    /* The PWM output generates a square wave at the pitch frequency,
       with amplitude proportional to env_level.
       In real build:
         uint32_t arr = (uint32_t)(SYS_CLK_HZ / pitch);
         __HAL_TIM_SET_AUTORELOAD(&htim3, arr);
         __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, (arr * env_level) / 2);
    */
    (void)pitch;
    (void)env_level;
}