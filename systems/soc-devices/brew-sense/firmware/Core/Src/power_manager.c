/**
 * power_manager.c — Ultra-Low-Power Manager for Brew Sense
 * 
 * Manages STM32L476 power modes for 30-day battery life on 2× AAA.
 */

#include "power_manager.h"
#include "stm32l4xx_hal.h"

static power_config_t s_config;
static power_mode_t s_current_mode = POWER_MODE_RUN;
static uint32_t s_last_wake_time = 0;

/*----------------------------------------------------------------------------*/

void power_manager_init(const power_config_t *config) {
    if (config) {
        s_config = *config;
    } else {
        s_config.sample_interval_sec = 60;
        s_config.wifi_push_interval_sec = 300;
        s_config.display_timeout_sec = 30;
        s_config.enable_wifi = true;
        s_config.enable_display = true;
        s_config.enable_buzzer = true;
        s_config.low_battery_threshold = 2.2f;
    }
    
    /* Configure RTC for wake-up from STOP mode */
    /* RTC_WUT = sample_interval */
    __HAL_RCC_RTC_ENABLE();
    
    /* Enable ultra-low-power mode */
    HAL_PWREx_EnableUltraLowPower();
    HAL_PWREx_EnableFastWakeUp();
    
    /* Disable unused GPIO clocks to save power */
    __HAL_RCC_GPIOC_CLK_DISABLE();  /* Will re-enable when needed */
    
    s_last_wake_time = HAL_GetTick();
}

/*----------------------------------------------------------------------------*/

void power_manager_sleep(power_mode_t mode) {
    s_current_mode = mode;
    
    switch (mode) {
        case POWER_MODE_RUN:
            /* No sleep */
            break;
            
        case POWER_MODE_LOW_RUN:
            /* Reduce clock to 80MHz, disable display */
            if (!s_config.enable_display) {
                /* Display already handled elsewhere */
            }
            /* Could reduce SystemCoreClock here */
            break;
            
        case POWER_MODE_SLEEP:
            /* CPU sleep, peripherals keep running */
            HAL_PWR_EnterSLEEPMode(PWR_MAINREGULATOR_ON, PWR_SLEEPENTRY_WFI);
            break;
            
        case POWER_MODE_STOP:
            /* Deep sleep, only RTC and backup domain alive */
            /* Configure RTC wake-up timer */
            HAL_RTCEx_SetWakeUpTimer_IT(&hrtc, s_config.sample_interval_sec,
                                          RTC_WAKEUPCLOCK_CK_SPRE_16BITS);
            
            /* Enter STOP mode */
            HAL_PWR_EnterSTOPMode(PWR_LOWPOWERREGULATOR_ON, PWR_STOPENTRY_WFI);
            
            /* After wake-up: re-init system clock */
            SystemClock_Config();
            break;
            
        case POWER_MODE_STANDBY:
            /* Deepest sleep, only backup domain */
            HAL_PWR_EnterSTANDBYMode();
            /* Never reaches here — reset on wake */
            break;
    }
}

/*----------------------------------------------------------------------------*/

void power_manager_wake(void) {
    /* After STOP mode wake-up, restore system clock */
    SystemClock_Config();
    s_last_wake_time = HAL_GetTick();
    s_current_mode = POWER_MODE_RUN;
}

/*----------------------------------------------------------------------------*/

float power_manager_get_battery_voltage(void) {
    /* Use ADC to read battery voltage through voltage divider
     * Divider: VBAT --[R1=100k]-- ADC --[R2=100k]-- GND
     * ADC reads VBAT/2
     * VBAT = ADC_reading × 3.3V × 2 / 4095
     */
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = ADC_CHANNEL_8;  /* PB0 */
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
    
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);
    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 10);
    
    uint32_t adc_val = HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);
    
    /* Convert: V = ADC × Vref × (R1+R2)/R2 / 4095 */
    float voltage = ((float)adc_val / 4095.0f) * 3.3f * 2.0f;
    
    return voltage;
}

/*----------------------------------------------------------------------------*/

uint8_t power_manager_get_battery_percent(void) {
    float voltage = power_manager_get_battery_voltage();
    
    /* Alkaline AAA discharge curve (2 cells in series):
     * 3.2V = 100%, 2.0V = 0%
     * Approximate linear model (good enough for indicator) */
    if (voltage >= 3.2f) return 100;
    if (voltage <= 2.0f) return 0;
    
    return (uint8_t)((voltage - 2.0f) / 1.2f * 100.0f);
}

/*----------------------------------------------------------------------------*/

bool power_manager_is_usb_connected(void) {
    return HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_9) == GPIO_PIN_SET;
}

/*----------------------------------------------------------------------------*/

void power_manager_set_sample_interval(uint32_t seconds) {
    if (seconds >= 1 && seconds <= 3600) {
        s_config.sample_interval_sec = seconds;
    }
}

/*----------------------------------------------------------------------------*/

power_mode_t power_manager_get_mode(void) {
    return s_current_mode;
}

/*----------------------------------------------------------------------------*/

void power_manager_set_display(bool enable) {
    if (enable && !s_config.enable_display) {
        /* Turn on display */
        s_config.enable_display = true;
        /* display_on() called separately */
    } else if (!enable && s_config.enable_display) {
        /* Turn off display */
        s_config.enable_display = false;
        /* display_off() called separately */
    }
}

/*----------------------------------------------------------------------------*/

void power_manager_shutdown(void) {
    /* Enter STANDBY mode — only wake via WKUP pin or RTC */
    /* Configure WKUP pin (PC11 = BOOT button) */
    HAL_PWR_EnableWakeUpPin(PWR_WAKEUP_PIN2);
    
    /* Clear wake-up flags */
    __HAL_PWR_CLEAR_FLAG(PWR_FLAG_WU);
    
    /* Enter STANDBY */
    HAL_PWR_EnterSTANDBYMode();
}