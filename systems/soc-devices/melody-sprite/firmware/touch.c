/*
 * Melody Sprite — RP2040 FM Synthesizer
 * touch.c — MPR121 capacitive touch driver
 *
 * Uses two MPR121 controllers:
 *   U6 (I2C 0x5A) — 16-pad chromatic keyboard
 *   U7 (I2C 0x5B) — 8 function buttons
 */

#include "touch.h"
#include <string.h>

/* MPR121 Register Map */
#define MPR121_MHDR       0x2B
#define MPR121_NHDR       0x2C
#define MPR121_NCLR       0x2D
#define MPR121_FDLR       0x2E
#define MPR121_MHDF       0x2F
#define MPR121_NHDF       0x30
#define MPR121_NCLF       0x31
#define MPR121_FDLF       0x32
#define MPR121_NHDT       0x33
#define MPR121_NCLT       0x34
#define MPR121_FDLT       0x35
#define MPR121_DEBOUNCE   0x5B
#define MPR121_CONFIG1     0x5C
#define MPR121_CONFIG2     0x5D
#define MPR121_ECR        0x5E  /* Electrode Configuration Register */
#define MPR121_TOUCH0_7   0x00  /* Touch status registers */
#define MPR121_TOUCH8_11  0x01
#define MPR121_OOR0_7     0x02
#define MPR121_OOR8_11    0x03
#define MPR121_FILT_DATA  0x04  /* Filtered data registers */
#define MPR121_BASELINE   0x1E  /* Baseline registers */

/* I2C addresses */
#define MPR121_KBD_ADDR   0x5A
#define MPR121_BTN_ADDR   0x5B

/* GPIO pins */
#define MPR121_KBD_IRQ    14  /* GPIO14 — keyboard IRQ */
#define MPR121_BTN_IRQ    15  /* GPIO15 — button IRQ */
#define I2C_SDA_PIN        8
#define I2C_SCL_PIN        9

/* Stub I2C functions (would use Pico SDK hardware_i2c in real build) */
static int mpr121_write(uint8_t addr, uint8_t reg, uint8_t val) { (void)addr; (void)reg; (void)val; return 0; }
static int mpr121_read(uint8_t addr, uint8_t reg) { (void)addr; (void)reg; return 0; }
static uint16_t mpr121_read16(uint8_t addr, uint8_t reg) { (void)addr; (void)reg; return 0; }

/* Initialize one MPR121 controller */
static int mpr121_init(uint8_t addr)
{
    /* Soft reset */
    mpr121_write(addr, MPR121_ECR, 0x00);  /* Stop all electrodes */

    /* Set CDT (Charge Discharge Time) and other filtering */
    mpr121_write(addr, MPR121_MHDR, 0x01);
    mpr121_write(addr, MPR121_NHDR, 0x01);
    mpr121_write(addr, MPR121_NCLR, 0x00);
    mpr121_write(addr, MPR121_FDLR, 0x00);

    mpr121_write(addr, MPR121_MHDF, 0x01);
    mpr121_write(addr, MPR121_NHDF, 0x01);
    mpr121_write(addr, MPR121_NCLF, 0x00);
    mpr121_write(addr, MPR121_FDLF, 0x00);

    mpr121_write(addr, MPR121_NHDT, 0x00);
    mpr121_write(addr, MPR121_NCLT, 0x00);
    mpr121_write(addr, MPR121_FDLT, 0x00);

    /* Debounce: touch = 2 samples, release = 4 samples */
    mpr121_write(addr, MPR121_DEBOUNCE, 0x24);

    /* Config register 1: FFI = 6 samples, SFI = 6 samples */
    mpr121_write(addr, MPR121_CONFIG1, 0x33);

    /* Config register 2: CDT = 2µs, ESI = 1ms */
    mpr121_write(addr, MPR121_CONFIG2, 0x22);

    /* Enable electrodes with touch/release thresholds */
    /* Threshold = TOUCH_THRESHOLD (12) touch, TOUCH_RELEASE (8) release */
    for (int i = 0; i < 12; i++) {
        mpr121_write(addr, 0x41 + i * 2, TOUCH_THRESHOLD);  /* Touch threshold */
        mpr121_write(addr, 0x42 + i * 2, TOUCH_RELEASE);    /* Release threshold */
    }

    /* Enable electrodes 0-11 */
    mpr121_write(addr, MPR121_ECR, 0x8F); /* ECR: CL=8, EXE=1, ELE_EN=0F (all 12) */

    return 0;
}

void touch_init(touch_controller_t *tc)
{
    memset(tc, 0, sizeof(touch_controller_t));

    /* Initialize I2C at 400kHz */
    /* Real: i2c_init(i2c0, 400000); i2c_gpio_init... */

    /* Initialize both MPR121 controllers */
    mpr121_init(MPR121_KBD_ADDR);
    mpr121_init(MPR121_BTN_ADDR);

    /* Set up IRQ pins as inputs with pull-ups */
    /* Real: gpio_set_dir(MPR121_KBD_IRQ, GPIO_IN); gpio_pull_up(MPR121_KBD_IRQ); */
    /* Real: gpio_set_dir(MPR121_BTN_IRQ, GPIO_IN); gpio_pull_up(MPR121_BTN_IRQ); */

    /* Calibrate baselines */
    touch_recalibrate(tc);

    tc->initialized = true;
}

void touch_set_key_callback(touch_controller_t *tc, touch_event_cb_t cb)
{
    tc->key_callback = cb;
}

void touch_set_button_callback(touch_controller_t *tc, button_event_cb_t cb)
{
    tc->button_callback = cb;
}

void touch_scan(touch_controller_t *tc)
{
    if (!tc->initialized) return;

    /* Read keyboard touch state (MPR121 #1, 16 keys = 2 × 8-bit regs + overflow) */
    uint16_t kbd_state = mpr121_read16(MPR121_KBD_ADDR, MPR121_TOUCH0_7);
    /* Upper byte = electrodes 8-11, lower = 0-7; we use all 16 via both reg pairs */
    /* For 16 keys on one MPR121, we'd use electrodes 0-11 + 4 virtual or */
    /* split across two MPR121s. Our design uses MPR121 #1 for keys 0-11 */
    /* and keys 12-15 from MPR121 #2 (sharing with func buttons) */
    /* Simplified: read 16 bits across both controllers */

    /* Process keyboard keys */
    for (int i = 0; i < TOUCH_NUM_KEYS; i++) {
        uint16_t mask = (1 << (i % 12));
        bool currently_touched = (kbd_state & mask) != 0;

        tc->keys[i].prev_touched = tc->keys[i].touched;
        tc->keys[i].touched = currently_touched;

        if (currently_touched && !tc->keys[i].prev_touched) {
            /* Key pressed — calculate velocity from touch strength */
            uint8_t velocity = 100; /* Default medium velocity */
            if (tc->key_callback) {
                tc->key_callback(i, velocity, true);
            }
        } else if (!currently_touched && tc->keys[i].prev_touched) {
            /* Key released */
            if (tc->key_callback) {
                tc->key_callback(i, 0, false);
            }
        }
    }

    /* Read function buttons (MPR121 #2) */
    uint16_t btn_state = mpr121_read16(MPR121_BTN_ADDR, MPR121_TOUCH0_7);

    for (int i = 0; i < TOUCH_NUM_BUTTONS; i++) {
        bool pressed = (btn_state & (1 << i)) != 0;

        tc->buttons[i].prev_pressed = tc->buttons[i].pressed;
        tc->buttons[i].pressed = pressed;

        if (pressed && !tc->buttons[i].prev_pressed) {
            if (tc->button_callback) {
                tc->button_callback(i, true);
            }
        } else if (!pressed && tc->buttons[i].prev_pressed) {
            if (tc->button_callback) {
                tc->button_callback(i, false);
            }
        }
    }
}

void touch_recalibrate(touch_controller_t *tc)
{
    (void)tc;
    /* In real implementation:
     * 1. Stop all electrodes (ECR = 0)
     * 2. Wait for auto-configuration to run
     * 3. Read baseline values from MPR121_BASELINE registers
     * 4. Store in tc->keys[i].baseline
     * 5. Re-enable electrodes
     */
}

bool touch_is_key_pressed(const touch_controller_t *tc, uint8_t key)
{
    if (key >= TOUCH_NUM_KEYS) return false;
    return tc->keys[key].touched;
}

bool touch_is_button_pressed(const touch_controller_t *tc, uint8_t button)
{
    if (button >= TOUCH_NUM_BUTTONS) return false;
    return tc->buttons[button].pressed;
}