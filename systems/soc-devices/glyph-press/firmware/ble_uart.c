/**
 * glyph_press/firmware/ble_uart.c — BLE UART Protocol Handler
 *
 * HC-05 Bluetooth Classic SPP module on UART0 (GP0/GP1, 9600 baud).
 * Receives text commands from phone/computer and queues text for embossing.
 *
 * Protocol (ASCII, \n terminated):
 *   TEXT <string>  — queue text
 *   MODE G1|G2|G8|LABEL|PAGE
 *   LANG en|fr|es|de|pt|ar|hi|zh
 *   FORCE 0-9
 *   CPL <n>
 *   FEED <mm>
 *   START
 *   STOP
 *   STATUS
 *   TEST
 *   HELP
 */

#include "main.h"
#include "pico/stdlib.h"
#include "hardware/uart.h"
#include <string.h>
#include <stdio.h>

#define UART_ID    uart0
#define BAUD_RATE  9600

static char s_rx_buf[TEXT_BUFFER_SIZE + 64];
static uint16_t s_rx_pos = 0;
static bool s_init_done = false;

static const char *HELP_TEXT =
    "Glyph Press Commands:\n"
    "  TEXT <string>  - Queue text for embossing\n"
    "  MODE G1|G2|G8|LABEL|PAGE\n"
    "  LANG en|fr|es|de|pt|ar|hi|zh\n"
    "  FORCE 0-9      - Embossing force\n"
    "  CPL <n>        - Cells per line (20-40)\n"
    "  FEED <mm>      - Feed paper by N mm\n"
    "  START          - Begin embossing\n"
    "  STOP           - Cancel\n"
    "  STATUS         - Query status\n"
    "  TEST           - Emboss Braille alphabet\n"
    "  HELP           - This message\n";

void ble_init(void)
{
    uart_init(UART_ID, BAUD_RATE);
    gpio_set_function(PIN_UART0_TX, GPIO_FUNC_UART);
    gpio_set_function(PIN_UART0_RX, GPIO_FUNC_UART);
    uart_set_fifo_enabled(UART_ID, true);
    s_init_done = true;
}

void ble_send(const char *str)
{
    if (!s_init_done) return;
    uart_puts(UART_ID, str);
}

static void process_command(const char *cmd)
{
    if (strncmp(cmd, "TEXT ", 5) == 0) {
        const char *text = cmd + 5;
        uint16_t len = strlen(text);
        if (len > TEXT_BUFFER_SIZE - 1) len = TEXT_BUFFER_SIZE - 1;
        memcpy(g_buffer.text, text, len);
        g_buffer.text[len] = '\0';
        g_buffer.text_len = len;
        g_ble_text_ready = false; /* not auto-start; user presses START or sends START */
        ble_send("OK Text queued\n");
    } else if (strncmp(cmd, "MODE ", 5) == 0) {
        if (strcmp(cmd + 5, "G1") == 0) g_config.mode = MODE_GRADE1;
        else if (strcmp(cmd + 5, "G2") == 0) g_config.mode = MODE_GRADE2;
        else if (strcmp(cmd + 5, "G8") == 0) g_config.mode = MODE_8DOT;
        else if (strcmp(cmd + 5, "LABEL") == 0) g_config.mode = MODE_LABEL;
        else if (strcmp(cmd + 5, "PAGE") == 0) g_config.mode = MODE_PAGE;
        else { ble_send("ERR Unknown mode\n"); return; }
        ble_send("OK Mode set\n");
    } else if (strncmp(cmd, "LANG ", 5) == 0) {
        const char *langs[] = {"en","fr","es","de","pt","ar","hi","zh"};
        bool found = false;
        for (int i = 0; i < LANG_COUNT; i++) {
            if (strcmp(cmd + 5, langs[i]) == 0) {
                g_config.lang = (gp_lang_t)i;
                found = true;
                break;
            }
        }
        ble_send(found ? "OK Lang set\n" : "ERR Unknown lang\n");
    } else if (strncmp(cmd, "FORCE ", 6) == 0) {
        int f = atoi(cmd + 6);
        if (f >= 0 && f <= 9) {
            g_config.force = (uint8_t)f;
            ble_send("OK Force set\n");
        } else {
            ble_send("ERR Force 0-9\n");
        }
    } else if (strncmp(cmd, "CPL ", 4) == 0) {
        int c = atoi(cmd + 4);
        if (c >= MIN_CELLS_PER_LINE && c <= MAX_CELLS_PER_LINE) {
            g_config.cells_per_line = (uint8_t)c;
            ble_send("OK CPL set\n");
        } else {
            ble_send("ERR CPL 20-40\n");
        }
    } else if (strncmp(cmd, "FEED ", 5) == 0) {
        float mm = atof(cmd + 5);
        feed_mm(mm);
        ble_send("OK Fed\n");
    } else if (strcmp(cmd, "START") == 0) {
        if (g_buffer.text_len > 0 && g_state == STATE_IDLE) {
            g_state = STATE_TRANSLATE;
            g_config.cells_done = 0;
            g_buffer.text_pos = 0;
            ble_send("OK Embossing\n");
        } else {
            ble_send("ERR No text or busy\n");
        }
    } else if (strcmp(cmd, "STOP") == 0) {
        g_state = STATE_IDLE;
        ble_send("OK Stopped\n");
    } else if (strcmp(cmd, "STATUS") == 0) {
        char buf[80];
        const char *modes[] = {"G1","G2","8dot","Label","Page"};
        snprintf(buf, sizeof(buf), "OK %s mode:%s cells:%d/%d\n",
                 g_state == STATE_IDLE ? "idle" : "busy",
                 modes[g_config.mode % 5],
                 g_config.cells_done, g_config.cells_total);
        ble_send(buf);
    } else if (strcmp(cmd, "TEST") == 0) {
        strcpy(g_buffer.text, "ABCDEFGHIJKLMNOPQRSTUVWXYZ");
        g_buffer.text_len = 26;
        g_state = STATE_TRANSLATE;
        g_config.cells_done = 0;
        g_buffer.text_pos = 0;
        ble_send("OK Test embossing alphabet\n");
    } else if (strcmp(cmd, "HELP") == 0) {
        ble_send(HELP_TEXT);
    } else if (strlen(cmd) == 0) {
        /* empty line, ignore */
    } else {
        ble_send("ERR Unknown command. Send HELP.\n");
    }
}

void ble_task(void)
{
    if (!s_init_done) return;

    while (uart_is_readable(UART_ID)) {
        char ch = (char)uart_getc(UART_ID);
        if (ch == '\r') continue;
        if (ch == '\n') {
            s_rx_buf[s_rx_pos] = '\0';
            process_command(s_rx_buf);
            s_rx_pos = 0;
        } else {
            if (s_rx_pos < sizeof(s_rx_buf) - 1)
                s_rx_buf[s_rx_pos++] = ch;
        }
    }
}

bool ble_get_line(char *buf, uint16_t maxlen)
{
    if (!uart_is_readable(UART_ID)) return false;
    uint16_t i = 0;
    while (i < maxlen - 1 && uart_is_readable(UART_ID)) {
        char ch = (char)uart_getc(UART_ID);
        if (ch == '\n') break;
        if (ch != '\r') buf[i++] = ch;
    }
    buf[i] = '\0';
    return i > 0;
}