/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * main.c — FreeRTOS task initialization and system entry point
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "stm32g474.h"     /* register definitions (minimal, generated) */

/* FreeRTOS */
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"
#include "timers.h"

#include "pulser.h"
#include "tgc.h"
#include "receiver.h"
#include "thickness.h"
#include "flaw.h"
#include "materials.h"
#include "calibration.h"
#include "display.h"
#include "sd_log.h"
#include "uart_proto.h"
#include "power.h"

/* ---- Task Handles ---- */
static TaskHandle_t hAcquireTask;
static TaskHandle_t hProcessTask;
static TaskHandle_t hUITask;
static TaskHandle_t hCommTask;

/* ---- Queues ---- */
QueueHandle_t xScanRequestQueue;      /* acquire ← process/ui: fire requests   */
QueueHandle_t xAscanResultQueue;      /* acquire → process: completed A-scans     */
QueueHandle_t xMeasurementQueue;      /* process → comm/ui: measurement results  */
QueueHandle_t xConfigQueue;           /* comm → process: config change requests  */

/* ---- Semaphores ---- */
SemaphoreHandle_t xSPIMutex;          /* OLED + SD share SPI1                    */
SemaphoreHandle_t xI2CMutex;           /* MAX17048 I²C                           */
SemaphoreHandle_t xConfigMutex;        /* protect shared config structs          */

/* ---- Global state ---- */
typedef struct {
    pulser_config_t       pulser;
    tgc_config_t          tgc;
    rx_config_t           rx;
    thickness_result_t    last_thickness;
    flaw_result_t         last_flaw;
    flaw_gate_t           flaw_gate;
    uint8_t               default_material_idx;
    uint8_t               battery_pct;
    power_state_t         power_state;
    uint8_t               continuous_running;
    uint32_t              measurement_seq;
} system_state_t;

static system_state_t g_state;

/* ---- System clock setup (PLL: HSI16 → 170 MHz) ---- */
static void clock_init(void)
{
    /* Enable HSI16 and wait */
    RCC->CR |= RCC_CR_HSION;
    while (!(RCC->CR & RCC_CR_HSIRDY)) { }

    /* Configure PLL: HSI16 → /4 → ×85 → /2 = 170 MHz */
    RCC->PLLCFGR = (4U << RCC_PLLCFGR_PLLM_Pos) |
                   (85U << RCC_PLLCFGR_PLLN_Pos) |
                   (RCC_PLLCFGR_PLLR_2 << RCC_PLLCFGR_PLLR_Pos) |  /* /2 */
                   (0 << RCC_PLLCFGR_PLLSRC_Pos);                   /* HSI16 */
    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY)) { }

    /* Flash latency 5 wait states for 170 MHz */
    FLASH->ACR = FLASH_ACR_LATENCY_5WS | FLASH_ACR_PRFTEN |
                 FLASH_ACR_ICEN | FLASH_ACR_DCEN;

    /* Switch SYSCLK to PLL */
    RCC->CFGR = (RCC_CFGR_SW_PLL << RCC_CFGR_SW_Pos);
    while (((RCC->CFGR & RCC_CFGR_SWS_Msk) >> RCC_CFGR_SWS_Pos) !=
           RCC_CFGR_SW_PLL) { }

    SystemCoreClock = SYSCLK_HZ;
}

/* ---- GPIO initial setup ---- */
static void gpio_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN |
                    RCC_AHB2ENR_GPIOCEN;

    /* Status LEDs (PB6/PB7/PB8) — output, push-pull */
    GPIOB->MODER = (GPIOB->MODER & ~(GPIO_MODER_MODE6 | GPIO_MODER_MODE7 |
                                      GPIO_MODER_MODE8)) |
                   (1U << GPIO_MODER_MODE6_Pos) | (1U << GPIO_MODER_MODE7_Pos) |
                   (1U << GPIO_MODER_MODE8_Pos);
    GPIOB->OTYPER &= ~(GPIO_OTYPER_OT6 | GPIO_OTYPER_OT7 | GPIO_OTYPER_OT8);
    GPIOB->BSRR = (1U << (16 + 6));   /* white off (active low for some) */

    /* Trigger button (PA10), menu (PB14), mode (PB15) — input, pull-up */
    GPIOA->MODER &= ~(GPIO_MODER_MODE10);
    GPIOA->PUPDR |= (1U << GPIO_PUPDR_PUPD10_Pos);
    GPIOB->MODER &= ~(GPIO_MODER_MODE14 | GPIO_MODER_MODE15);
    GPIOB->PUPDR |= (1U << GPIO_PUPDR_PUPD14_Pos) | (1U << GPIO_PUPDR_PUPD15_Pos);

    /* Rotary encoder A/B (PA11/PA12) — input, pull-up */
    GPIOA->MODER &= ~(GPIO_MODER_MODE11 | GPIO_MODER_MODE12);
    GPIOA->PUPDR |= (1U << GPIO_PUPDR_PUPD11_Pos) | (1U << GPIO_PUPDR_PUPD12_Pos);
}

/* ---- NVIC priority grouping for FreeRTOS ---- */
static void nvic_init(void)
{
    /* 4 bits preemption, 0 bits sub-priority */
    NVIC_SetPriorityGrouping(3);
    /* Set interrupt priorities (all use FreeRTOS-aware calls in init) */
}

/* ---- Default state initialization ---- */
static void state_init(void)
{
    g_state.pulser.mode            = PULSE_MODE_NEG_SPIKE;
    g_state.pulser.width_ns         = PULSE_WIDTH_NS_DEFAULT;
    g_state.pulser.hv_voltage_mv    = HV_VOLTAGE_DEFAULT_MV;
    g_state.pulser.prf_hz           = PRF_HZ_DEFAULT;
    g_state.pulser.burst_cycles     = 1;
    g_state.pulser.armed            = 0;

    g_state.tgc.shape               = TGC_SHAPE_LINEAR;
    g_state.tgc.start_db            = LNA_GAIN_MID_DB;
    g_state.tgc.end_db               = LNA_GAIN_MID_DB + 30.0f;
    g_state.tgc.window_us            = (uint16_t)CAPTURE_WINDOW_US_DEFAULT;
    g_state.tgc.lna_gain_idx         = 1;

    g_state.rx.window_us            = (uint16_t)CAPTURE_WINDOW_US_DEFAULT;
    g_state.rx.sample_count         = (uint16_t)(CAPTURE_WINDOW_US_DEFAULT *
                                                  (ADC_SAMPLE_RATE_HZ / 1000000.0f));
    g_state.rx.source               = 0;   /* envelope only */
    g_state.rx.trigger_channel      = 0;

    g_state.last_thickness.valid    = 0;
    g_state.last_flaw.detected      = 0;
    g_state.flaw_gate.start_us      = 5;
    g_state.flaw_gate.width_us      = 80;
    g_state.flaw_gate.threshold     = 200;
    g_state.flaw_gate.enabled       = 0;

    g_state.default_material_idx    = 0;  /* steel */
    g_state.battery_pct             = 100;
    g_state.power_state             = POWER_STATE_RUN;
    g_state.continuous_running      = 0;
    g_state.measurement_seq         = 0;
}

/* ===================================================================== */
/*  Acquire Task — fires pulser + captures ADC                            */
/* ===================================================================== */
static void AcquireTask(void *arg)
{
    (void)arg;
    uint8_t req;

    for (;;) {
        /* Wait for a fire request from UI (trigger) or process (continuous) */
        if (xQueueReceive(xScanRequestQueue, &req, portMAX_DELAY) == pdTRUE) {
            if (!g_state.pulser.armed) continue;

            /* Arm AFE + HV if needed */
            power_enable_afe(1);
            power_enable_hv(1);
            vTaskDelay(pdMS_TO_TICKS(2));   /* HV boost settle (~2 ms) */

            /* Synchronize TGC ramp with the pulse */
            tgc_arm();

            /* Start ADC DMA capture (timer-triggered) */
            receiver_start_continuous();

            /* Fire the pulser — single or continuous handled by PRF timer */
            if (g_state.continuous_running) {
                pulser_start_continuous();
            } else {
                pulser_fire_single();
            }

            /* Wait for the acquisition to complete (process task consumes) */
            ascan_t scan;
            uint8_t got = rx_get_latest(&scan);
            if (got) {
                xQueueSend(xAscanResultQueue, &scan, 0);
            }

            /* Tear down analog if idle */
            if (!g_state.continuous_running) {
                pulser_stop_continuous();
                receiver_stop_continuous();
                tgc_disarm();
                power_enable_hv(0);
                power_enable_afe(0);
            }
        }
    }
}

/* ===================================================================== */
/*  Process Task — thickness/flaw computation + logging + display        */
/* ===================================================================== */
static void ProcessTask(void *arg)
{
    (void)arg;
    ascan_t scan;
    thickness_result_t thk;
    flaw_result_t flaw;
    log_entry_t entry;

    for (;;) {
        if (xQueueReceive(xAscanResultQueue, &scan, portMAX_DELAY) == pdTRUE) {
            /* Compute thickness based on active mode */
            const material_t *mat = materials_get(g_state.default_material_idx);

            switch (g_state.last_thickness.mode) {
            case MEASURE_MODE_ECHO_ECHO:
                thickness_echo_echo(&scan, &g_state.last_thickness, &thk);
                break;
            case MEASURE_MODE_FLAW:
                thickness_compute(&scan, &g_state.last_thickness, &thk);
                flaw_evaluate(&scan, &thk, &flaw);
                break;
            case MEASURE_MODE_PULSE_ECHO:
            default:
                thickness_compute(&scan, &g_state.last_thickness, &thk);
                break;
            }

            /* Apply zero-probe offset from calibration */
            const calibration_t *cal = calibration_get();
            thk.zero_offset_ns = cal->zero_offset_ns;

            g_state.last_thickness = thk;
            g_state.last_flaw       = flaw;

            /* Update display (UI task actually draws; we just signal) */
            xQueueSend(xMeasurementQueue, &thk, 0);

            /* Send to ESP32-C3 for BLE streaming */
            uart_send_measurement(&thk, &flaw, mat ? mat->name : "?",
                                   g_state.battery_pct);

            /* Log to SD */
            entry.sequence      = ++g_state.measurement_seq;
            entry.timestamp      = 0;   /* filled by ESP32-C3 RTC sync */
            entry.thickness_mm  = thk.thickness_mm;
            entry.tof_ns         = thk.tof_ns;
            entry.velocity_mps   = mat ? mat->velocity_mps : 5920;
            entry.mode           = (uint8_t)thk.mode;
            entry.flaw_detected  = flaw.detected;
            entry.flaw_depth_mm  = flaw.depth_mm;
            entry.flaw_equiv_mm  = flaw.equiv_mm;
            entry.gain_db        = g_state.tgc.end_db;
            entry.battery_pct    = (int16_t)g_state.battery_pct;
            if (mat) {
                for (uint8_t i = 0; i < MATERIAL_NAME_MAX && mat->name[i]; i++)
                    entry.material[i] = mat->name[i];
            }
            sd_log_measurement(&entry);

            /* Trigger beep on flaw detection */
            if (flaw.detected) {
                power_update(NULL);
            }
        }
    }
}

/* ===================================================================== */
/*  UI Task — OLED draw, rotary encoder, buttons, menus                   */
/* ===================================================================== */
static void UITask(void *arg)
{
    (void)arg;
    thickness_result_t thk;
    ascan_t scan;
    TickType_t last_wake = xTaskGetTickCount();

    for (;;) {
        /* Drain any new measurement */
        if (xQueueReceive(xMeasurementQueue, &thk, 0) == pdTRUE) {
            /* updated; display will refresh below */
        }

        /* Poll input (encoder/buttons) — implemented in display.c */
        display_menu_select();

        /* Render current page */
        switch (display_get_page()) {
        case UI_PAGE_ASCAN:
            if (rx_get_latest(&scan)) {
                const material_t *mat = materials_get(g_state.default_material_idx);
                display_draw_ascan(&scan, &g_state.last_thickness,
                                    &g_state.last_flaw,
                                    mat ? mat->name : "?",
                                    g_state.battery_pct);
            }
            break;
        case UI_PAGE_MENU:
            display_menu_draw();
            break;
        case UI_PAGE_CALIBRATE:
            display_text_f(0, 0, "CALIBRATE");
            display_text_f(0, 16, "Place probe on");
            display_text_f(0, 24, "reference block");
            display_text_f(0, 40, "Press trigger");
            break;
        case UI_PAGE_LOG:
            display_text_f(0, 0, "LOG: %lu", sd_log_count());
            display_text_f(0, 24, "Last: %.2f mm",
                           g_state.last_thickness.thickness_mm);
            break;
        case UI_PAGE_INFO:
            display_text_f(0, 0, "Ping Caliper v1.0");
            display_text_f(0, 16, "Bat: %d%%", g_state.battery_pct);
            display_text_f(0, 32, "HV: %umV", pulser_read_hv());
            display_text_f(0, 48, "PRF: %uHz", g_state.pulser.prf_hz);
            break;
        }
        display_flush();

        vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(50));   /* 20 Hz UI */
    }
}

/* ===================================================================== */
/*  Comm Task — UART protocol handler + power monitor                     */
/* ===================================================================== */
static void CommTask(void *arg)
{
    (void)arg;
    power_t pwr;
    TickType_t last_wake = xTaskGetTickCount();

    for (;;) {
        /* Poll UART for incoming commands from ESP32-C3 */
        uart_proto_poll();

        /* Power/battery update every 5 s */
        power_update(&pwr);
        g_state.battery_pct = pwr.battery_pct;
        if (pwr.battery_pct <= BATTERY_CRIT_PCT) {
            power_low_battery_handler();
        }

        vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(200));
    }
}

/* ===================================================================== */
/*  Application entry point                                                */
/* ===================================================================== */
int main(void)
{
    /* Hardware bring-up */
    clock_init();
    nvic_init();
    gpio_init();

    /* Initialize all subsystems */
    state_init();
    materials_init();
    materials_load_from_flash();
    calibration_init();
    calibration_load((calibration_t *)calibration_get());
    pulser_init();
    tgc_init();
    receiver_init();
    flaw_init();
    display_init();
    sd_init();
    uart_proto_init();
    power_init();

    /* Create queues */
    xScanRequestQueue    = xQueueCreate(QUEUE_LEN, sizeof(uint8_t));
    xAscanResultQueue    = xQueueCreate(2,   sizeof(ascan_t));
    xMeasurementQueue    = xQueueCreate(8,   sizeof(thickness_result_t));
    xConfigQueue         = xQueueCreate(4,   sizeof(uint32_t));

    /* Create mutexes */
    xSPIMutex    = xSemaphoreCreateMutex();
    xI2CMutex    = xSemaphoreCreateMutex();
    xConfigMutex = xSemaphoreCreateMutex();

    /* Create tasks */
    xTaskCreate(AcquireTask, "acquire", TASK_STACK_ACQUIRE, NULL,
                TASK_PRIO_ACQUIRE, &hAcquireTask);
    xTaskCreate(ProcessTask, "process", TASK_STACK_PROCESS, NULL,
                TASK_PRIO_PROCESS, &hProcessTask);
    xTaskCreate(UITask,       "ui",      TASK_STACK_UI, NULL,
                TASK_PRIO_UI, &hUITask);
    xTaskCreate(CommTask,     "comm",    TASK_STACK_COMM, NULL,
                TASK_PRIO_COMM, &hCommTask);

    /* Welcome beep + display */
    display_text(0, 0, "Ping Caliper");
    display_text(0, 16, "Booting...");
    display_flush();

    /* Start scheduler */
    vTaskStartScheduler();

    /* Should never reach here */
    for (;;) { }
}

/* ---- FreeRTOS hooks ---- */
void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
    (void)xTask; (void)pcTaskName;
    for (;;) { }
}

void vApplicationMallocFailedHook(void)
{
    for (;;) { }
}

void vApplicationIdleHook(void)
{
    __WFI();
}

/* ---- Weak stubs for HAL/ISR references ---- */
void SysTick_Handler(void)
{
    if (xTaskGetSchedulerState() != taskSCHEDULER_NOT_STARTED) {
        xPortSysTickHandler();
    }
}