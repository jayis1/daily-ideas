/*
 * main.c — Quartz Tuner application entry point
 *
 * Initializes all subsystems and runs the main measurement loop.
 * Built for STM32G491RET6 with STM32 HAL + FreeRTOS.
 */

#include "types.h"
#include "si5351.h"
#include "ad5933.h"
#include "sweep.h"
#include "motional.h"
#include "admittance.h"
#include "allan.h"
#include "turnover.h"
#include "classify.h"
#include "display.h"
#include "sdlog.h"
#include "ble.h"
#include "heater.h"
#include "freqcount.h"
#include "calibrate.h"
#include "power.h"

#include "stm32g4xx_hal.h"
#include <stdio.h>
#include <string.h>

/* Global state */
static crystal_t g_crystal;
static device_state_t g_state = STATE_IDLE;
static display_mode_t g_display_mode = DISPLAY_PARAMS;
static uint32_t g_measurement_id = 0;
static bool g_btn_sweep_pressed = false;
static bool g_btn_cal_pressed = false;
static bool g_btn_mode_pressed = false;

/* FreeRTOS task handles */
static TaskHandle_t xSweepTask = NULL;
static TaskHandle_t xDisplayTask = NULL;
static TaskHandle_t xBleTask = NULL;

/* Button debounce */
#define DEBOUNCE_MS 50

static void btn_sweep_irq(void)
{
    static uint32_t last = 0;
    uint32_t now = HAL_GetTick();
    if (now - last > DEBOUNCE_MS) {
        g_btn_sweep_pressed = true;
        last = now;
    }
}

static void btn_cal_irq(void)
{
    static uint32_t last = 0;
    uint32_t now = HAL_GetTick();
    if (now - last > DEBOUNCE_MS) {
        g_btn_cal_pressed = true;
        last = now;
    }
}

static void btn_mode_irq(void)
{
    static uint32_t last = 0;
    uint32_t now = HAL_GetTick();
    if (now - last > DEBOUNCE_MS) {
        g_btn_mode_pressed = true;
        last = now;
    }
}

/*
 * Sweep task — runs a full frequency sweep, extracts parameters,
 * and optionally does temperature sweep and Allan deviation.
 */
static void vSweepTask(void *pvParameters)
{
    (void)pvParameters;

    while (1) {
        /* Wait for sweep button press */
        if (!g_btn_sweep_pressed) {
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }
        g_btn_sweep_pressed = false;

        /* Check if calibration is needed */
        if (!g_crystal.cal.valid) {
            g_state = STATE_ERROR;
            display_show_message("Not calibrated!\\nPress CAL first.");
            vTaskDelay(pdMS_TO_TICKS(2000));
            g_state = STATE_IDLE;
            continue;
        }

        /* Run frequency sweep */
        g_state = STATE_SWEEPING;
        display_show_message("Sweeping...");

        /* Set up sweep: center on nominal frequency, ±1% span */
        float f_center = g_crystal.sweep.f_center_hz;
        float span = g_crystal.sweep.span_hz;
        if (span < 10000.0f) span = f_center * 0.02f;  /* ±1% default */

        int rc = sweep_run(&g_crystal.sweep, f_center, span, 512);
        if (rc != 0) {
            g_state = STATE_ERROR;
            display_show_message("Sweep failed!");
            vTaskDelay(pdMS_TO_TICKS(2000));
            g_state = STATE_IDLE;
            continue;
        }

        /* Extract motional parameters */
        motional_extract(&g_crystal.sweep, &g_crystal.params, &g_crystal.cal);

        /* Classify crystal type */
        classify_crystal(&g_crystal.params, &g_crystal.classification);

        /* Log to SD */
        g_crystal.id = ++g_measurement_id;
        sdlog_save(&g_crystal);

        /* Stream over BLE */
        ble_notify_results(&g_crystal);

        g_state = STATE_DISPLAY_RESULTS;
        display_update(&g_crystal, g_display_mode);

        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

/*
 * Display task — handles mode button and screen updates.
 */
static void vDisplayTask(void *pvParameters)
{
    (void)pvParameters;

    while (1) {
        if (g_btn_mode_pressed) {
            g_btn_mode_pressed = false;
            g_display_mode = (g_display_mode + 1) % 5;
        }

        if (g_state == STATE_DISPLAY_RESULTS) {
            display_update(&g_crystal, g_display_mode);
        } else {
            display_show_state(g_state);
        }

        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

/*
 * BLE task — handles BLE GATT connections and streaming.
 */
static void vBleTask(void *pvParameters)
{
    (void)pvParameters;

    ble_init();
    ble_advertise("QuartzTuner");

    while (1) {
        ble_process();
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

/*
 * Calibration procedure — walks the user through OSLT calibration.
 */
static void run_calibration(void)
{
    g_state = STATE_CALIBRATING;

    /* Step 1: SHORT */
    display_show_message("CAL: Insert SHORT\\nPress SWEEP");
    while (!g_btn_sweep_pressed) { vTaskDelay(pdMS_TO_TICKS(50)); }
    g_btn_sweep_pressed = false;
    calibrate_short(&g_crystal.cal);

    /* Step 2: OPEN */
    display_show_message("CAL: Remove DUT\\n(OPEN) Press SWEEP");
    while (!g_btn_sweep_pressed) { vTaskDelay(pdMS_TO_TICKS(50)); }
    g_btn_sweep_pressed = false;
    calibrate_open(&g_crystal.cal);

    /* Step 3: LOAD (50 Ω) */
    display_show_message("CAL: Insert 50ohm\\nPress SWEEP");
    while (!g_btn_sweep_pressed) { vTaskDelay(pdMS_TO_TICKS(50)); }
    g_btn_sweep_pressed = false;
    calibrate_load(&g_crystal.cal);

    /* Step 4: THROUGH */
    display_show_message("CAL: Short series\\n(THRU) Press SWEEP");
    while (!g_btn_sweep_pressed) { vTaskDelay(pdMS_TO_TICKS(50)); }
    g_btn_sweep_pressed = false;
    calibrate_through(&g_crystal.cal);

    /* Done */
    g_crystal.cal.valid = true;
    display_show_message("CAL complete!\\nReady to measure.");
    vTaskDelay(pdMS_TO_TICKS(1500));
    g_state = STATE_IDLE;
}

/*
 * Temperature sweep — measures frequency vs temperature.
 */
static void run_temperature_sweep(void)
{
    g_state = STATE_TEMPERATURE_SWEEP;
    turnover_sweep(&g_crystal.turnover, &g_crystal.sweep, &g_crystal.cal);
    turnover_fit(&g_crystal.turnover);
    g_state = STATE_DISPLAY_RESULTS;
}

/*
 * Allan deviation measurement — counts frequency at multiple gate times.
 */
static void run_allan_measurement(void)
{
    g_state = STATE_ALLAN_MEASUREMENT;
    display_show_message("Allan dev...\\n1 minute");
    allan_measure(&g_crystal.allan, &g_crystal.sweep, &g_crystal.cal);
    g_state = STATE_DISPLAY_RESULTS;
}

int main(void)
{
    /* HAL initialization */
    HAL_Init();
    SystemClock_Config();

    /* Peripheral init */
    si5351_init();
    ad5933_init();
    display_init();
    sdlog_init();
    heater_init();
    freqcount_init();
    power_init();

    /* Configure GPIO for buttons */
    /* BTN_SWEEP  = PC0 (exti) */
    /* BTN_CAL    = PC1 (exti) */
    /* BTN_MODE   = PB15 (exti) */
    HAL_NVIC_SetPriority(EXTI0_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(EXTI0_IRQn);
    HAL_NVIC_SetPriority(EXTI1_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(EXTI1_IRQn);
    HAL_NVIC_SetPriority(EXTI15_10_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(EXTI15_10_IRQn);

    /* Default sweep parameters: 10 MHz center, ±1% span */
    g_crystal.sweep.f_center_hz = 10000000.0f;
    g_crystal.sweep.span_hz = 200000.0f;
    g_crystal.cal.valid = false;

    /* Splash screen */
    display_show_message("Quartz Tuner v1.0\\nPress CAL to start");
    HAL_Delay(2000);

    /* Create FreeRTOS tasks */
    xTaskCreate(vSweepTask, "sweep", 2048, NULL, 3, &xSweepTask);
    xTaskCreate(vDisplayTask, "display", 1024, NULL, 2, &xDisplayTask);
    xTaskCreate(vBleTask, "ble", 1024, NULL, 1, &xBleTask);

    /* Main loop handles calibration and special modes */
    while (1) {
        if (g_btn_cal_pressed) {
            g_btn_cal_pressed = false;
            run_calibration();
        }

        /* Check for long-press on SWEEP for temperature/Allan modes */
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

/* Interrupt handlers */
void EXTI0_IRQHandler(void) { btn_sweep_irq(); HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_0); }
void EXTI1_IRQHandler(void) { btn_cal_irq(); HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_1); }
void EXTI15_10_IRQHandler(void) { btn_mode_irq(); HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_15); }