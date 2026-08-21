/*
 * Tremor Tile — SX1262 LoRa Radio Driver
 * lora_radio.c — SPI driver for LoRa communication
 *
 * SX1262: 868/915 MHz LoRa transceiver, +22dBm, -127dBm sensitivity
 * Interface: SPI1 @ 4MHz + GPIO control lines
 */

#include "lora_radio.h"
#include "config.h"
#include "hardware/spi.h"
#include "hardware/gpio.h"
#include "pico/stdlib.h"
#include <string.h>
#include <stdio.h>

// SX1262 Register Map (key registers)
#define SX1262_REG_LR_SYNCWORD              0x0740
#define SX1262_REG_LR_SYNCWORD_PRIVATE       0x12
#define SX1262_REG_LR_SYNCWORD_PUBLIC        0x34

// SX1262 Opcodes
#define SX1262_OP_SET_STANDBY               0x80
#define SX1262_OP_SET_PACKET_TYPE            0x8A
#define SX1262_OP_SET_RF_FREQUENCY           0x86
#define SX1262_OP_SET_TX_PARAMS              0x8E
#define SX1262_OP_SET_MOD_PARAMS              0x8C
#define SX1262_OP_SET_PACKET_PARAMS          0x8D
#define SX1262_OP_SET_BUFFER_BASE_ADDR       0x8F
#define SX1262_OP_WRITE_BUFFER               0x0D
#define SX1262_OP_READ_BUFFER                0x1D
#define SX1262_OP_SET_DIO_IRQ_PARAMS        0x08
#define SX1262_OP_GET_IRQ_STATUS             0x12
#define SX1262_OP_CLEAR_IRQ_STATUS           0x02
#define SX1262_OP_GET_STATUS                 0xC0
#define SX1262_OP_SET_RX                     0x82
#define SX1262_OP_SET_TX                     0x83
#define SX1262_OP_SET_CAD                    0xC8
#define SX1262_OP_SET_DIO3_AS_TCXO_CTRL     0x97
#define SX1262_OP_CALIBRATE                  0x89
#define SX1262_OP_SET_REGULATOR_MODE         0x96

// Packet types
#define SX1262_PACKET_TYPE_LORA              0x01
#define SX1262_PACKET_TYPE_GFSK              0x00

// Standby modes
#define SX1262_STANDBY_RC                    0x00
#define SX1262_STANDBY_XOSC                  0x01

// Regulator modes
#define SX1262_REGULATOR_DCDC                0x00
#define SX1262_REGULATOR_LDO                  0x01

// IRQ masks
#define SX1262_IRQ_TX_DONE                    (1 << 0)
#define SX1262_IRQ_RX_DONE                    (1 << 1)
#define SX1262_IRQ_SYNC_WORD_VALID            (1 << 2)
#define SX1262_IRQ_HEADER_VALID               (1 << 3)
#define SX1262_IRQ_HEADER_ERROR               (1 << 4)
#define SX1262_IRQ_CRC_ERROR                  (1 << 5)
#define SX1262_IRQ_CAD_DONE                   (1 << 6)
#define SX1262_IRQ_CAD_DETECTED               (1 << 7)
#define SX1262_IRQ_TIMEOUT                    (1 << 8)

// TX queue
#define TX_QUEUE_SIZE  8
static lora_packet_t tx_queue[TX_QUEUE_SIZE];
static uint8_t tx_queue_head = 0;
static uint8_t tx_queue_tail = 0;
static uint8_t tx_queue_count = 0;

// State
static bool initialized = false;
static bool tx_in_progress = false;

// SPI chip select helpers
static inline void sx1262_cs_select(void) {
    gpio_put(SPI1_CS_PIN, 0);
    busy_wait_us(10);  // CS setup time
}

static inline void sx1262_cs_deselect(void) {
    busy_wait_us(10);  // CS hold time
    gpio_put(SPI1_CS_PIN, 1);
}

// Wait for SX1262 BUSY pin to go low (indicates ready)
static void sx1262_wait_busy(void) {
    uint32_t timeout = 10000;  // 10ms timeout
    while (gpio_get(SX1262_BUSY_PIN) && timeout > 0) {
        busy_wait_us(1);
        timeout--;
    }
    if (timeout == 0) {
        printf("SX1262: BUSY timeout!\n");
    }
}

// Write command with no data
static void sx1262_write_command(uint8_t opcode) {
    sx1262_wait_busy();
    sx1262_cs_select();
    spi_write_blocking(spi1, &opcode, 1);
    sx1262_cs_deselect();
}

// Write command with data
static void sx1262_write_command_with_data(uint8_t opcode, const uint8_t *data, uint16_t len) {
    sx1262_wait_busy();
    sx1262_cs_select();
    uint8_t tx_buf[256];
    tx_buf[0] = opcode;
    memcpy(&tx_buf[1], data, len);
    spi_write_blocking(spi1, tx_buf, len + 1);
    sx1262_cs_deselect();
}

// Write register
static void sx1262_write_register(uint16_t addr, uint8_t value) {
    uint8_t data[3] = {
        (addr >> 8) & 0xFF,
        addr & 0xFF,
        value
    };
    sx1262_write_command_with_data(0x0D, data, 3);  // Write register opcode
}

// Read register
static uint8_t sx1262_read_register(uint16_t addr) {
    sx1262_wait_busy();
    uint8_t tx_buf[3] = { 0x1D, (addr >> 8) & 0xFF, addr & 0xFF };
    uint8_t rx_buf[2];
    sx1262_cs_select();
    spi_write_blocking(spi1, tx_buf, 3);
    spi_read_blocking(spi1, 0xFF, rx_buf, 2);
    sx1262_cs_deselect();
    return rx_buf[1];
}

// Set RF frequency from MHz value
static void sx1262_set_frequency(float freq_mhz) {
    // SX1262 frequency = (freq_hz * 2^25) / 32MHz
    // For 868 MHz: (868000000 * 33554432) / 32000000 = 9096202240 = 0x21E7C800
    uint32_t freq_reg = (uint32_t)((double)freq_mhz * 1000000.0 * (double)(1LL << 25) / 32000000.0);
    uint8_t data[4] = {
        (freq_reg >> 24) & 0xFF,
        (freq_reg >> 16) & 0xFF,
        (freq_reg >> 8) & 0xFF,
        freq_reg & 0xFF
    };
    sx1262_write_command_with_data(SX1262_OP_SET_RF_FREQUENCY, data, 4);
}

// Initialize SX1262
void lora_radio_init(void) {
    // Configure GPIO pins
    gpio_init(SPI1_CS_PIN);
    gpio_set_dir(SPI1_CS_PIN, GPIO_OUT);
    gpio_put(SPI1_CS_PIN, 1);  // CS inactive

    gpio_init(SX1262_RESET_PIN);
    gpio_set_dir(SX1262_RESET_PIN, GPIO_OUT);
    gpio_put(SX1262_RESET_PIN, 1);  // Not in reset

    gpio_init(SX1262_BUSY_PIN);
    gpio_set_dir(SX1262_BUSY_PIN, GPIO_IN);

    gpio_init(SX1262_DIO1_PIN);
    gpio_set_dir(SX1262_DIO1_PIN, GPIO_IN);

    gpio_init(SX1262_TCXO_EN_PIN);
    gpio_set_dir(SX1262_TCXO_EN_PIN, GPIO_OUT);
    gpio_put(SX1262_TCXO_EN_PIN, 1);  // Enable TCXO

    gpio_init(SX1262_RF_SW_PIN);
    gpio_set_dir(SX1262_RF_SW_PIN, GPIO_OUT);
    gpio_put(SX1262_RF_SW_PIN, 1);  // RX path

    // Hardware reset sequence
    gpio_put(SX1262_RESET_PIN, 0);
    busy_wait_us(1000);  // 1ms reset pulse
    gpio_put(SX1262_RESET_PIN, 1);
    busy_wait_us(10000);  // 10ms startup

    // Wait for BUSY to go low
    sx1262_wait_busy();

    // Set regulator mode to DCDC (more efficient)
    uint8_t reg_mode = SX1262_REGULATOR_DCDC;
    sx1262_write_command_with_data(SX1262_OP_SET_REGULATOR_MODE, &reg_mode, 1);

    // Set standby mode (required before configuration)
    uint8_t standby_cfg = SX1262_STANDBY_XOSC;  // Use crystal oscillator
    sx1262_write_command_with_data(SX1262_OP_SET_STANDBY, &standby_cfg, 1);

    // Set packet type to LoRa
    uint8_t packet_type = SX1262_PACKET_TYPE_LORA;
    sx1262_write_command_with_data(SX1262_OP_SET_PACKET_TYPE, &packet_type, 1);

    // Set RF frequency
    sx1262_set_frequency(LORA_FREQ);

    // Set TX parameters: +22dBm, ramp time 200us
    uint8_t tx_params[2] = { LORA_TX_POWER, 0x02 };  // 22dBm, 200us ramp
    sx1262_write_command_with_data(SX1262_OP_SET_TX_PARAMS, tx_params, 2);

    // Set modulation parameters: SF7, BW=125kHz, CR=4/5, low-datarate-optimize=off
    // SF7 = 0x07, BW125 = 0x04, CR4/5 = 0x01
    uint8_t mod_params[4] = { LORA_SF_NORMAL, 0x04, 0x01, 0x00 };
    sx1262_write_command_with_data(SX1262_OP_SET_MOD_PARAMS, mod_params, 4);

    // Set packet parameters: preamble=8, header=explicit, CRC=on, invertIQ=off
    uint8_t pkt_params[6] = {
        0x00, 0x08,  // Preamble length: 8 symbols
        0x00,        // Header type: explicit
        0x40,        // Payload length: 64 bytes max
        0x01,        // CRC: on
        0x00         // Invert IQ: off
    };
    sx1262_write_command_with_data(SX1262_OP_SET_PACKET_PARAMS, pkt_params, 6);

    // Set sync word (LoRa private network)
    sx1262_write_register(SX1262_REG_LR_SYNCWORD, SX1262_REG_LR_SYNCWORD_PRIVATE);

    // Set DIO1 interrupt mask (TX done, RX done)
    uint8_t irq_mask[4] = {
        (SX1262_IRQ_TX_DONE | SX1262_IRQ_RX_DONE | SX1262_IRQ_TIMEOUT) >> 8,
        (SX1262_IRQ_TX_DONE | SX1262_IRQ_RX_DONE | SX1262_IRQ_TIMEOUT) & 0xFF,
        0x00, 0x00  // DIO2 mask (unused)
    };
    sx1262_write_command_with_data(SX1262_OP_SET_DIO_IRQ_PARAMS, irq_mask, 4);

    // Clear all IRQ flags
    uint8_t clear_irq[2] = { 0xFF, 0xFF };
    sx1262_write_command_with_data(SX1262_OP_CLEAR_IRQ_STATUS, clear_irq, 2);

    // Set buffer base addresses
    uint8_t buf_base[4] = { 0x00, 0x00, 0x00, 0x80 };  // TX: 0x0000, RX: 0x0080
    sx1262_write_command_with_data(SX1262_OP_SET_BUFFER_BASE_ADDR, buf_base, 4);

    initialized = true;
    printf("SX1262: Initialized — %.1f MHz, SF%d, BW=125kHz, +%ddBm\n",
           LORA_FREQ, LORA_SF_NORMAL, LORA_TX_POWER);
}

// Send a heartbeat packet
void lora_radio_send_heartbeat(uint16_t device_id, uint8_t battery_pct, uint8_t status_flags) {
    lora_packet_t pkt;
    pkt.type = PKT_TYPE_HEARTBEAT;
    pkt.device_id = device_id;
    pkt.length = PKT_HEARTBEAT_SIZE;

    // Pack heartbeat data
    pkt.data[0] = PKT_TYPE_HEARTBEAT;
    pkt.data[1] = (device_id >> 8) & 0xFF;
    pkt.data[2] = device_id & 0xFF;
    pkt.data[3] = battery_pct;
    pkt.data[4] = status_flags;
    // Bytes 5-11: reserved (timestamps, etc.)
    memset(&pkt.data[5], 0, 7);

    lora_radio_enqueue(&pkt);
}

// Enqueue a packet for transmission
void lora_radio_enqueue(lora_packet_t *pkt) {
    if (tx_queue_count >= TX_QUEUE_SIZE) {
        printf("LoRa: TX queue full, dropping packet type %d\n", pkt->type);
        return;
    }

    tx_queue[tx_queue_head] = *pkt;
    tx_queue_head = (tx_queue_head + 1) % TX_QUEUE_SIZE;
    tx_queue_count++;
}

// Enqueue an alert packet (high priority)
void lora_radio_enqueue_alert(alert_t *alert) {
    lora_packet_t pkt;
    pkt.type = PKT_TYPE_ALERT;
    pkt.device_id = DEVICE_ID;
    pkt.length = PKT_ALERT_SIZE;

    // Pack alert data
    pkt.data[0] = PKT_TYPE_ALERT;
    pkt.data[1] = (DEVICE_ID >> 8) & 0xFF;
    pkt.data[2] = DEVICE_ID & 0xFF;
    pkt.data[3] = alert->type;
    pkt.data[4] = alert->severity;
    pkt.data[5] = (alert->affected_bands >> 8) & 0xFF;
    pkt.data[6] = alert->affected_bands & 0xFF;
    pkt.data[7] = (alert->timestamp >> 24) & 0xFF;
    pkt.data[8] = (alert->timestamp >> 16) & 0xFF;
    pkt.data[9] = (alert->timestamp >> 8) & 0xFF;
    pkt.data[10] = alert->timestamp & 0xFF;
    memset(&pkt.data[11], 0, PKT_ALERT_SIZE - 11);

    // Alert uses SF12 for maximum range — reconfigure temporarily
    // (Will be handled in send_next)

    lora_radio_enqueue(&pkt);
}

// Check if there are packets pending in the TX queue
bool lora_radio_tx_pending(void) {
    return tx_queue_count > 0 && !tx_in_progress;
}

// Send the next packet in the TX queue
void lora_radio_send_next(void) {
    if (tx_queue_count == 0 || tx_in_progress) {
        return;
    }

    lora_packet_t *pkt = &tx_queue[tx_queue_tail];

    // If this is an alert, switch to SF12 for max range
    if (pkt->type == PKT_TYPE_ALERT) {
        uint8_t mod_params[4] = { LORA_SF_ALERT, 0x04, 0x01, 0x00 };
        sx1262_write_command_with_data(SX1262_OP_SET_MOD_PARAMS, mod_params, 4);
        busy_wait_us(1000);  // Allow modem to settle
    }

    // Write data to TX buffer
    sx1262_wait_busy();
    sx1262_cs_select();
    uint8_t write_cmd = SX1262_OP_WRITE_BUFFER;
    uint8_t offset[1] = { 0x00 };  // Offset in buffer
    spi_write_blocking(spi1, &write_cmd, 1);
    spi_write_blocking(spi1, offset, 1);
    spi_write_blocking(spi1, pkt->data, pkt->length);
    sx1262_cs_deselect();

    // Set RF switch to TX
    gpio_put(SX1262_RF_SW_PIN, 0);  // TX path

    // Start transmission (timeout: 10 seconds for SF12)
    uint8_t tx_timeout[3] = { 0x00, 0x27, 0x10 };  // ~10s timeout
    sx1262_write_command_with_data(SX1262_OP_SET_TX, tx_timeout, 3);

    tx_in_progress = true;
    printf("LoRa: TX type=%d len=%d (queue: %d)\n", pkt->type, pkt->length, tx_queue_count);

    // Wait for TX done (polling for simplicity; in production use DIO1 interrupt)
    uint32_t timeout = 15000000;  // 15 seconds max
    while (tx_in_progress && timeout > 0) {
        // Check DIO1 for TX done interrupt
        if (gpio_get(SX1262_DIO1_PIN)) {
            // Read and clear IRQ status
            uint8_t irq_status[2];
            sx1262_wait_busy();
            sx1262_cs_select();
            uint8_t get_irq_cmd = SX1262_OP_GET_IRQ_STATUS;
            spi_write_blocking(spi1, &get_irq_cmd, 1);
            spi_read_blocking(spi1, 0xFF, irq_status, 2);
            sx1262_cs_deselect();

            uint16_t irq_flags = ((uint16_t)irq_status[0] << 8) | irq_status[1];

            if (irq_flags & SX1262_IRQ_TX_DONE) {
                tx_in_progress = false;
                printf("LoRa: TX complete\n");
            }

            if (irq_flags & SX1262_IRQ_TIMEOUT) {
                tx_in_progress = false;
                printf("LoRa: TX timeout\n");
            }

            // Clear IRQ flags
            uint8_t clear_irq[2] = { irq_status[0], irq_status[1] };
            sx1262_write_command_with_data(SX1262_OP_CLEAR_IRQ_STATUS, clear_irq, 2);
        }

        busy_wait_us(1);
        timeout--;
    }

    if (timeout == 0) {
        printf("LoRa: TX timeout (firmware)\n");
        tx_in_progress = false;
    }

    // Switch back to RX
    gpio_put(SX1262_RF_SW_PIN, 1);  // RX path

    // If we used SF12 for an alert, switch back to SF7
    if (pkt->type == PKT_TYPE_ALERT) {
        uint8_t mod_params[4] = { LORA_SF_NORMAL, 0x04, 0x01, 0x00 };
        sx1262_write_command_with_data(SX1262_OP_SET_MOD_PARAMS, mod_params, 4);
    }

    // Dequeue
    tx_queue_tail = (tx_queue_tail + 1) % TX_QUEUE_SIZE;
    tx_queue_count--;
}