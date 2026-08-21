/**
 * main.c — Brew Sense Fermentation Monitor
 * 
 * STM32L476RG-based precision fermentation tracker with:
 * - Vibrating tube densitometer for specific gravity
 * - DS18B20 temperature probe
 * - Senseair S8 NDIR CO₂ sensor
 * - EZO-pH pH probe interface
 * - BMP388 barometric pressure
 * - BLE 5.2 + Wi-Fi (via ESP32-C3) connectivity
 * - SSD1306 OLED display
 * - Buzzer + RGB LED alarms
 * 
 * Target: 30 days on 2× AAA alkaline batteries
 */

#include "stm32l4xx_hal.h"
#include <stdio.h>
#include <string.h>

#include "sensor_manager.h"
#include "densitometer.h"
#include "fermentation.h"
#include "ble_service.h"
#include "wifi_uplink.h"
#include "power_manager.h"
#include "display.h"
#include "alarm.h"
#include "calibration.h"

/* Configuration defaults */
#define SAMPLE_INTERVAL_SEC      60    /* 1 minute between samples */
#define WIFI_PUSH_INTERVAL_SEC   300   /* 5 minutes between Wi-Fi pushes */
#define DISPLAY_TIMEOUT_SEC      30    /* Display turns off after 30s */
#define BATTERY_LOW_THRESHOLD    2.2f  /* Low battery threshold in V */

/* Global state */
static sensor_data_t g_sensor_data;
static fermentation_state_t g_ferment_state;
static densitometer_result_t g_dens_result;
static calibration_data_t g_calibration;
static bool g_wifi_push_enabled = false;
static uint32_t g_wifi_timer = 0;
static uint32_t g_sample_count = 0;

/* Function prototypes */
static void SystemClock_Config(void);
static void Error_Handler(void);
static void update_all_sensors(void);
static void update_all_outputs(void);
static void handle_serial_commands(void);

int main(void) {
    /* HAL initialization */
    HAL_Init();
    SystemClock_Config();
    
    /* Enable instruction cache for performance */
    __HAL_FLASH_INSTRUCTION_CACHE_ENABLE();
    __HAL_FLASH_DATA_CACHE_ENABLE();
    __HAL_FLASH_PREFETCH_BUFFER_ENABLE();
    
    /* Initialize power manager first */
    power_config_t pwr_cfg = {
        .sample_interval_sec = SAMPLE_INTERVAL_SEC,
        .wifi_push_interval_sec = WIFI_PUSH_INTERVAL_SEC,
        .display_timeout_sec = DISPLAY_TIMEOUT_SEC,
        .enable_wifi = true,
        .enable_display = true,
        .enable_buzzer = true,
        .low_battery_threshold = BATTERY_LOW_THRESHOLD,
    };
    power_manager_init(&pwr_cfg);
    
    /* Initialize sensors */
    sensor_config_t sensor_cfg = {
        .sample_interval_ms = SAMPLE_INTERVAL_SEC * 1000,
        .enable_co2 = true,
        .enable_ph = true,
        .enable_gravity = true,
        .enable_pressure = true,
    };
    
    sensor_status_t status = sensor_manager_init(&sensor_cfg);
    if (status != SENSOR_OK) {
        /* Some sensors may have failed — continue anyway */
        printf("Sensor init warnings: 0x%02X\r\n", status);
    }
    
    /* Initialize densitometer */
    densitometer_config_t dens_cfg = {
        .sweep_start_hz = 1000,
        .sweep_end_hz = 8000,
        .sweep_step_hz = 10,
        .settle_time_us = 500,
        .num_averages = 3,
    };
    densitometer_init(&dens_cfg);
    
    /* Initialize fermentation engine */
    fermentation_config_t ferm_cfg = {
        .og = 1.050f,           /* Default OG — user can change via BLE */
        .fg_target = 1.010f,    /* Default FG target */
        .stuck_threshold_hr = 48,
        .stable_sg_delta = 0.001f,
        .sample_interval_min = 1,
    };
    fermentation_init(&ferm_cfg);
    
    /* Initialize BLE */
    if (ble_service_init() != 0) {
        printf("BLE init failed — running without BLE\r\n");
    }
    
    /* Initialize Wi-Fi uplink (ESP32-C3) */
    if (wifi_uplink_init() != 0) {
        printf("Wi-Fi init failed — running without Wi-Fi\r\n");
        g_wifi_push_enabled = false;
    }
    
    /* Initialize display */
    if (display_init() != 0) {
        printf("Display init failed\r\n");
    }
    
    /* Initialize alarm */
    alarm_config_t alarm_cfg = {
        .enable_buzzer = true,
        .enable_led = true,
        .temp_high_threshold = 30.0f,
        .temp_low_threshold = 10.0f,
        .ph_low_threshold = 2.5f,
        .ph_high_threshold = 4.4f,
        .stuck_hours = 48,
        .alarm_on_finished = true,
        .alarm_on_stuck = true,
    };
    alarm_init(&alarm_cfg);
    
    /* Load calibration from flash */
    if (calibration_load(&g_calibration)) {
        /* Apply densitometer calibration */
        densitometer_cal_t dens_cal;
        dens_cal.f_air = g_calibration.dens_f_air;
        dens_cal.f_water = g_calibration.dens_f_water;
        dens_cal.t_cal = g_calibration.dens_t_cal;
        dens_cal.valid = g_calibration.dens_valid;
        densitometer_save_calibration(&dens_cal);
        
        printf("Calibration loaded (air=%.1f Hz, water=%.1f Hz)\r\n",
               g_calibration.dens_f_air, g_calibration.dens_f_water);
    } else {
        printf("No calibration found — please calibrate!\r\n");
        /* Blink LED to indicate uncalibrated state */
        alarm_set_led(255, 0, 0);  /* Red */
    }
    
    /* Start Senseair S8 continuous mode */
    s8_start_continuous();
    
    printf("Brew Sense initialized. Starting main loop.\r\n");
    
    /* ====== Main Loop ====== */
    while (1) {
        /* Read all sensors */
        update_all_sensors();
        
        /* Run densitometer sweep */
        float temp_c = g_sensor_data.temperature_c;
        if (densitometer_read_sg(temp_c, &g_dens_result) == 0 && g_dens_result.valid) {
            g_sensor_data.gravity_sg = g_dens_result.sg_temperature_compensated;
        }
        
        /* Update fermentation engine */
        fermentation_update(g_sensor_data.temperature_c,
                           g_sensor_data.gravity_sg,
                           g_sensor_data.co2_ppm,
                           g_sensor_data.ph,
                           g_sensor_data.pressure_hpa);
        
        /* Get fermentation state */
        ferment_stage_t stage = fermentation_get_stage();
        float activity = fermentation_get_activity_index();
        int8_t trend = fermentation_get_trend();
        uint8_t alerts = fermentation_get_alerts();
        
        /* Update BLE characteristics */
        ble_update_gravity(g_sensor_data.gravity_sg);
        ble_update_temperature(g_sensor_data.temperature_c);
        ble_update_co2(g_sensor_data.co2_ppm);
        ble_update_ph(g_sensor_data.ph);
        ble_update_pressure(g_sensor_data.pressure_hpa);
        ble_update_stage(stage);
        ble_update_activity(activity);
        ble_update_trend(trend);
        
        /* Update battery */
        uint8_t batt_pct = power_manager_get_battery_percent();
        ble_update_battery(batt_pct);
        
        /* Update display */
        if (display_is_on()) {
            display_page_t page = display_get_page();
            switch (page) {
                case DISPLAY_PAGE_MAIN:
                    display_render_main(g_sensor_data.gravity_sg,
                                       g_sensor_data.temperature_c,
                                       stage, activity);
                    break;
                case DISPLAY_PAGE_CO2_PH:
                    display_render_co2_ph(g_sensor_data.co2_ppm,
                                          g_sensor_data.ph);
                    break;
                case DISPLAY_PAGE_GRAPH:
                    display_render_graph(g_ferment_state.gravity_history,
                                        g_ferment_state.history_count,
                                        g_sensor_data.gravity_sg);
                    break;
                case DISPLAY_PAGE_STATUS:
                    display_render_status(batt_pct, wifi_get_rssi(),
                                         HAL_GetTick() / 3600000);
                    break;
            }
        }
        
        /* Check alarms */
        alarm_check(stage, g_sensor_data.gravity_sg,
                    g_sensor_data.temperature_c, g_sensor_data.ph, alerts);
        
        /* Wi-Fi push (every 5 minutes) */
        g_wifi_timer++;
        if (g_wifi_push_enabled && 
            (g_wifi_timer * SAMPLE_INTERVAL_SEC >= WIFI_PUSH_INTERVAL_SEC)) {
            if (wifi_is_connected()) {
                wifi_push_all(g_sensor_data.gravity_sg,
                             g_sensor_data.temperature_c,
                             g_sensor_data.co2_ppm,
                             g_sensor_data.ph,
                             g_sensor_data.pressure_hpa,
                             stage, activity);
            }
            g_wifi_timer = 0;
        }
        
        /* Handle serial commands */
        handle_serial_commands();
        
        /* Process BLE events */
        ble_process_events();
        
        /* Increment sample counter */
        g_sample_count++;
        
        /* Enter low-power mode until next sample */
        power_manager_sleep(POWER_MODE_STOP);
        power_manager_wake();
    }
}

/**
 * Read all sensors and populate g_sensor_data.
 */
static void update_all_sensors(void) {
    sensor_status_t status = sensor_manager_read_all(&g_sensor_data);
    
    if (status & SENSOR_DS18B20_ERR) {
        printf("DS18B20 read error\r\n");
    }
    if (status & SENSOR_BMP388_ERR) {
        printf("BMP388 read error\r\n");
    }
    if (status & SENSOR_S8_ERR) {
        printf("S8 CO2 read error\r\n");
    }
    if (status & SENSOR_EZO_PH_ERR) {
        printf("EZO-pH read error\r\n");
    }
    if (status & SENSOR_BATT_LOW) {
        printf("Low battery: %.2fV\r\n", g_sensor_data.battery_v);
    }
}

/**
 * Handle serial commands for calibration and configuration.
 * Commands are received via UART2 (debug port).
 * 
 * Supported commands:
 *   CALS,air      — Air calibration for densitometer
 *   CALS,water    — Water calibration (at current temp)
 *   CALS,ph4      — pH 4.0 buffer calibration
 *   CALS,ph7      — pH 7.0 buffer calibration
 *   CALR           — Read calibration data
 *   OG,1.050       — Set original gravity
 *   FG,1.010       — Set target final gravity
 *   RESET          — Reset fermentation engine
 *   WIFI,ssid,pass — Configure Wi-Fi
 */
static void handle_serial_commands(void) {
    /* UART RX would be handled via interrupt and ring buffer */
    /* This is a simplified implementation for illustration */
    
    /* In production, this would use a UART RX interrupt handler */
    /* and a command parser. For now, the interface is defined */
    /* and the full implementation would go in a separate module. */
}

/**
 * System Clock Configuration
 * STM32L476RG @ 80MHz (low-power run) or 120MHz (normal)
 * 
 * Using MSI clock (4MHz) for low-power mode,
 * PLL with HSI16 for active mode (80MHz).
 */
static void SystemClock_Config(void) {
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};
    
    /* Configure MSI as base clock source */
    osc.OscillatorType = RCC_OSCILLATORTYPE_MSI;
    osc.MSIState = RCC_MSI_ON;
    osc.MSIClockRange = RCC_MSIRANGE_6;  /* 4MHz MSI */
    osc.MSICalibrationValue = RCC_MSICALIBRATION_DEFAULT;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_MSI;
    osc.PLL.PLLM = 1;       /* 4MHz / 1 = 4MHz */
    osc.PLL.PLLN = 40;      /* 4MHz × 40 = 160MHz */
    osc.PLL.PLLP = 7;       /* 160MHz / 8 = 20MHz (for ADC) */
    osc.PLL.PLLQ = 4;       /* 160MHz / 4 = 40MHz (for USB) */
    osc.PLL.PLLR = 2;       /* 160MHz / 2 = 80MHz SYSCLK */
    
    if (HAL_RCC_OscConfig(&osc) != HAL_OK) {
        Error_Handler();
    }
    
    /* Select PLL as system clock */
    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                    RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;    /* 80MHz HCLK */
    clk.APB1CLKDivider = RCC_HCLK_DIV1;     /* 80MHz APB1 */
    clk.APB2CLKDivider = RCC_HCLK_DIV1;     /* 80MHz APB2 */
    
    if (HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_4) != HAL_OK) {
        Error_Handler();
    }
    
    /* Enable peripheral clocks */
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();
    __HAL_RCC_USART1_CLK_ENABLE();
    __HAL_RCC_USART2_CLK_ENABLE();
    __HAL_RCC_USART3_CLK_ENABLE();
    __HAL_RCC_I2C1_CLK_ENABLE();
    __HAL_RCC_ADC1_CLK_ENABLE();
    __HAL_RCC_TIM3_CLK_ENABLE();
    __HAL_RCC_DAC1_CLK_ENABLE();
}

static void Error_Handler(void) {
    /* Flash all LEDs rapidly */
    while (1) {
        HAL_GPIO_TogglePin(GPIOB, GPIO_PIN_15);  /* Red LED */
        HAL_Delay(100);
    }
}