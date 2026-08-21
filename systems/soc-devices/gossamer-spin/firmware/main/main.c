/*
 * gossamer-spin / firmware / main.c
 * Main application: boot, state machine, electrospinning run loop.
 *
 * The run loop runs at 10 Hz (process data update rate):
 *   1. Check safety (door, tilt, current comparator)
 *   2. Update HV PID (runs at 1 kHz in a timer ISR)
 *   3. Read jet current + classify state
 *   4. Read environment (temp/humidity)
 *   5. Update OLED display
 *   6. Log to SD card
 *   7. Send process data to ESP32 (BLE/Wi-Fi relay)
 *   8. Check run duration / syringe empty
 */
#include "main.h"

spin_ctx_t g_ctx = { 0 };

const char *const JET_STATE_NAMES[5] = {
    "IDLE", "STABLE", "INTERRUPTED", "UNSTABLE", "DRIPPING"
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
    /* ADC reading of VBAT ÷ 2 → mV. Placeholder. */
    return 3900;
}

static void check_run_complete(void)
{
    uint32_t elapsed = (millis() - g_ctx.run_start_ms) / 1000;
    g_ctx.proc.elapsed_s = elapsed;

    if (elapsed >= g_ctx.recipe.duration_s) {
        /* Run complete — shut down gracefully */
        hv_enable(false);
        syringe_stop();
        collector_stop();
        sd_log_close();
        g_ctx.state = ST_IDLE;
    }

    if (syringe_empty()) {
        hv_enable(false);
        syringe_stop();
        collector_stop();
        sd_log_close();
        g_ctx.state = ST_IDLE;
    }
}

static void do_run_step(void)
{
    process_t *p = &g_ctx.proc;

    /* 1. Safety check */
    if (!safety_check()) {
        p->jet_state = JET_IDLE;
        hv_enable(false);
        syringe_stop();
        collector_stop();
        g_ctx.safety_tripped = true;
        g_ctx.safety_source = safety_get_source();
        g_ctx.state = ST_SAFE;
        return;
    }

    /* 2. Read jet current + classify */
    jet_current_update(&p->current_na, &p->jet_sigma_na, &p->jet_state);

    /* 3. Read HV voltage (PID runs in ISR) */
    p->voltage_kv = hv_read_voltage();

    /* 4. Read environment */
    env_read(&p->temp_c, &p->rh_pct);

    /* 5. Update context */
    p->flow_mlh = g_ctx.recipe.flow_mlh;
    p->drum_rpm = g_ctx.recipe.drum_rpm;
    p->elapsed_s = (millis() - g_ctx.run_start_ms) / 1000;
    g_ctx.battery_mv = read_battery_mv();

    /* 6. Update OLED */
    oled_update(&g_ctx);

    /* 7. Log to SD */
    sd_log_write(p);

    /* 8. Send to ESP32 for BLE/Wi-Fi */
    uart_link_send(p);

    /* 9. Check completion */
    check_run_complete();
}

static void start_run(void)
{
    recipe_t *r = &g_ctx.recipe;

    /* Safety pre-check */
    if (!safety_check()) {
        g_ctx.state = ST_SAFE;
        g_ctx.safety_tripped = true;
        g_ctx.safety_source = safety_get_source();
        return;
    }

    /* Set HV target */
    hv_set_target(r->voltage_kv);

    /* Start syringe pump */
    syringe_set_flow(r->flow_mlh);
    syringe_start();

    /* Start collector drum */
    collector_set_rpm(r->drum_rpm);
    collector_start();

    /* Enable HV (last — after everything else is ready) */
    hv_enable(true);

    g_ctx.run_start_ms = millis();
    g_ctx.safety_tripped = false;
    g_ctx.state = ST_RUNNING;

    /* Open new SD log file */
    sd_log_init();
}

static void stop_run(void)
{
    hv_enable(false);
    syringe_stop();
    collector_stop();
    sd_log_close();
    g_ctx.state = ST_IDLE;
}

int main(void)
{
    /* HAL init, clock to 170 MHz, GPIO, peripherals */
    boot_ms = millis();

    /* Init all modules */
    hv_supply_init();
    syringe_pump_init();
    collector_init();
    jet_current_init();
    safety_init();
    env_monitor_init();
    oled_init();
    sd_log_init();
    uart_link_init();
    recipe_init();

    /* Default state */
    g_ctx.state = ST_IDLE;
    g_ctx.recipe_idx = 0;
    recipe_load(0, &g_ctx.recipe);

    while (1) {
        /* Poll for commands from ESP32 (BLE/Wi-Fi) */
        uart_link_poll();

        switch (g_ctx.state) {
        case ST_BOOT:
            g_ctx.state = ST_IDLE;
            break;

        case ST_IDLE:
            oled_update(&g_ctx);
            /* Wait for button press or BLE command to start */
            /* ~200 ms sleep */
            continue;

        case ST_READY:
            oled_update(&g_ctx);
            continue;

        case ST_RUNNING:
            do_run_step();
            break;

        case ST_SAFE:
            /* Safety tripped — display warning, wait for manual reset */
            oled_update(&g_ctx);
            /* Require power cycle or button hold to reset */
            continue;

        case ST_ERROR:
            oled_update(&g_ctx);
            continue;
        }

        /* ~100 ms cycle (10 Hz) */
    }
}