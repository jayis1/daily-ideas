/*
 * hall-puck / firmware / Core / Src / vdp_switch.c
 * Van der Pauw contact switch matrix (2× ADG714 8-channel SPST)
 *
 * ADG714 #1 (SW1, CS=PA15): controls current path to 4 sample contacts
 *   SW1.0 → Contact 1 (I force +)
 *   SW1.1 → Contact 2 (I force +)
 *   SW1.2 → Contact 3 (I force +)
 *   SW1.3 → Contact 4 (I force +)
 *   SW1.4 → Contact 1 (I force -)
 *   SW1.5 → Contact 2 (I force -)
 *   SW1.6 → Contact 3 (I force -)
 *   SW1.7 → Contact 4 (I force -)
 *
 * ADG714 #2 (SW2, CS=PB0): controls voltage sense to 4 sample contacts
 *   SW2.0 → Contact 1 (V sense +)
 *   SW2.1 → Contact 2 (V sense +)
 *   SW2.2 → Contact 3 (V sense +)
 *   SW2.3 → Contact 4 (V sense +)
 *   SW2.4 → Contact 1 (V sense -)
 *   SW2.5 → Contact 2 (V sense -)
 *   SW2.6 → Contact 3 (V sense -)
 *   SW2.7 → Contact 4 (V sense -)
 *
 * MIT License.
 */
#include "vdp_switch.h"
#include "ads122u04.h"
#include "current_source.h"
#include "main.h"

extern SPI_HandleTypeDef hspi1;

/* ADG714 SPI command: 16-bit write (0x00 = write all, 0x80 = update) */
#define ADG714_WRITE_CMD    0x00
#define ADG714_UPDATE_CMD   0x80

/* ---- SPI helpers ---- */
static void spi_cs_low(uint8_t cs_pin)
{
    if (cs_pin < 16) GPIOA->BSRR = (1 << cs_pin) << 16;
    else GPIOB->BSRR = (1 << (cs_pin - 16)) << 16;
}

static void spi_cs_high(uint8_t cs_pin)
{
    if (cs_pin < 16) GPIOA->BSRR = (1 << cs_pin);
    else GPIOB->BSRR = (1 << (cs_pin - 16));
}

static void adg714_write(uint8_t cs_pin, uint8_t switch_state)
{
    spi_cs_low(cs_pin);
    /* Write command byte + switch state byte */
    while (!(SPI1->SR & SPI_SR_TXE));
    *(volatile uint8_t *)&SPI1->DR = ADG714_WRITE_CMD;
    while (!(SPI1->SR & SPI_SR_RXNE));
    (void)SPI1->DR;
    while (!(SPI1->SR & SPI_SR_TXE));
    *(volatile uint8_t *)&SPI1->DR = switch_state;
    while (!(SPI1->SR & SPI_SR_RXNE));
    (void)SPI1->DR;
    /* Update switches */
    while (!(SPI1->SR & SPI_SR_TXE));
    *(volatile uint8_t *)&SPI1->DR = ADG714_UPDATE_CMD;
    while (!(SPI1->SR & SPI_SR_RXNE));
    (void)SPI1->DR;
    spi_cs_high(cs_pin);
}

/* ---- Configuration lookup ----
 * For each measurement config, define:
 *   sw1_state: which switches in ADG714 #1 (current) are ON
 *   sw2_state: which switches in ADG714 #2 (voltage) are ON
 *
 * Bit mapping:
 *   SW1: bit0=I+→C1, bit1=I+→C2, bit2=I+→C3, bit3=I+→C4
 *        bit4=I-→C1, bit5=I-→C2, bit6=I-→C3, bit7=I-→C4
 *   SW2: bit0=V+→C1, bit1=V+→C2, bit2=V+→C3, bit3=V+→C4
 *        bit4=V-→C1, bit5=V-→C2, bit6=V-→C3, bit7=V-→C4
 */

typedef struct {
    uint8_t sw1_state;
    uint8_t sw2_state;
} switch_config_t;

static const switch_config_t configs[] = {
    /* VDP_RA_FWD: I: 1→2, V: 3→4 */
    [VDP_RA_FWD]  = { (1<<0) | (1<<5),           /* I+→C1, I-→C2 */
                      (1<<2) | (1<<7) },          /* V+→C3, V-→C4 */
    /* VDP_RA_REV: I: 2→1, V: 4→3 */
    [VDP_RA_REV]  = { (1<<1) | (1<<4),           /* I+→C2, I-→C1 */
                      (1<<3) | (1<<6) },          /* V+→C4, V-→C3 */
    /* VDP_RB_FWD: I: 2→3, V: 4→1 */
    [VDP_RB_FWD]  = { (1<<1) | (1<<6),           /* I+→C2, I-→C3 */
                      (1<<3) | (1<<4) },          /* V+→C4, V-→C1 */
    /* VDP_RB_REV: I: 3→2, V: 1→4 */
    [VDP_RB_REV]  = { (1<<2) | (1<<5),           /* I+→C3, I-→C2 */
                      (1<<0) | (1<<7) },          /* V+→C1, V-→C4 */
    /* HALL_BP_FWD: I: 1→3, V: 2→4 (B+) */
    [HALL_BP_FWD] = { (1<<0) | (1<<6),           /* I+→C1, I-→C3 */
                      (1<<1) | (1<<7) },          /* V+→C2, V-→C4 */
    /* HALL_BP_REV: I: 3→1, V: 4→2 (B+) */
    [HALL_BP_REV] = { (1<<2) | (1<<4),           /* I+→C3, I-→C1 */
                      (1<<3) | (1<<5) },          /* V+→C4, V-→C2 */
    /* HALL_BM_FWD: I: 1→3, V: 2→4 (B-) */
    [HALL_BM_FWD] = { (1<<0) | (1<<6),
                      (1<<1) | (1<<7) },
    /* HALL_BM_REV: I: 3→1, V: 4→2 (B-) */
    [HALL_BM_REV] = { (1<<2) | (1<<4),
                      (1<<3) | (1<<5) },
    /* Contact checks: same as VdP configs */
    [CONTACT_CHECK_1] = { (1<<0) | (1<<5), (1<<2) | (1<<7) },
    [CONTACT_CHECK_2] = { (1<<1) | (1<<6), (1<<3) | (1<<4) },
    [CONTACT_CHECK_3] = { (1<<2) | (1<<7), (1<<0) | (1<<5) },
    [CONTACT_CHECK_4] = { (1<<3) | (1<<4), (1<<1) | (1<<6) },
    /* Short (zero cal): V+ and V- both to C1 */
    [SHORT_ZERO]  = { 0x00,                        /* no current */
                      (1<<0) | (1<<4) },          /* V+→C1, V-→C1 */
    /* All off */
    [SWITCH_OFF]  = { 0x00, 0x00 },
};

static const char *config_names[] = {
    "VDP_Ra_fwd", "VDP_Ra_rev", "VDP_Rb_fwd", "VDP_Rb_rev",
    "HALL_B+_fwd", "HALL_B+_rev", "HALL_B-_fwd", "HALL_B-_rev",
    "Check_1", "Check_2", "Check_3", "Check_4",
    "Short_Zero", "Off",
};

/* ---- Public API ---- */
void vdp_switch_init(void)
{
    /* Configure CS pins as output */
    GPIOA->MODER &= ~(3 << (SW1_CS_PIN * 2));
    GPIOA->MODER |= (1 << (SW1_CS_PIN * 2));  /* output */
    GPIOB->MODER &= ~(3 << (SW2_CS_PIN * 2));
    GPIOB->MODER |= (1 << (SW2_CS_PIN * 2));  /* output */

    /* CS high (inactive) */
    GPIOA->BSRR = (1 << SW1_CS_PIN);
    GPIOB->BSRR = (1 << SW2_CS_PIN);

    /* All switches off */
    vdp_switch_all_open();
}

void vdp_switch_set_config(vdp_config_t config)
{
    if (config > SWITCH_OFF) return;

    uint8_t sw1 = configs[config].sw1_state;
    uint8_t sw2 = configs[config].sw2_state;

    adg714_write(SW1_CS_PIN, sw1);
    adg714_write(SW2_CS_PIN, sw2);

    delay_ms(2);  /* switch settle time (ADG714: <100ns, but be safe) */
}

void vdp_switch_all_open(void)
{
    adg714_write(SW1_CS_PIN, 0x00);
    adg714_write(SW2_CS_PIN, 0x00);
}

bool vdp_switch_check_contact(int contact)
{
    /* Check contact by forcing small current through adjacent contacts
     * and measuring voltage. If contact is open, voltage will be near Vcc.
     * If contact is good, voltage will be small (< 100mV for < 100kΩ).
     */
    if (contact < 0 || contact > 3) return false;

    vdp_config_t check_configs[4] = {
        CONTACT_CHECK_1, CONTACT_CHECK_2, CONTACT_CHECK_3, CONTACT_CHECK_4
    };

    vdp_switch_set_config(check_configs[contact]);
    current_source_set(0.01f);  /* 10 µA test current */
    current_source_enable();
    delay_ms(5);

    float voltage_uv;
    ads122u04_read_voltage_uv(&voltage_uv);

    current_source_disable();
    vdp_switch_all_open();

    /* If voltage < 100mV (100000 µV), contact is good (< 100kΩ) */
    /* If voltage > 1V (1000000 µV), contact is open */
    return fabsf(voltage_uv) < 100000.0f;
}

const char *vdp_switch_config_name(vdp_config_t config)
{
    if (config > SWITCH_OFF) return "Unknown";
    return config_names[config];
}