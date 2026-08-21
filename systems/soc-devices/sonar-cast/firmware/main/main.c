/*
 * sonar-cast / firmware / main.c
 * Main application: boot, state machine, ping loop (STM32G474 core).
 *
 * The ping loop runs in the main thread at the configured ping rate:
 *   1. Fire CHIRP (HRTIM + H-bridge)
 *   2. ADC capture ECHO_WINDOW_SAMPLES
 *   3. Pulse-compress → envelope
 *   4. Detector: bottom + fish + bottom-type
 *   5. Read IMU tilt, pressure depth, water temp → speed of sound
 *   6. Assemble result, update OLED, log to SD, send to ESP32 via UART
 *   7. Poll UART for GPS / commands
 *   8. Sleep until next ping interval
 */
#include "main.h"
#include <math.h>

sonar_ctx_t g_ctx = { 0 };

const char *const BOTTOM_NAMES[4] = { "hard", "soft", "weedy", "unknown" };

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

static void update_context(sonar_result_t *r)
{
    /* Read sensors into the result struct */
    imuw_read_tilt(&r->tilt_deg);
    depth_read(&r->temp_c, &r->depth_pres_m, &r->sound_speed);
    g_ctx.battery_mv = read_battery_mv();
    g_ctx.water_detected = true;   /* PA12 probe (placeholder) */
}

static void do_ping(sonar_result_t *r)
{
    /* 1. Fire CHIRP */
    chirp_fire();

    /* 2. ADC capture */
    uint16_t *raw = adc_capture(ECHO_WINDOW_SAMPLES);
    /* (in real build, block on DMA-complete semaphore) */

    /* 3. Pulse-compress → envelope bins (for BLE) + full envelope (for detector) */
    float env_bins[ECHO_BIN_COUNT];
    adc_pulse_compress(raw, env_bins, ECHO_BIN_COUNT);
    /* copy bins into result */
    memcpy(r->echogram, env_bins, ECHO_BIN_COUNT * sizeof(float));
    /* scale to 0..255 for BLE */
    for (int i = 0; i < ECHO_BIN_COUNT; i++) {
        float v = env_bins[i] * 255.0f;
        if (v > 255) v = 255;
        r->echogram[i] = (uint8_t)v;
    }

    /* 4. Detector on full envelope (re-run compress at full res into a local buf) */
    /* For simplicity we reuse env_bins decimated — in production we'd use
       the full-res envelope from adc_get_env_full(). */
    static float env_full[ECHO_BIN_COUNT];
    for (int i = 0; i < ECHO_BIN_COUNT; i++) env_full[i] = env_bins[i];
    detector_run(env_full, ECHO_BIN_COUNT, r);

    /* 5. Update context (IMU, pressure, temp, battery) */
    update_context(r);

    /* 6. GPS (from ESP32 via UART, already polled) */
    uart_link_poll();
}

static void set_state(sonar_state_t s)
{
    g_ctx.state = s;
    switch (s) {
    case ST_IDLE:   g_ctx.ping_rate_hz = 0;  break;
    case ST_ACTIVE: g_ctx.ping_rate_hz = 10; break;
    case ST_DRIFT:  g_ctx.ping_rate_hz = 1;  break;
    case ST_SLEEP:  g_ctx.ping_rate_hz = 0;  break;
    }
}

int main(void)
{
    /* HAL init, clock to 170 MHz, GPIO, peripherals */
    boot_ms = millis();

    /* Init all modules */
    chirp_init();
    hrtim_drv_init();
    adc_dsp_init();
    detector_init();
    imuw_init();
    depth_init();
    sd_log_init();
    oled_init();
    uart_link_init();
    model_init();

    /* Start in IDLE; switch to ACTIVE when water is detected. */
    set_state(ST_IDLE);

    sonar_result_t *r = &g_ctx.last;

    while (1) {
        /* Poll for commands / GPS */
        uart_link_poll();

        /* State machine */
        switch (g_ctx.state) {
        case ST_IDLE:
            if (g_ctx.water_detected) set_state(ST_ACTIVE);
            oled_update(&g_ctx);
            /* sleep ~500 ms */
            continue;

        case ST_SLEEP:
            /* Everything off; ESP32 wakes us via GPIO8. */
            continue;

        case ST_DRIFT:
        case ST_ACTIVE: {
            uint32_t period_ms = 1000 / g_ctx.ping_rate_hz;
            uint32_t t0 = millis();

            do_ping(r);
            g_ctx.ping_count++;

            oled_update(&g_ctx);
            sd_log_write(r);
            uart_link_send_result(r);

            /* Adaptive ping rate: deeper water → slower ping */
            if (r->depth_m > 40.0f && g_ctx.ping_rate_hz > 5)
                g_ctx.ping_rate_hz = 5;
            else if (r->depth_m < 10.0f && g_ctx.ping_rate_hz < 20)
                g_ctx.ping_rate_hz = 20;

            /* Sleep remainder of period */
            uint32_t elapsed = millis() - t0;
            (void)elapsed;  /* delay(period_ms - elapsed) */
            break;
        }
        }
    }
}

/* Detector init (no state, but keeps the API uniform). */
void detector_init(void) { }