/*
 * lode-sweep / firmware / main.c
 * Main application: boot, state machine, sweep loop (STM32G474 core).
 *
 * The sweep loop runs at 1 kHz (one TX pulse per cycle):
 *   1. Fire TX pulse (HRTIM + MOSFET)
 *   2. ADC capture 256 samples (16 gates × 16 oversample)
 *   3. Extract 16 gates, ground-balance, normalize
 *   4. Classify (k-NN), estimate depth, read IMU tilt
 *   5. Audio feedback (pitch-coded)
 *   6. Update OLED, log to SD (if significant), send to ESP32
 *   7. Poll UART for GPS / commands
 *   8. Sleep until next pulse period (1 ms)
 */
#include "main.h"

sweep_ctx_t g_ctx = { 0 };

const char *const CLASS_NAMES[NUM_CLASSES] = {
    "Iron", "Foil", "Nickel", "Pull-Tab",
    "Zinc", "Gold", "Copper", "Silver"
};

static uint32_t boot_ms = 0;

uint32_t millis(void)
{
    /* In real build: SysTick-based ms counter. */
    static uint32_t fake = 0;
    return fake++ / 100;
}

static uint16_t read_battery_mv(void)
{
    /* ADC reading of VBAT ÷ 2 → mV.  Placeholder. */
    return 3900;
}

static void update_context(sweep_result_t *r)
{
    /* Read IMU tilt */
    imuw_read_tilt(&r->tilt_deg);
    g_ctx.battery_mv = read_battery_mv();
}

/* ADC sample buffer (16 gates × 16 oversample = 256 samples) */
static int16_t adc_samples[ADC_SAMPLES_PER_PULSE];
static float gates[NUM_GATES];

static void do_sweep(sweep_result_t *r)
{
    /* 1. Fire TX pulse + ADC capture */
    pi_fire_and_sample(adc_samples);

    /* 2. Extract 16 gates (oversample averaging) */
    decay_extract(adc_samples, gates);

    /* 3. Ground balance (subtract adaptive ground model) */
    ground_balance(gates);

    /* 4. Normalize decay curve for classification */
    float raw_signal = 0.0f;
    for (int i = 0; i < NUM_GATES; i++) raw_signal += gates[i];
    decay_normalize(gates);
    r->signal_strength = raw_signal;

    /* 5. Classify (k-NN) */
    target_id_classify(gates, r);

    /* 6. Copy decay curve into result */
    memcpy(r->decay, gates, NUM_GATES * sizeof(float));

    /* 7. Update context (IMU tilt, battery) */
    update_context(r);

    /* 8. Estimate depth */
    depth_estimate(r);

    /* 9. GPS (from ESP32 via UART, already polled) */
    uart_link_poll();

    /* 10. Audio feedback */
    r->iron_discrim = g_ctx.discrim_mode ? 1 : 0;
    audio_update(r);
}

static void set_state(sweep_state_t s)
{
    g_ctx.state = s;
}

int main(void)
{
    /* HAL init, clock to 170 MHz, GPIO, peripherals */
    boot_ms = millis();

    /* Init all modules */
    pi_driver_init();
    decay_init();
    ground_init();
    target_id_init();
    depth_init();
    audio_init();
    imuw_init();
    sd_log_init();
    oled_init();
    uart_link_init();
    model_init();

    /* Default settings */
    g_ctx.sensitivity = 5;
    g_ctx.discrim_mode = false;
    g_ctx.ground_amp = 0.0f;
    g_ctx.ground_tau = 3.0f;   /* typical ground τ */

    /* Start in IDLE; switch to ACTIVE on button press */
    set_state(ST_IDLE);

    sweep_result_t *r = &g_ctx.last;
    bool ground_calibrated = false;

    while (1) {
        /* Poll for commands / GPS */
        uart_link_poll();

        /* State machine */
        switch (g_ctx.state) {
        case ST_IDLE:
            oled_update(&g_ctx);
            /* sleep ~200 ms, wait for button press to go ACTIVE */
            continue;

        case ST_SLEEP:
            /* Everything off; ESP32 wakes us via GPIO8. */
            continue;

        case ST_DRIFT:
        case ST_ACTIVE: {
            uint32_t t0 = millis();

            do_sweep(r);
            g_ctx.pulse_count++;

            /* First few pulses: calibrate ground balance */
            if (!ground_calibrated && g_ctx.pulse_count > 16) {
                ground_calibrate(gates);
                ground_calibrated = true;
            }
            /* Re-calibrate ground every 1000 pulses if signal is weak */
            if (g_ctx.pulse_count % 1000 == 0 && r->signal_strength < 0.01f) {
                ground_calibrate(gates);
            }

            oled_update(&g_ctx);

            /* Log to SD only if signal above threshold */
            if (r->signal_strength > 0.05f) {
                sd_log_write(r);
            }

            if (g_ctx.state == ST_ACTIVE) {
                uart_link_send_result(r);
            }

            /* Sleep remainder of 1 ms pulse period */
            uint32_t elapsed = millis() - t0;
            (void)elapsed;  /* delay(TX_PERIOD_US/1000 - elapsed) */
            break;
        }
        }
    }
}