/* ui.c — Button input + menu navigation
 *
 * Two buttons:
 *   GPIO0  — RUN (short press) / MENU (long press)
 *   GPIO2  — not used (pump) ... use a second button on a free GPIO.
 *
 * For the pocket form factor, we use a single button (GPIO0/BOOT) with
 * short/long/double-press detection, plus an optional rotary encoder.
 * Here we implement a simple two-button scheme: GPIO0 (RUN) and an
 * external button on GPIO17 (CHRG status pin, repurposed as MODE).
 */
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "esp_timer.h"

#include "sdkconfig.h"
#include "ui.h"

static const char *TAG = "ui";
static QueueHandle_t s_queue = NULL;
static int s_menu_sel = 0;

#define BTN_RUN_PIN   0
#define BTN_MODE_PIN  17

static void IRAM_ATTR btn_isr(void *arg)
{
    int pin = (int)arg;
    ui_cmd_t cmd;
    if (pin == BTN_RUN_PIN) {
        cmd = UI_CMD_RUN;
    } else {
        cmd = UI_CMD_MENU_NEXT;
    }
    BaseType_t hp = pdFALSE;
    xQueueSendFromISR(s_queue, &cmd, &hp);
    if (hp) portYIELD_FROM_ISR();
}

QueueHandle_t ui_trigger_queue(void) { return s_queue; }

void ui_init(void)
{
    s_queue = xQueueCreate(8, sizeof(ui_cmd_t));

    /* Configure both buttons as inputs with pull-ups + falling-edge IRQ */
    gpio_config_t io = {
        .pin_bit_mask = (1ULL << BTN_RUN_PIN) | (1ULL << BTN_MODE_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    gpio_config(&io);

    gpio_install_isr_service(0);
    gpio_isr_handler_add(BTN_RUN_PIN, btn_isr, (void *)BTN_RUN_PIN);
    gpio_isr_handler_add(BTN_MODE_PIN, btn_isr, (void *)BTN_MODE_PIN);

    ESP_LOGI(TAG, "UI initialized (RUN=GPIO0, MODE=GPIO17)");
}

int ui_menu_selected(void) { return s_menu_sel; }

ui_cmd_t ui_wait_cmd(uint32_t timeout_ms)
{
    ui_cmd_t cmd = UI_CMD_NONE;
    xQueueReceive(s_queue, &cmd, pdMS_TO_TICKS(timeout_ms));
    if (cmd == UI_CMD_MENU_NEXT) {
        s_menu_sel = (s_menu_sel + 1) % 4;
    }
    return cmd;
}