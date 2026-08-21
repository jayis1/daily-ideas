/*
 * temperature.c — Peltier PID temperature control via ADS122U04 + PT1000
 *
 * ADS122U04: 24-bit delta-sigma ADC, SPI interface
 * PT1000: 4-wire ratiometric measurement with 1k reference resistor
 * TEC: TEC1-12704 driven by MT3601 boost + DRV8833 H-bridge (bidirectional)
 */

#include "main.h"
#include <math.h>
#include "temperature.h"
#include "i2c_util.h"

/* ADS122U04 registers */
#define ADS122_CMD_RESET    0x06
#define ADS122_CMD_START    0x08
#define ADS122_CMD_POWERDOWN 0x02
#define ADS122_CMD_RDATA    0x10
#define ADS122_CMD_RREG     0x20
#define ADS122_CMD_WREG     0x40

/* ── PID state ──────────────────────────────────────────── */
static struct {
    float integral;
    float prev_error;
    float target;
    uint8_t enabled;
    uint8_t heating;  /* 1 = heating, 0 = cooling */
} tec_pid;

/* ── ADS122U04 SPI helpers ──────────────────────────────── */
extern SPI_HandleTypeDef hspi1;

static void ads122_cs_low(void)  { HAL_GPIO_WritePin(FLASH_CS_PORT, FLASH_CS_PIN, GPIO_PIN_RESET); }
/* Note: ADS122 uses its own CS — in this design it shares SPI1 with flash.
 * In practice, a separate CS pin would be used. We'll use a software CS.
 */
static uint8_t ads122_xfer(uint8_t cmd)
{
    uint8_t tx = cmd, rx = 0;
    HAL_SPI_TransmitReceive(&hspi1, &tx, &rx, 1, 100);
    return rx;
}

static void ads122_write_reg(uint8_t reg, uint8_t val)
{
    ads122_xfer(ADS122_CMD_WREG | (reg << 2));
    ads122_xfer(val);
}

static uint8_t ads122_read_reg(uint8_t reg)
{
    ads122_xfer(ADS122_CMD_RREG | (reg << 2));
    return ads122_xfer(0xFF);
}

static void ads122_start_conv(void)
{
    ads122_xfer(ADS122_CMD_START);
}

static int32_t ads122_read_data(void)
{
    ads122_xfer(ADS122_CMD_RDATA);
    uint8_t b[3] = {0, 0, 0};
    HAL_SPI_Receive(&hspi1, b, 3, 100);
    int32_t val = ((int32_t)b[0] << 16) | ((int32_t)b[1] << 8) | b[2];
    /* Sign extend from 24-bit */
    if (val & 0x800000) val |= 0xFF000000;
    return val;
}

int temperature_init(void)
{
    /* Reset ADS122U04 */
    ads122_xfer(ADS122_CMD_RESET);
    HAL_Delay(1);

    /* Configure registers:
     * Reg 0: AINp=AIN0, AINn=AIN1, Gain=1, PGA bypass
     * Reg 1: Data rate=20 SPS, Mode=Normal, Conv=Continuous, VREF=External
     * Reg 2: No IDAC (external excitation)
     * Reg 3: No excitation current, VREF external on AIN0/AIN1
     */

    /* For 4-wire PT1000 ratiometric:
     * Drive reference resistor (1k) with excitation, measure PT1000 voltage.
     * R_PT1000 = V_pt1000 / V_ref * R_ref
     */

    ads122_write_reg(0, 0x01); /* AIN0+/AIN1-, gain 1, PGA bypassed */
    ads122_write_reg(1, 0x04); /* 20 SPS, continuous, external VREF */
    ads122_write_reg(2, 0x00);
    ads122_write_reg(3, 0x00);

    /* Initialize PID state */
    tec_pid.integral = 0;
    tec_pid.prev_error = 0;
    tec_pid.target = TEC_TEMP_DEFAULT;
    tec_pid.enabled = 0;
    tec_pid.heating = 0;

    /* Initialize TIM4 PWM for TEC */
    HAL_TIM_PWM_Start(&htim4, TIM_CHANNEL_3);

    return 0;
}

/* Read PT1000 resistance and convert to temperature.
 * PT1000 Callendar-Van Dusen: R(t) = R0 * (1 + A*t + B*t²) for t >= 0
 * A = 3.9083e-3, B = -5.775e-7
 * We solve the quadratic for t.
 */
float temperature_read(void)
{
    ads122_start_conv();
    HAL_Delay(55); /* 20 SPS → ~50ms conv time */

    int32_t raw = ads122_read_data();

    /* Convert to resistance ratio.
     * With 1k reference and gain 1, Vref = I_exc * R_ref
     * V_meas = I_exc * R_pt1000
     * Code = V_meas / Vref * 2^23 = R_pt1000 / R_ref * 2^23
     * R_pt1000 = Code / 2^23 * R_ref
     */
    float ratio = (float)raw / 8388608.0f; /* 2^23 */
    float r = ratio * RTD_R_REF;

    /* Callendar-Van Dusen (for t >= 0): t = (-A + sqrt(A² - 4B(1 - R/R0))) / (2B) */
    float A = 3.9083e-3f;
    float B = -5.775e-7f;
    float frac = r / RTD_R_REF;

    float discriminant = A * A - 4.0f * B * (1.0f - frac);
    if (discriminant < 0) return -999.0f;

    float temp = (-A + sqrtf(discriminant)) / (2.0f * B);
    return temp;
}

/* PID step — call at 10 Hz */
float temperature_pid_step(float target)
{
    float current = temperature_read();
    if (current < -100) return current; /* sensor error */

    float error = target - current;

    /* Determine heating or cooling */
    tec_pid.heating = (error > 0) ? 1 : 0;
    error = fabsf(error);

    /* PID */
    tec_pid.integral += error * 0.1f; /* 0.1s per step */
    float derivative = (error - tec_pid.prev_error) / 0.1f;
    tec_pid.prev_error = error;

    /* Anti-windup */
    if (tec_pid.integral > 50.0f) tec_pid.integral = 50.0f;
    if (tec_pid.integral < -50.0f) tec_pid.integral = -50.0f;

    float output = TEC_KP * error + TEC_KI * tec_pid.integral + TEC_KD * derivative;

    /* Clamp to 0-100% duty cycle */
    if (output < 0) output = 0;
    if (output > 100) output = 100;

    /* Set PWM duty cycle (TIM4 CH3) */
    uint32_t arr = __HAL_TIM_GET_AUTORELOAD(&htim4);
    uint32_t ccr = (uint32_t)(output * (float)arr / 100.0f);
    __HAL_TIM_SET_COMPARE(&htim4, TIM_CHANNEL_3, ccr);

    /* Set H-bridge direction (heating vs cooling) */
    if (tec_pid.heating) {
        HAL_GPIO_WritePin(VALVE_A_PORT, VALVE_A_PIN, GPIO_PIN_SET);
        HAL_GPIO_WritePin(VALVE_B_PORT, VALVE_B_PIN, GPIO_PIN_RESET);
    } else {
        HAL_GPIO_WritePin(VALVE_A_PORT, VALVE_A_PIN, GPIO_PIN_RESET);
        HAL_GPIO_WritePin(VALVE_B_PORT, VALVE_B_PIN, GPIO_PIN_SET);
    }

    return current;
}

void temperature_enable(void)
{
    tec_pid.enabled = 1;
    HAL_GPIO_WritePin(TEC_EN_PORT, TEC_EN_PIN, GPIO_PIN_SET);
}

void temperature_disable(void)
{
    tec_pid.enabled = 0;
    HAL_GPIO_WritePin(TEC_EN_PORT, TEC_EN_PIN, GPIO_PIN_RESET);
    __HAL_TIM_SET_COMPARE(&htim4, TIM_CHANNEL_3, 0);
}

int temperature_set_target(float target_c)
{
    if (target_c < TEC_TEMP_MIN || target_c > TEC_TEMP_MAX) return -1;
    tec_pid.target = target_c;
    tec_pid.integral = 0;
    tec_pid.prev_error = 0;
    return 0;
}

float temperature_get_tec_current(void)
{
    /* Read TEC current from current-sense amplifier (INA181A1, 20V/V)
     * via ADC2 on PC0.
     * Sense resistor: 0.1 ohm → I = V_sense / 0.1
     * ADC reads V_sense * 20, so I = ADC_voltage / (20 * 0.1) = ADC_voltage / 2
     */
    HAL_ADC_Start(&hadc2);
    HAL_ADC_PollForConversion(&hadc2, 10);
    uint32_t raw = HAL_ADC_GetValue(&hadc2);
    HAL_ADC_Stop(&hadc2);

    float v = (float)raw * 3.3f / 4095.0f;
    return v / 2.0f; /* amps */
}