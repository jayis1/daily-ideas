/*
 * main.c — Iono Pin top-level state machine
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * States: IDLE -> PURGE -> SAMPLE -> (loop accumulate) -> CLASSIFY -> REPORT
 *          | FAULT (any time)
 *
 * SPDX-License-Identifier: MIT
 */
#include "stm32g474_conf.h"
#include "stm32g4xx_hal.h"
#include <string.h>
#include <stdio.h>

#include "ims.h"
#include "library.h"
#include "hv_supply.h"
#include "shutter.h"
#include "ionizer.h"
#include "electrometer.h"
#include "pump.h"
#include "bme280.h"
#include "ds18b20.h"
#include "display.h"
#include "sd_log.h"
#include "ble_bridge.h"
#include "safety.h"
#include "buttons.h"

/* HAL handles (defined here; configured by HAL MSP in a full CubeMX project) */
ADC_HandleTypeDef hadc1, hadc2;
TIM_HandleTypeDef htim1, htim2, htim6, htim7;
SPI_HandleTypeDef hspi2, hspi3;
I2C_HandleTypeDef hi2c1;
UART_HandleTypeDef huart2;

static float g_batt_v = 0.0f;
static float g_p_kpa = 101.3f, g_t_amb = 22.0f, g_t_drift = 22.0f;

static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef o = {0};
    o.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    o.HSIState = RCC_HSI_ON;
    o.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    o.PLL.PLLState = RCC_PLL_ON;
    o.PLL.PLLSource = RCC_PLLSOURCE_HSI;
    o.PLL.PLLM = 4;
    o.PLL.PLLN = 42;
    o.PLL.PLLR = 2;
    o.PLL.PLLP = RCC_PLLP_DIV7;
    o.PLL.PLLQ = 2;
    HAL_RCC_OscConfig(&o);
    RCC_ClkInitTypeDef c = {0};
    c.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                  RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    c.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    c.AHBCLKDivider = RCC_SYSCLK_DIV1;
    c.APB1CLKDivider = RCC_HCLK_DIV1;
    c.APB2CLKDivider = RCC_HCLK_DIV1;
    HAL_RCC_ClockConfig(&c, FLASH_LATENCY_2);
}

void SystemInit(void) { /* called from startup */ }

static float read_battery(void)
{
    /* PB0 ADC2 channel 0, 2:1 divider from 18650 (3.0-4.2V) */
    ADC_ChannelConfTypeDef ch = {0};
    ch.Channel = ADC_CHANNEL_15;   /* PB0 maps to ADC2_IN15 on G474 */
    ch.Rank = 1;
    ch.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
    HAL_ADC_ConfigChannel(&hadc2, &ch);
    HAL_ADC_Start(&hadc2);
    HAL_ADC_PollForConversion(&hadc2, 5);
    uint32_t v = HAL_ADC_GetValue(&hadc2);
    HAL_ADC_Stop(&hadc2);
    return (float)v / 4095.0f * 3.0f * 2.0f;
}

static void init_peripherals(void)
{
    /* TIM2 CH1 — EMCO control PWM (1 MHz, ARR=100) */
    htim2.Instance = TIM2;
    htim2.Init.Prescaler = (PCLK1_HZ / 1000000UL) - 1;
    htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim2.Init.Period = 99;
    htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    HAL_TIM_PWM_Init(&htim2);
    TIM_OC_InitTypeDef oc = {0};
    oc.OCMode = TIM_OCMODE_PWM1;
    oc.Pulse = 0; oc.OCPolarity = TIM_OCPOLARITY_HIGH;
    HAL_TIM_PWM_ConfigChannel(&htim2, &oc, TIM_CHANNEL_1);
    /* TIM2 CH2 — pump PWM (25 kHz) */
    htim2.Init.Prescaler = 0;
    htim2.Init.Period = (PCLK1_HZ / 25000UL) - 1;
    HAL_TIM_PWM_Init(&htim2);
    oc.Pulse = 0;
    HAL_TIM_PWM_ConfigChannel(&htim2, &oc, TIM_CHANNEL_2);

    /* TIM6 — shutter rep rate (1 MHz base) */
    htim6.Instance = TIM6;
    htim6.Init.Prescaler = (PCLK1_HZ / 1000000UL) - 1;
    htim6.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim6.Init.Period = 1000000UL / IMS_REP_RATE_HZ - 1;
    HAL_TIM_Base_Init(&htim6);

    /* TIM7 — shutter pulse width 200us (1 MHz base, ARR=200) */
    htim7.Instance = TIM7;
    htim7.Init.Prescaler = (PCLK1_HZ / 1000000UL) - 1;
    htim7.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim7.Init.Period = 199;
    HAL_TIM_Base_Init(&htim7);

    /* ADC1 — PA0, 12-bit, TIM1_TRGO triggered, DMA */
    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV1;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc1.Init.LowPowerAutoWait = DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.NbrOfConversion = 1;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConv = ADC_EXTERNALTRIG_T1_TRGO;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_RISING;
    HAL_ADC_Init(&hadc1);
    ADC_ChannelConfTypeDef ac = {0};
    ac.Channel = ADC_CHANNEL_1;
    ac.Rank = 1;
    ac.SamplingTime = ADC_SAMPLETIME_24CYCLES_5;
    HAL_ADC_ConfigChannel(&hadc1, &ac);

    /* ADC2 — PA1 (HV mon) + PB0 (battery), software-triggered */
    hadc2.Instance = ADC2;
    hadc2.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV1;
    hadc2.Init.Resolution = ADC_RESOLUTION_12B;
    hadc2.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc2.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc2.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc2.Init.ContinuousConvMode = DISABLE;
    hadc2.Init.NbrOfConversion = 1;
    hadc2.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    HAL_ADC_Init(&hadc2);
    HAL_ADCEx_Calibration_Start(&hadc2, ADC_SINGLE_ENDED);

    /* TIM1 — ADC1 trigger @ 40 ksps */
    htim1.Instance = TIM1;
    htim1.Init.Prescaler = 0;
    htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim1.Init.Period = (PCLK2_HZ / IMS_SAMPLE_RATE) - 1;
    HAL_TIM_Base_Init(&htim1);
    TIM_MasterConfigTypeDef mc = {0};
    mc.MasterOutputTrigger = TIM_TRGO_UPDATE;
    HAL_TIMEx_MasterConfigSynchronization(&htim1, &mc);

    /* UART2 — ESP32-C3 bridge @ 921600 */
    huart2.Instance = USART2;
    huart2.Init.BaudRate = BRIDGE_BAUD;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    HAL_UART_Init(&huart2);

    /* I2C1 — BME280 + OLED, 400 kHz */
    hi2c1.Instance = I2C1;
    hi2c1.Init.Timing = 0x10909CEC;   /* 400 kHz @ 170 MHz */
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    HAL_I2C_Init(&hi2c1);
}

/* TIM6 update IRQ — shutter rep tick */
void TIM6_DAC_IRQHandler(void)
{
    if (__HAL_TIM_GET_FLAG(&htim6, TIM_FLAG_UPDATE)) {
        __HAL_TIM_CLEAR_FLAG(&htim6, TIM_FLAG_UPDATE);
        extern void shutter_on_rep_tick(void);
        shutter_on_rep_tick();
    }
}
/* TIM7 update IRQ — shutter pulse end */
void TIM7_IRQHandler(void)
{
    if (__HAL_TIM_GET_FLAG(&htim7, TIM_FLAG_UPDATE)) {
        __HAL_TIM_CLEAR_FLAG(&htim7, TIM_FLAG_UPDATE);
        extern void shutter_on_pulse_end(void);
        shutter_on_pulse_end();
    }
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    init_peripherals();

    /* subsystem init */
    safety_init();
    hv_init();
    shutter_init();
    ionizer_init();
    electrometer_init();
    pump_init();
    bme280_init();
    ds18b20_init();
    display_init();
    sdlog_init();
    ble_bridge_init();
    buttons_init();
    ims_init();

    display_splash();
    HAL_Delay(800);
    display_idle();

    typedef enum { ST_IDLE, ST_PURGE, ST_SAMPLE, ST_CLASSIFY, ST_FAULT } state_t;
    state_t st = ST_IDLE;
    ims_result_t result;
    classify_result_t cls;

    while (1) {
        safety_tick();
        if (safety_fault()) { st = ST_FAULT; }

        button_t btn = buttons_poll();
        if (btn == BTN_MODE && st != ST_FAULT) {
            /* cycle rep rate 20/30/40 Hz */
            uint32_t r = shutter_get_rep_rate();
            shutter_set_rep_rate_hz(r >= 40 ? 20 : r + 10);
        }
        if (btn == BTN_CAL && st == ST_IDLE) {
            /* calibration: run blank (drift gas only) to capture RIP reference */
            st = ST_PURGE;
        }
        if (btn == BTN_SCAN && st == ST_IDLE) {
            st = ST_PURGE;
        }

        switch (st) {
        case ST_IDLE:
            display_status("IDLE", hv_read_drift_v(), g_batt_v, g_p_kpa, g_t_amb);
            HAL_Delay(100);
            break;
        case ST_PURGE:
            /* enable pump + HV + ionizer, purge for 2 s */
            if (safety_interlock_closed()) {
                pump_enable(true);
                valve_set_sample(false);
                hv_enable(true);
                hv_set_drift_v(HV_DRIFT_TARGET_V);
                HAL_Delay(200);
                ionizer_enable(true);
                shutter_arm(true);
                HAL_TIM_Base_Start(&htim1);   /* start ADC trigger */
                ims_reset_avg();
                display_status("PURGE", hv_read_drift_v(), g_batt_v, g_p_kpa, g_t_amb);
                HAL_Delay(2000);
                valve_set_sample(true);
                st = ST_SAMPLE;
            } else {
                display_fault("LID OPEN");
                st = ST_IDLE;
            }
            break;
        case ST_SAMPLE:
            /* accumulate sweeps until IMS_AVG_COUNT reached or timeout */
            if (electrometer_sweep_ready()) {
                int16_t buf[IMS_SAMPLES_PER_SWEEP];
                electromer_get(buf, IMS_SAMPLES_PER_SWEEP);
                ims_accumulate(buf);
            }
            /* periodically read ambient conditions */
            bme280_read(&g_t_amb, &g_p_kpa, NULL);
            ds18b20_read(&g_t_drift);
            g_batt_v = read_battery();
            if (ims_result_ready()) {
                st = ST_CLASSIFY;
            }
            /* timeout after ~15s */
            {
                static uint32_t sample_start = 0;
                if (sample_start == 0) sample_start = HAL_GetTick();
                if (HAL_GetTick() - sample_start > 15000) {
                    sample_start = 0;
                    st = ST_CLASSIFY;
                }
                if (st != ST_SAMPLE) sample_start = 0;
            }
            break;
        case ST_CLASSIFY:
            ims_compute(g_p_kpa, g_t_drift, g_t_amb, &result);
            library_classify(result.peaks, result.num_peaks, &cls);
            display_spectrum(&result, &cls);
            sdlog_log_spectrum(&result, &cls);
            ble_bridge_send_spectrum(&result, &cls);
            /* audible feedback: beep on positive hit */
            if (cls.cls == CLASS_EXPLOSIVE || cls.cls == CLASS_CWA || cls.cls == CLASS_DRUG) {
                HAL_GPIO_TogglePin(GPIOB, GPIO_PIN_6);
                HAL_Delay(80); HAL_GPIO_TogglePin(GPIOB, GPIO_PIN_6);
            }
            /* return to sample loop for continuous monitoring */
            st = ST_SAMPLE;
            break;
        case ST_FAULT:
            shutter_arm(false);
            ionizer_enable(false);
            hv_emergency_shutdown();
            pump_enable(false);
            display_fault(safety_fault_msg());
            ble_bridge_send_status(safety_fault_msg());
            if (btn == BTN_MODE) safety_clear_fault();
            HAL_Delay(200);
            if (!safety_fault()) st = ST_IDLE;
            break;
        }
    }
}

void HAL_Delay(uint32_t ms) { HAL_Delay(ms); }   /* provided by HAL */