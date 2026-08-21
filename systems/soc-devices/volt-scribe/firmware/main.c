/*
 * volt-scribe — main.c
 * Portable Electrochemical Workstation (STM32G491RET6)
 *
 * Entry point: initializes hardware, runs the interactive command loop.
 * Techniques: CV, DPV, SWV, EIS, Amperometric, Galvanostatic
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

#include "potentiostat.h"
#include "cv_engine.h"
#include "dpv_engine.h"
#include "swv_engine.h"
#include "eis_engine.h"
#include "amperometric.h"
#include "dsp.h"
#include "display.h"
#include "sd_log.h"
#include "ble_relay.h"

/* ── Global state ─────────────────────────────────────────────── */

typedef enum {
    MODE_CV,
    MODE_DPV,
    MODE_SWV,
    MODE_EIS,
    MODE_AMPEROMETRIC,
    MODE_GALVANOSTATIC,
    MODE_COUNT
} technique_mode_t;

static const char *mode_names[MODE_COUNT] = {
    "cv", "dpv", "swv", "eis", "amperometric", "galvanostatic"
};

static technique_mode_t current_mode = MODE_CV;

/* Experiment parameters */
typedef struct {
    /* CV */
    float cv_start;       /* V */
    float cv_vertex;      /* V */
    float cv_end;         /* V */
    float cv_scan_rate;   /* V/s */
    int   cv_cycles;

    /* DPV */
    float dpv_start;      /* V */
    float dpv_end;        /* V */
    float dpv_step;       /* V */
    float dpv_pulse_amp;  /* V */
    float dpv_pulse_width;/* s */
    float dpv_scan_rate;  /* V/s */

    /* SWV */
    float swv_start;      /* V */
    float swv_end;        /* V */
    float swv_step;       /* V */
    float swv_amplitude;  /* V */
    float swv_frequency;  /* Hz */

    /* EIS */
    float eis_dc_bias;    /* V */
    float eis_ac_amp;     /* V rms */
    float eis_freq_start; /* Hz */
    float eis_freq_end;   /* Hz */
    int   eis_ppd;        /* points per decade */

    /* Amperometric */
    float amp_potential;  /* V */
    float amp_duration;   /* s */
    float amp_sample_rate;/* Hz */

    /* Galvanostatic */
    float galv_current;   /* A */
    float galv_duration;  /* s */

    /* iR compensation */
    float ir_compensation;/* Ω (0 = off) */
} params_t;

static params_t params = {
    .cv_start       = -0.2f,
    .cv_vertex      =  0.8f,
    .cv_end         = -0.2f,
    .cv_scan_rate   =  0.05f,
    .cv_cycles      =  3,
    .dpv_start      =  0.0f,
    .dpv_end        =  0.6f,
    .dpv_step       =  0.004f,
    .dpv_pulse_amp  =  0.050f,
    .dpv_pulse_width=  0.050f,
    .dpv_scan_rate  =  0.010f,
    .swv_start      =  0.0f,
    .swv_end        =  0.6f,
    .swv_step       =  0.004f,
    .swv_amplitude  =  0.025f,
    .swv_frequency  =  25.0f,
    .eis_dc_bias    =  0.0f,
    .eis_ac_amp     =  0.010f,
    .eis_freq_start =  1.0f,
    .eis_freq_end   =  100000.0f,
    .eis_ppd        =  10,
    .amp_potential  =  0.45f,
    .amp_duration   =  60.0f,
    .amp_sample_rate=  10.0f,
    .galv_current   =  0.001f,
    .galv_duration  =  60.0f,
    .ir_compensation=  0.0f,
};

static volatile int experiment_running = 0;

/* ── UART command interface (simple line-based CLI) ────────────── */

#define CMD_BUF_LEN 128
static char cmd_buf[CMD_BUF_LEN];
static int cmd_pos = 0;

static void cmd_help(void)
{
    printf("Volt Scribe Commands:\r\n");
    printf("  mode <cv|dpv|swv|eis|amperometric|galvanostatic>\r\n");
    printf("  set <param> <value>  — set experiment parameter\r\n");
    printf("  run                  — start experiment\r\n");
    printf("  stop                 — abort running experiment\r\n");
    printf("  auto                 — auto-range TIA\r\n");
    printf("  status               — show current settings\r\n");
    printf("  help                 — this message\r\n");
}

static void cmd_status(void)
{
    printf("Mode: %s\r\n", mode_names[current_mode]);
    switch (current_mode) {
    case MODE_CV:
        printf("  start=%.3fV vertex=%.3fV end=%.3fV rate=%.3fV/s cycles=%d\r\n",
               params.cv_start, params.cv_vertex, params.cv_end,
               params.cv_scan_rate, params.cv_cycles);
        break;
    case MODE_DPV:
        printf("  start=%.3fV end=%.3fV step=%.3fV pulse=%.3fV rate=%.3fV/s\r\n",
               params.dpv_start, params.dpv_end, params.dpv_step,
               params.dpv_pulse_amp, params.dpv_scan_rate);
        break;
    case MODE_SWV:
        printf("  start=%.3fV end=%.3fV step=%.3fV amp=%.3fV freq=%.1fHz\r\n",
               params.swv_start, params.swv_end, params.swv_step,
               params.swv_amplitude, params.swv_frequency);
        break;
    case MODE_EIS:
        printf("  dc_bias=%.3fV ac_amp=%.4fV f_start=%.1fHz f_end=%.0fHz ppd=%d\r\n",
               params.eis_dc_bias, params.eis_ac_amp,
               params.eis_freq_start, params.eis_freq_end, params.eis_ppd);
        break;
    case MODE_AMPEROMETRIC:
        printf("  E=%.3fV duration=%.1fs rate=%.1fHz\r\n",
               params.amp_potential, params.amp_duration, params.amp_sample_rate);
        break;
    case MODE_GALVANOSTATIC:
        printf("  I=%.6fA duration=%.1fs\r\n",
               params.galv_current, params.galv_duration);
        break;
    default:
        break;
    }
    printf("  iR_comp=%.1f Ohm\r\n", params.ir_compensation);
}

static void process_command(const char *cmd)
{
    char arg1[32], arg2[32];
    float val;

    if (sscanf(cmd, "mode %31s", arg1) == 1) {
        for (int i = 0; i < MODE_COUNT; i++) {
            if (strcmp(arg1, mode_names[i]) == 0) {
                current_mode = (technique_mode_t)i;
                printf("Mode set to %s\r\n", mode_names[i]);
                return;
            }
        }
        printf("Unknown mode: %s\r\n", arg1);
        return;
    }

    if (sscanf(cmd, "set %31s %31s", arg1, arg2) == 2) {
        val = strtof(arg2, NULL);
        if (strcmp(arg1, "potential_start") == 0)       params.cv_start = val;
        else if (strcmp(arg1, "potential_vertex") == 0)  params.cv_vertex = val;
        else if (strcmp(arg1, "potential_end") == 0)     params.cv_end = val;
        else if (strcmp(arg1, "scan_rate") == 0)         params.cv_scan_rate = val;
        else if (strcmp(arg1, "cycles") == 0)             params.cv_cycles = (int)val;
        else if (strcmp(arg1, "dpv_start") == 0)         params.dpv_start = val;
        else if (strcmp(arg1, "dpv_end") == 0)           params.dpv_end = val;
        else if (strcmp(arg1, "dpv_step") == 0)          params.dpv_step = val;
        else if (strcmp(arg1, "dpv_pulse_amp") == 0)     params.dpv_pulse_amp = val;
        else if (strcmp(arg1, "swv_start") == 0)         params.swv_start = val;
        else if (strcmp(arg1, "swv_end") == 0)           params.swv_end = val;
        else if (strcmp(arg1, "swv_amplitude") == 0)     params.swv_amplitude = val;
        else if (strcmp(arg1, "swv_frequency") == 0)     params.swv_frequency = val;
        else if (strcmp(arg1, "eis_dc_bias") == 0)       params.eis_dc_bias = val;
        else if (strcmp(arg1, "eis_ac_amplitude") == 0)  params.eis_ac_amp = val;
        else if (strcmp(arg1, "eis_freq_start") == 0)    params.eis_freq_start = val;
        else if (strcmp(arg1, "eis_freq_end") == 0)      params.eis_freq_end = val;
        else if (strcmp(arg1, "eis_ppd") == 0)           params.eis_ppd = (int)val;
        else if (strcmp(arg1, "potential") == 0)         params.amp_potential = val;
        else if (strcmp(arg1, "duration") == 0)          params.amp_duration = val;
        else if (strcmp(arg1, "sample_rate") == 0)       params.amp_sample_rate = val;
        else if (strcmp(arg1, "ir_compensation") == 0)   params.ir_compensation = val;
        else printf("Unknown parameter: %s\r\n", arg1);
        printf("Set %s = %s\r\n", arg1, arg2);
        return;
    }

    if (strcmp(cmd, "run") == 0) {
        experiment_running = 1;
        pot_cell_enable(1);
        display_show_running(current_mode);

        switch (current_mode) {
        case MODE_CV:
            cv_run(&params);
            break;
        case MODE_DPV:
            dpv_run(&params);
            break;
        case MODE_SWV:
            swv_run(&params);
            break;
        case MODE_EIS:
            eis_run(&params);
            break;
        case MODE_AMPEROMETRIC:
            amperometric_run(&params);
            break;
        case MODE_GALVANOSTATIC:
            /* Galvanostatic: constant current, measure potential */
            galvanostatic_run(&params);
            break;
        default:
            break;
        }

        experiment_running = 0;
        pot_cell_enable(0);
        display_show_idle();
        return;
    }

    if (strcmp(cmd, "stop") == 0) {
        experiment_running = 0;
        pot_cell_enable(0);
        printf("Stopped.\r\n");
        return;
    }

    if (strcmp(cmd, "auto") == 0) {
        tia_range_t range = pot_auto_range();
        printf("TIA auto-range: %s\r\n", tia_range_name(range));
        return;
    }

    if (strcmp(cmd, "status") == 0) {
        cmd_status();
        return;
    }

    if (strcmp(cmd, "help") == 0) {
        cmd_help();
        return;
    }

    printf("Unknown command. Type 'help'.\r\n");
}

/* ── Button / encoder handling ─────────────────────────────────── */

static volatile int btn_mode_pressed = 0;
static volatile int btn_start_pressed = 0;
static volatile int encoder_delta = 0;

void HAL_GPIO_EXTI_Callback(uint16_t pin)
{
    if (pin == (1U << 11)) btn_mode_pressed  = 1;   /* PC11 */
    if (pin == (1U << 12)) btn_start_pressed = 1;   /* PC12 */
}

/* ── Main ──────────────────────────────────────────────────────── */

int main(void)
{
    /* HAL init */
    HAL_Init();
    SystemClock_Config();  /* 170 MHz, HSE 8 MHz via PLL */

    /* Peripheral init */
    pot_init();       /* Potentiostat DAC + TIA + control amp */
    dsp_init();       /* CORDIC & math tables */
    display_init();   /* SSD1306 I2C OLED */
    sdlog_init();     /* SD card SPI */
    ble_relay_init(); /* UART to ESP32-C3 */

    printf("\r\n=== Volt Scribe v1.0 ===\r\n");
    printf("Portable Electrochemical Workstation\r\n");
    cmd_help();

    display_show_splash();
    HAL_Delay(1500);
    display_show_idle();

    /* Super-loop */
    while (1) {
        /* Handle mode button */
        if (btn_mode_pressed) {
            btn_mode_pressed = 0;
            current_mode = (technique_mode_t)((current_mode + 1) % MODE_COUNT);
            printf("Mode: %s\r\n", mode_names[current_mode]);
            display_show_mode(current_mode);
        }

        /* Handle start button */
        if (btn_start_pressed && !experiment_running) {
            btn_start_pressed = 0;
            /* Same as "run" command */
            process_command("run");
        }

        /* Check UART for commands */
        uint8_t ch;
        if (HAL_UART_Receive(&huart1, &ch, 1, 0) == HAL_OK) {
            if (ch == '\r' || ch == '\n') {
                if (cmd_pos > 0) {
                    cmd_buf[cmd_pos] = '\0';
                    process_command(cmd_buf);
                    cmd_pos = 0;
                }
            } else if (cmd_pos < CMD_BUF_LEN - 1) {
                cmd_buf[cmd_pos++] = (char)ch;
            }
        }

        /* Relay BLE data */
        ble_relay_poll();

        HAL_Delay(1);
    }
}

/* ── System Clock Configuration (170 MHz from 8 MHz HSE) ──────── */

void SystemClock_Config(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};

    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_ON;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLM = 1;  /* 8 MHz / 1 = 8 MHz */
    osc.PLL.PLLN = 85; /* 8 MHz * 85 = 680 MHz VCO */
    osc.PLL.PLLP = 2;  /* 680 / 2 = 340 MHz (not used) */
    osc.PLL.PLLQ = 4;  /* 680 / 4 = 170 MHz */
    osc.PLL.PLLR = 2;  /* 680 / 2 = 340 MHz sys */
    HAL_RCC_OscConfig(&osc);

    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                    RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV2;  /* 170 MHz */
    clk.APB1CLKDivider = RCC_HCLK_DIV1;   /* 170 MHz */
    clk.APB2CLKDivider = RCC_HCLK_DIV1;   /* 170 MHz */
    HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_4);
}

/* Hard fault handler */
void HardFault_Handler(void)
{
    while (1) {
        HAL_GPIO_TogglePin(GPIOB, GPIO_PIN_10); /* red LED blink */
        for (volatile int i = 0; i < 1000000; i++);
    }
}