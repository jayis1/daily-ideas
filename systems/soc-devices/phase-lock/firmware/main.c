/*
 * main.c — Phase Lock pocket digital lock-in amplifier
 *
 * Top-level state machine + main loop. Wires together all modules:
 *   ref_osc   — CORDIC sine reference + DAC1 drive
 *   adc       — oversampled 16-bit sampling at 28 ksps
 *   demod     — I/Q digital demodulation + IIR LPF
 *   pga       — programmable-gain front-end + auto-range
 *   power_amp — OPA569 excitation buffer + safety
 *   sweep     — frequency/amplitude sweep engine
 *   display   — SH1106 OLED
 *   sd_log    — microSD CSV logging
 *   ble_bridge— UART → ESP32-C3 BLE
 *   aux_adc   — ADS1115 aux inputs
 *   battery   — 18650 voltage monitor
 *   ui        — rotary encoder + buttons
 *
 * Main loop runs at ~10 kHz: poll UI, process demod (1 sample per loop
 * iteration at 28 ksps is handled by the DMA-ISR-driven adc_get_sample
 * blocking call), push to BLE at 100 Hz, log to SD at 10 Hz, and
 * run the safety checks at 1 Hz.
 */

#include "stm32g491_conf.h"
#include "ref_osc.h"
#include "adc.h"
#include "demod.h"
#include "pga.h"
#include "power_amp.h"
#include "sweep.h"
#include "display.h"
#include "sd_log.h"
#include "ble_bridge.h"
#include "aux_adc.h"
#include "battery.h"
#include "ui.h"
#include <string.h>
#include <stdio.h>

typedef enum {
    ST_IDLE,
    ST_MENU,
    ST_ACQUIRE,
    ST_SWEEP,
    ST_STOP,
} state_t;

static state_t  state = ST_IDLE;
static uint16_t run_id = 1;
static uint32_t sys_ms = 0;       /* SysTick ms counter */
static uint32_t last_ble_ms = 0;
static uint32_t last_log_ms = 0;
static uint32_t last_safety_ms = 0;
static uint32_t last_sweep_step_ms = 0;
static float    cur_freq = 1000.0f;
static float    cur_ampl = 1.0f;
static time_const_t cur_tc = TC_10MS;
static slope_t  cur_slope = SLOPE_6;
static pga_gain_t cur_pga = PGA_GAIN_1;
static bool     auto_gain = true;

static const char *tc_labels[TC_COUNT] = {
    "0.5ms", "1ms", "3ms", "10ms", "30ms", "100ms",
    "300ms", "1s", "3s", "10s"
};

void SystemInit(void)
{
    /* Set HSI 16 MHz → PLL → 170 MHz SYSCLK */
    RCC->CR |= RCC_CR_HSION;
    while (!(RCC->CR & RCC_CR_HSIRDY)) ;
    FLASH->ACR = FLASH_ACR_ICEN | FLASH_ACR_DCEN | FLASH_ACR_PRFTEN
               | FLASH_ACR_LATENCY_2WS;
    RCC->PLLCFGR = (RCC->PLLCFGR & ~(RCC_PLLCFGR_PLLM | RCC_PLLCFGR_PLLN
                                     | RCC_PLLCFGR_PLLP | RCC_PLLCFGR_PLLR))
                 | (PLLM_VALUE << RCC_PLLCFGR_PLLM_Pos)
                 | (PLLN_VALUE << RCC_PLLCFGR_PLLN_Pos)
                 | ((PLLP_VALUE - 1) << RCC_PLLCFGR_PLLP_Pos)
                 | RCC_PLLCFGR_PLLREN;
    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY)) ;
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL) ;
    /* SysTick 1 kHz */
    SysTick->LOAD = (SYSCLK_FREQ / SYSTICK_HZ) - 1;
    SysTick->VAL = 0;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_ENABLE_Msk
                  | SysTick_CTRL_TICKINT_Msk;
}

void SysTick_Handler(void) { sys_ms++; }

static void apply_config(void)
{
    ref_osc_set_freq(cur_freq);
    ref_osc_set_amplitude(cur_ampl);
    demod_set_tc(cur_tc);
    demod_set_slope(cur_slope);
    if (!auto_gain) pga_set_gain(cur_pga);
}

static void start_acquire(void)
{
    if (!battery_ok()) {
        display_show_message("Battery low", "charge first");
        return;
    }
    apply_config();
    pga_auto_range();
    power_amp_enable();
    power_amp_set_ilimit(200);
    ref_osc_start();
    adc_start();
    demod_reset();
    sd_log_open_trace(run_id++, cur_freq, tc_table[cur_tc]);
    state = ST_ACQUIRE;
    display_show_message("ACQUIRE", "R/Theta/X/Y");
}

static void start_sweep(void)
{
    if (!battery_ok()) {
        display_show_message("Battery low", "charge first");
        return;
    }
    apply_config();
    power_amp_enable();
    power_amp_set_ilimit(200);
    sweep_start_freq(10.0f, 100000.0f, 100, true);  /* default 10 Hz–100 kHz, log, 100 pts */
    sd_log_open_sweep(run_id++);
    state = ST_SWEEP;
    last_sweep_step_ms = sys_ms;
}

static void stop_all(void)
{
    ref_osc_stop();
    adc_stop();
    power_amp_disable();
    sweep_stop();
    sd_log_close();
    state = ST_IDLE;
    display_show_message("STOPPED", "idle");
}

int main(void)
{
    SystemInit();

    /* Init all peripherals */
    i2c_init();             /* implicit via display_init */
    display_init();
    ref_osc_init();
    adc_init();
    demod_init();
    pga_init();
    power_amp_init();
    sweep_init();
    sd_log_init();
    ble_bridge_init();
    aux_adc_init();
    ui_init();

    display_show_message("PHASE LOCK", "v1.0 ready");
    for (volatile int i = 0; i < 5000000; ++i) ;   /* splash ~0.5 s */

    state = ST_MENU;

    while (1) {
        ui_poll();

        /* Check for BLE command */
        char cmd[32];
        if (ble_bridge_poll_cmd(cmd, sizeof(cmd))) {
            if (strncmp(cmd, "RUN", 3) == 0)        start_acquire();
            else if (strncmp(cmd, "SWP", 3) == 0)  start_sweep();
            else if (strncmp(cmd, "STOP", 4) == 0) stop_all();
            else if (strncmp(cmd, "F:", 2) == 0)   { sscanf(cmd + 2, "%f", &cur_freq);  apply_config(); }
            else if (strncmp(cmd, "A:", 2) == 0)   { sscanf(cmd + 2, "%f", &cur_ampl);  apply_config(); }
            else if (strncmp(cmd, "TC:", 3) == 0)  { int t; sscanf(cmd + 3, "%d", &t); cur_tc = (time_const_t)t; apply_config(); }
        }

        if (ui_run_pressed()) {
            if (state == ST_IDLE || state == ST_MENU) start_acquire();
            else stop_all();
        }

        /* Process one demod sample every loop iteration (blocks until ready) */
        if (state == ST_ACQUIRE || state == ST_SWEEP) {
            demod_process();
        }

        demod_result_t r = demod_read();

        /* BLE push @ 100 Hz */
        if (sys_ms - last_ble_ms >= 10) {
            last_ble_ms = sys_ms;
            if (state == ST_ACQUIRE)
                ble_bridge_push_demod(&r, cur_freq, pga_get_gain());
        }

        /* SD log @ 10 Hz (time-trace) */
        if (state == ST_ACQUIRE && sys_ms - last_log_ms >= 100) {
            last_log_ms = sys_ms;
            sd_log_trace_row(sys_ms, r.R, r.theta, r.X, r.Y, r.noise);
        }

        /* Sweep step every 3·TC */
        if (state == ST_SWEEP) {
            uint32_t dwell = (uint32_t)(3.0f * tc_table[cur_tc] * 1000.0f);
            if (dwell < 50) dwell = 50;
            if (sys_ms - last_sweep_step_ms >= dwell) {
                last_sweep_step_ms = sys_ms;
                bool more = sweep_step();
                sweep_point_t p = sweep_last_point();
                p.ts_ms = sys_ms;
                sd_log_sweep_point(&p);
                ble_bridge_push_sweep(&p);
                if (!more) {
                    stop_all();
                    display_show_message("SWEEP DONE", "see SD log");
                }
            }
        }

        /* Safety check @ 1 Hz */
        if (sys_ms - last_safety_ms >= 1000) {
            last_safety_ms = sys_ms;
            if (state == ST_ACQUIRE || state == ST_SWEEP) {
                if (!power_amp_safety_check()) {
                    stop_all();
                    display_show_message("SAFETY TRIP", "amp disabled");
                }
                if (auto_gain) pga_auto_range();
                float bv = battery_read();
                if (battery_low()) {
                    display_show_message("Battery low", "");
                    if (state != ST_IDLE) stop_all();
                }
            }
        }

        /* Display update @ ~20 Hz */
        static uint32_t last_disp_ms = 0;
        if (sys_ms - last_disp_ms >= 50) {
            last_disp_ms = sys_ms;
            switch (state) {
                case ST_MENU:
                    display_show_menu(ui_current());
                    break;
                case ST_ACQUIRE:
                    display_show_demod(r, pga_get_gain());
                    break;
                case ST_SWEEP:
                    display_show_sweep(&g_sweep);
                    break;
                default: break;
            }
        }

        /* Menu navigation */
        if (state == ST_MENU) {
            int d = ui_encoder_delta();
            if (d != 0) {
                switch (ui_current()) {
                    case UI_FREQ:   cur_freq  += d * 100.0f; if (cur_freq < 1.0f) cur_freq = 1.0f; if (cur_freq > 100000.0f) cur_freq = 100000.0f; break;
                    case UI_AMPL:   cur_ampl  += d * 0.1f;   if (cur_ampl < 0.0f) cur_ampl = 0.0f; if (cur_ampl > 2.0f) cur_ampl = 2.0f; break;
                    case UI_TC:     cur_tc = (time_const_t)((cur_tc + d + TC_COUNT) % TC_COUNT); break;
                    case UI_SLOPE:  cur_slope = (slope_t)((cur_slope + d + 4) % 4); break;
                    case UI_GAIN:   cur_pga = (pga_gain_t)((cur_pga + d + 11) % 11); auto_gain = (cur_pga == 0); break;
                    case UI_SWEEP:  if (ui_select_pressed()) start_sweep(); break;
                    case UI_RUN:    if (ui_select_pressed()) start_acquire(); break;
                    case UI_LOG:    /* logging is automatic; this just shows status */ break;
                    default: break;
                }
                apply_config();
            }
            if (ui_select_pressed() && ui_current() == UI_RUN)  start_acquire();
            if (ui_select_pressed() && ui_current() == UI_SWEEP) start_sweep();
        }
    }
}