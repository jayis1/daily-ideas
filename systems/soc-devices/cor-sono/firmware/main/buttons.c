/*
 * cor-sono / firmware / buttons.c
 * Debounced tactile button input
 */
#include "main.h"
#include "buttons.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"

static const char *TAG = "btn";

#define PIN_REC   17
#define PIN_MODE  18
#define PIN_MENU  19

static QueueHandle_t btn_queue;

static void IRAM_ATTR gpio_isr(void *arg)
{
    uint32_t pin = (uint32_t)arg;
    xQueueSendFromISR(btn_queue, &pin, NULL);
}

static void button_task(void *arg)
{
    uint32_t pin;
    while (1) {
        if (xQueueReceive(btn_queue, &pin, portMAX_DELAY)) {
            vTaskDelay(pdMS_TO_TICKS(30));  /* debounce */
            if (gpio_get_level(pin) == 0) {
                switch (pin) {
                case PIN_REC:  on_button_record(); break;
                case PIN_MODE: on_button_mode();   break;
                case PIN_MENU: on_button_menu();   break;
                }
            }
            /* Wait for release */
            while (gpio_get_level(pin) == 0) vTaskDelay(pdMS_TO_TICKS(10));
        }
    }
}

void buttons_init(void)
{
    ESP_LOGI(TAG, "init buttons");

    btn_queue = xQueueCreate(10, sizeof(uint32_t));

    gpio_config_t io = {
        .pin_bit_mask = (1ULL << PIN_REC) | (1ULL << PIN_MODE) | (1ULL << PIN_MENU),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = true,
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    gpio_config(&io);

    gpio_install_isr_service(0);
    gpio_isr_handler_add(PIN_REC,  gpio_isr, (void *)PIN_REC);
    gpio_isr_handler_add(PIN_MODE, gpio_isr, (void *)PIN_MODE);
    gpio_isr_handler_add(PIN_MENU, gpio_isr, (void *)PIN_MENU);

    xTaskCreate(button_task, "buttons", 2048, NULL, 5, NULL);
}