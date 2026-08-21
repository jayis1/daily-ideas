/*
 * pyro-balance / Core/Src/main.c
 * Pyro Balance — Pocket Thermogravimetric Analyzer
 * STM32G474RET6 application. MIT License.
 *
 * Scheduler: 10 Hz control loop, 1 Hz logging/streaming.
 */
#include "main.h"
#include "furnace.h"
#include "balance.h"
#include "ads122u04.h"
#include "tga.h"
#include "bme280.h"
#include "oled_display.h"
#include "sd_logger.h"
#include "safety.h"
#include "esp32_link.h"
#include "purge.h"
#include "flash_store.h"

pb_status_t g_status;
TIM_HandleTypeDef htim3;
ADC_HandleTypeDef hadc1;
I2C_HandleTypeDef hi2c1, hi2c2;
SPI_HandleTypeDef hspi1;
UART_HandleTypeDef huart1;
IWDG_HandleTypeDef hiwdg;

static uint32_t last_10hz_ms = 0, last_1hz_ms = 0;
static float m0_mg = 0.0f;

static void gpio_init_extra(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    GPIO_InitTypeDef g = {0};
    g.Pull = GPIO_NOPULL; g.Speed = GPIO_SPEED_FREQ_LOW;

    /* outputs */
    g.Mode = GPIO_MODE_OUTPUT_PP;
    g.Pin = HX711_SCK_PIN;  HAL_GPIO_Init(HX711_SCK_PORT, &g);
    g.Pin = HX711_RATE_PIN; HAL_GPIO_Init(HX711_RATE_PORT, &g);
    g.Pin = HEATER_EN_PIN; HAL_GPIO_Init(HEATER_EN_PORT, &g); HAL_GPIO_WritePin(HEATER_EN_PORT, HEATER_EN_PIN, GPIO_PIN_RESET);
    g.Pin = PUMP_PWM_PIN;  HAL_GPIO_Init(PUMP_PWM_PORT, &g);
    g.Pin = LED_PIN;       HAL_GPIO_Init(LED_PORT, &g);
    g.Pin = BUZZER_PIN;    HAL_GPIO_Init(BUZZER_PORT, &g);
    g.Pin = OLED_CS_PIN;   HAL_GPIO_Init(OLED_CS_PORT, &g); HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);
    g.Pin = OLED_DC_PIN;   HAL_GPIO_Init(OLED_DC_PORT, &g);
    g.Pin = SD_CS_PIN;     HAL_GPIO_Init(SD_CS_PORT, &g);   HAL_GPIO_WritePin(SD_CS_PORT, SD_CS_PIN, GPIO_PIN_SET);
    g.Pin = N2_VALVE_PIN;  HAL_GPIO_Init(N2_VALVE_PORT, &g);
    g.Pin = FAN_PIN;       HAL_GPIO_Init(FAN_PORT, &g);

    /* inputs */
    g.Mode = GPIO_MODE_INPUT; g.Pull = GPIO_PULLUP;
    g.Pin = HX711_DOUT_PIN;  HAL_GPIO_Init(HX711_DOUT_PORT, &g);
    g.Pin = OVERTEMP_PIN;     HAL_GPIO_Init(OVERTEMP_PORT, &g);
    g.Pin = FUSE_SENSE_PIN;   HAL_GPIO_Init(FUSE_SENSE_PORT, &g);
    g.Pin = INTERLOCK_PIN;    HAL_GPIO_Init(INTERLOCK_PORT, &g);
    g.Pin = BTN_START_PIN|BTN_STOP_PIN|BTN_MENU_PIN; HAL_GPIO_Init(GPIOB, &g);
}

static void iwdg_init(void)
{
    hiwdg.Instance = IWDG;
    hiwdg.Init.Prescaler = IWDG_PRESCALER_256;
    hiwdg.Init.Reload = 0xFFF;
    hiwdg.Init.Window = 0xFFF;
    HAL_IWDG_Init(&hiwdg);
}

static void buttons_scan(void)
{
    static uint32_t db_start = 0, db_stop = 0, db_menu = 0;
    if (!HAL_GPIO_ReadPin(BTN_START_PORT, BTN_START_PIN)) {
        if (HAL_GetTick() - db_start > 200) {
            if (g_status.state == PB_IDLE) {
                m0_mg = balance_last_mg();
                if (m0_mg > 1.0f) {
                    tga_reset(m0_mg);
                    furnace_start(g_cfg.final_temp_c, g_cfg.rate_c_per_min_x10, g_cfg.hold_min);
                    if (g_cfg.purge_n2) { purge_set_n2(true); purge_pump_on(true); }
                    sd_open_run(g_status.method_id);
                    g_status.state = PB_RUNNING;
                    g_status.t_start_ms = HAL_GetTick();
                }
            }
            db_start = HAL_GetTick();
        }
    } else db_start = HAL_GetTick();

    if (!HAL_GPIO_ReadPin(BTN_STOP_PORT, BTN_STOP_PIN)) {
        if (HAL_GetTick() - db_stop > 200) {
            if (g_status.state == PB_RUNNING) {
                furnace_stop();
                g_status.state = PB_COOLING;
            }
            db_stop = HAL_GetTick();
        }
    } else db_stop = HAL_GetTick();

    if (!HAL_GPIO_ReadPin(BTN_MENU_PORT, BTN_MENU_PIN)) {
        if (HAL_GetTick() - db_menu > 200) {
            /* menu cycle: defaults for brevity */
            g_cfg.rate_c_per_min_x10 = (g_cfg.rate_c_per_min_x10 >= 200) ? 50 : g_cfg.rate_c_per_min_x10 + 50;
            db_menu = HAL_GetTick();
        }
    } else db_menu = HAL_GetTick();
}

static void run_tick_10hz(void)
{
    /* acquire */
    balance_read_mg();          /* HX711 at 80 Hz, filtered */
    g_status.mass_mg = balance_last_mg();
    g_status.temp_c = furnace_get_temp();
    g_status.target_c = furnace_get_target();

    /* PID */
    furnace_pid_tick();

    /* safety */
    if (!safety_check()) {
        furnace_emergency_cut();
        g_status.state = PB_ALARM;
        return;
    }

    /* battery */
    {
        static uint16_t vadc; uint32_t s = 0;
        for (int i = 0; i < 8; i++) {
            ADC_ChannelConfTypeDef c = {0};
            c.Channel = ADC_CHANNEL_9; c.Rank = 1; c.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
            HAL_ADC_ConfigChannel(&hadc1, &c);
            HAL_ADC_Start(&hadc1);
            if (HAL_ADC_PollForConversion(&hadc1, 5) == HAL_OK) s += HAL_ADC_GetValue(&hadc1);
            HAL_ADC_Stop(&hadc1);
        }
        vadc = s >> 3;
        g_status.battery_v = (vadc * 3.3f * 4.0f) / 4095.0f; /* divider ×0.25 */
    }
}

static void run_tick_1hz(void)
{
    float pct = (m0_mg > 0) ? (g_status.mass_mg / m0_mg) * 100.0f : 0.0f;
    tga_push(g_status.temp_c, g_status.mass_mg, HAL_GetTick());

    /* crude DTG (per minute) */
    static float last_mass_pct = 100.0f; static uint32_t last_t = 0;
    float dtg = 0.0f;
    if (last_t) {
        float dmin = (HAL_GetTick() - last_t) / 60000.0f;
        if (dmin > 0) dtg = (pct - last_mass_pct) / dmin;
    }
    last_mass_pct = pct; last_t = HAL_GetTick();

    sd_log_point(g_status.temp_c, g_status.mass_mg, pct, dtg, HAL_GetTick() - g_status.t_start_ms);
    esp32_send_point(g_status.temp_c, g_status.mass_mg, pct, dtg, HAL_GetTick() - g_status.t_start_ms);
    oled_draw_tg(tga_get(), g_status.temp_c, pct);

    if (g_status.state == PB_RUNNING && g_status.temp_c >= g_cfg.final_temp_c - 0.5f) {
        /* reached final temp — hold then cool */
        static uint32_t hold_start = 0;
        if (!hold_start) hold_start = HAL_GetTick();
        if ((HAL_GetTick() - hold_start) / 60000 >= g_cfg.hold_min) {
            furnace_stop();
            g_status.state = PB_COOLING;
            hold_start = 0;
        }
    }
    if (g_status.state == PB_COOLING) {
        furnace_cooling_tick();
        if (furnace_get_temp() < 60.0f) {
            tga_finalize();
            sd_close_run();
            esp32_send_result(tga_get());
            purge_pump_on(false); purge_set_n2(false);
            g_status.state = PB_IDLE;
            HAL_GPIO_WritePin(LED_PORT, LED_PIN, GPIO_PIN_SET);
        }
    }
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    gpio_init_extra();
    iwdg_init();

    /* periph inits (simplified) */
    bme280_init();
    ads_init();
    balance_init();
    furnace_init();
    oled_init();
    sd_init();
    safety_init();
    esp32_link_init();
    purge_init();
    flash_load();
    if (g_cfg.magic != 0x5042414C) flash_defaults();

    g_status.state = PB_IDLE;
    g_status.method_id = 0;

    oled_text(0, "Pyro Balance v1.0");
    oled_text(1, "Ready. Insert sample.");

    while (1) {
        HAL_IWDG_Refresh(&hiwdg);
        uint32_t now = HAL_GetTick();

        if (now - last_10hz_ms >= 100) {
            last_10hz_ms = now;
            run_tick_10hz();
            buttons_scan();
            esp32_link_poll();
        }
        if (now - last_1hz_ms >= 1000) {
            last_1hz_ms = now;
            run_tick_1hz();
        }
        __WFI();
    }
}

/* ---- HAL MSP / IRQ stubs ---- */
void HAL_MspInit(void) {}
void NMI_Handler(void) {}
void HardFault_Handler(void) { while (1); }
void MemManage_Handler(void) { while (1); }
void BusFault_Handler(void) { while (1); }
void UsageFault_Handler(void) { while (1); }
void SVC_Handler(void) {}
void DebugMon_Handler(void) {}
void PendSV_Handler(void) {}
void SysTick_Handler(void) { HAL_IncTick(); }

void Error_Handler(void) {
    while (1) { HAL_GPIO_TogglePin(LED_PORT, LED_PIN); HAL_Delay(50); }
}

void SystemClock_Config(void)
{
    RCC_OscInitTypeDef o = {0};
    o.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    o.HSEState = RCC_HSE_ON;
    o.PLL.PLLState = RCC_PLL_ON;
    o.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    o.PLL.PLLM = 6; o.PLL.PLLN = 85; o.PLL.PLLP = 7; o.PLL.PLLQ = 2; o.PLL.PLLR = 2;
    if (HAL_RCC_OscConfig(&o) != HAL_OK) Error_Handler();
    RCC_ClkInitTypeDef c = {0};
    c.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK|RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
    c.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    c.AHBCLKDivider = RCC_SYSCLK_DIV1;
    c.APB1CLKDivider = RCC_HCLK_DIV1;
    c.APB2CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&c, FLASH_LATENCY_4) != HAL_OK) Error_Handler();
}