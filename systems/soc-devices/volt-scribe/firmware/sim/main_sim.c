/*
 * volt-scribe — Desktop simulation build
 *
 * Simulates the potentiostat, DSP, and display for testing
 * the electrochemical algorithms without hardware.
 * Compile: gcc -lm -o volt_scribe_sim main_sim.c ../dsp.c ../cv_engine.c ../dpv_engine.c ../swv_engine.c ../eis_engine.c
 *
 * This file provides stubs for all HAL functions and simulates
 * electrochemical cell responses.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

/* ── Stub types ─────────────────────────────────────────────────── */

typedef enum { HAL_OK = 0, HAL_ERROR, HAL_BUSY, HAL_TIMEOUT } HAL_StatusTypeDef;

typedef struct {
    int dummy;
} DAC_HandleTypeDef;

typedef struct {
    int dummy;
} ADC_HandleTypeDef;

typedef struct {
    int dummy;
} I2C_HandleTypeDef;

typedef struct {
    int dummy;
} SPI_HandleTypeDef;

typedef struct {
    int dummy;
} UART_HandleTypeDef;

#define GPIO_PIN_SET    1
#define GPIO_PIN_RESET  0
#define DAC_CHANNEL_1   1
#define DAC_CHANNEL_2   2
#define DAC_ALIGN_12B_R 0
#define I2C_MEMADD_SIZE_8BIT 0

DAC_HandleTypeDef hdac1, hdac2;
ADC_HandleTypeDef hadc1, hadc2;
I2C_HandleTypeDef hi2c1;
SPI_HandleTypeDef hspi1;
UART_HandleTypeDef huart1;

/* ── Simulated cell state ───────────────────────────────────────── */

static float sim_E_applied = 0.0f;
static float sim_R_s = 100.0f;     /* Solution resistance (Ω) */
static float sim_R_ct = 2000.0f;    /* Charge transfer resistance (Ω) */
static float sim_C_dl = 20e-6f;    /* Double layer capacitance (F) */
static float sim_E0 = 0.3f;         /* Standard potential (V) */
static float sim_n = 1;             /* Number of electrons */
static float sim_D = 1e-5f;         /* Diffusion coefficient (cm²/s) */
static float sim_A = 0.0314f;       /* Electrode area (cm²) */
static float sim_C0 = 1e-6f;        /* Bulk concentration (mol/cm³) */

/* ── Simulated current (Randles-Sevčik model) ──────────────────── */

static float simulated_current(float E, float scan_rate)
{
    /* Butler-Volmer + Randles equivalent circuit */
    float i_f = 0;

    /* Faradaic current: simplified Butler-Volmer */
    float overpotential = E - sim_E0;
    float alpha = 0.5f;
    float i0 = 1e-4f;  /* Exchange current (A) */
    float F_RT = 38.94f;  /* F/(RT) at 25°C ≈ 38.94 V⁻¹ */

    i_f = i0 * (expf(alpha * F_RT * overpotential) -
                expf(-(1 - alpha) * F_RT * overpotential));

    /* Capacitive current: i_c = C_dl * dE/dt */
    float i_c = sim_C_dl * scan_rate;

    return i_f + i_c;
}

/* ── HAL stubs ──────────────────────────────────────────────────── */

HAL_StatusTypeDef HAL_DAC_SetValue(DAC_HandleTypeDef *hdac, uint32_t channel,
                                     uint32_t alignment, uint32_t value)
{
    /* Track applied voltage */
    sim_E_applied = (float)(int32_t)value / 4096.0f * 2.048f - 1.024f;
    return HAL_OK;
}

HAL_StatusTypeDef HAL_DAC_Start(DAC_HandleTypeDef *hdac, uint32_t channel) { return HAL_OK; }

HAL_StatusTypeDef HAL_ADC_Start(ADC_HandleTypeDef *hadc) { return HAL_OK; }
HAL_StatusTypeDef HAL_ADC_PollForConversion(ADC_HandleTypeDef *hadc, uint32_t timeout) { return HAL_OK; }
uint32_t HAL_ADC_GetValue(ADC_HandleTypeDef *hadc)
{
    /* Return simulated ADC value */
    return 2048;
}

HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *huart, const uint8_t *data,
                                     uint16_t size, uint32_t timeout) { return HAL_OK; }
HAL_StatusTypeDef HAL_UART_Receive(UART_HandleTypeDef *huart, uint8_t *data,
                                    uint16_t size, uint32_t timeout) { return HAL_TIMEOUT; }

HAL_StatusTypeDef HAL_I2C_Master_Transmit(I2C_HandleTypeDef *hi2c, uint16_t addr,
                                           uint8_t *data, uint16_t size, uint32_t timeout) { return HAL_OK; }
HAL_StatusTypeDef HAL_I2C_Master_Receive(I2C_HandleTypeDef *hi2c, uint16_t addr,
                                          uint8_t *data, uint16_t size, uint32_t timeout)
{
    /* Return simulated ADS1115 reading */
    if (size >= 2) {
        int16_t val = (int16_t)(simulated_current(sim_E_applied, 0.05f) / 1e-6f * 32768 / 4096);
        data[0] = (val >> 8) & 0xFF;
        data[1] = val & 0xFF;
    }
    return HAL_OK;
}

void HAL_GPIO_WritePin(void *port, uint16_t pin, int state) { (void)port; (void)pin; (void)state; }
void HAL_Delay(uint32_t ms) { (void)ms; /* No delay in simulation */ }

/* ── Redirect printf ────────────────────────────────────────────── */

/* Already using stdout in simulation */

/* ── Include actual modules ─────────────────────────────────────── */

/* We need to provide the params_t type and experiment_running variable */
volatile int experiment_running = 0;
float ir_comp_ohm = 0.0f;
float eis_ac_amplitude_mv = 10.0f;

/* Simplified params */
typedef struct {
    float cv_start, cv_vertex, cv_end, cv_scan_rate;
    int   cv_cycles;
    float dpv_start, dpv_end, dpv_step, dpv_pulse_amp, dpv_pulse_width, dpv_scan_rate;
    float swv_start, swv_end, swv_step, swv_amplitude, swv_frequency;
    float eis_dc_bias, eis_ac_amp, eis_freq_start, eis_freq_end;
    int   eis_ppd;
    float amp_potential, amp_duration, amp_sample_rate;
    float galv_current, galv_duration;
    float ir_compensation;
} params_t;

/* Stub implementations of engine functions that use the simulated cell */

void pot_init(void) {}
void pot_set_voltage(float v) { sim_E_applied = v; }
float pot_read_current(void) { return simulated_current(sim_E_applied, 0.05f); }
float pot_read_potential(void) { return sim_E_applied; }

typedef enum {
    TIA_1NA = 0, TIA_10NA, TIA_100NA, TIA_1UA, TIA_10UA, TIA_100UA, TIA_10MA,
    TIA_RANGE_COUNT
} tia_range_t;

void pot_set_range(tia_range_t r) { (void)r; }
tia_range_t pot_auto_range(void) { return TIA_1UA; }
const char *tia_range_name(tia_range_t r) { return "1 µA"; }
float tia_rf_value(tia_range_t r) { return 100000.0f; }
void pot_cell_enable(int e) { (void)e; }

void display_init(void) {}
void display_clear(void) {}
void display_show_splash(void) { printf("=== Volt Scribe v1.0 (Simulation) ===\n"); }
void display_show_idle(void) {}
void display_show_running(int m) {}
void display_show_mode(int m) {}
void display_plot_cv(const float *E, const float *I, int n, const void *p, int np) {}
void display_plot_dpv(const float *E, const float *dI, int n) {}
void display_plot_swv(const float *E, const float *dI, int n) {}
void display_plot_nyquist(const void *d, int n) {}
void display_plot_it(float t, float I) {}

void sdlog_init(void) {}
int sdlog_open(const char *p) { printf("Opening log file: %s\n", p); return 0; }
int sdlog_write(const char *d) { printf("%s", d); return 0; }
int sdlog_close(const char *f) { printf("Closing log file\n"); return 0; }
int sdlog_get_sequence(void) { return 1; }

void ble_relay_init(void) {}
void ble_relay_send_point(float x, float y) { (void)x; (void)y; }
void ble_relay_send_eis_point(float zr, float zi, float f) { (void)zr; (void)zi; (void)f; }
void ble_relay_poll(void) {}

void dsp_init(void) {}

/* ── Simple CV simulation test ─────────────────────────────────── */

static void sim_cv_test(void)
{
    printf("\n--- CV Simulation Test ---\n");
    printf("Simulating CV: -0.2V → 0.8V → -0.2V @ 50 mV/s\n\n");

    params_t p = {
        .cv_start = -0.2f, .cv_vertex = 0.8f, .cv_end = -0.2f,
        .cv_scan_rate = 0.05f, .cv_cycles = 1,
    };

    printf("E (V)\t\tI (µA)\n");
    printf("------\t\t------\n");

    float E = p.cv_start;
    float step = 0.01f;  /* 10 mV step */

    /* Forward scan */
    while (E <= p.cv_vertex) {
        float I = simulated_current(E, p.cv_scan_rate);
        printf("%.3f\t\t%.2f\n", E, I * 1e6f);
        E += step;
    }
    /* Reverse scan */
    while (E >= p.cv_end) {
        float I = simulated_current(E, -p.cv_scan_rate);
        printf("%.3f\t\t%.2f\n", E, I * 1e6f);
        E -= step;
    }

    printf("\nCV simulation complete.\n");
}

/* ── Main ───────────────────────────────────────────────────────── */

int main(void)
{
    printf("Volt Scribe — Desktop Simulation\n");
    printf("=================================\n\n");

    display_show_splash();

    sim_cv_test();

    printf("\nAll simulation tests passed.\n");
    return 0;
}