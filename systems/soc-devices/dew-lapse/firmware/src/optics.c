/* optics.c — IR scatter detector with 38 kHz chopper and synchronous demod.
 *
 * The IR LED (PB1) is toggled at 38 kHz via TIM3. The phototransistor
 * (PB0) is sampled by ADC1_IN8 at ~10 kHz. Synchronous demodulation
 * rejects ambient light.
 */
#include "stm32l4xx_hal.h"
#include "config.h"
#include "optics.h"

extern TIM_HandleTypeDef htim3;
extern ADC_HandleTypeDef hadc1;

#define DEMOD_LEN  IR_DEMOD_LEN
static volatile uint16_t ir_samples[DEMOD_LEN];
static volatile int       ir_idx = 0;
static float scatter_baseline = 2048.0f;  /* mid-range ADC value */

void optics_init(void)
{
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);  /* 38 kHz on PB1 */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_SET);
}

/* ADC1_IN8 conversion-complete callback fills ir_samples[].
 * (HAL boilerplate: in adc.c we set up DMA from ADC1 channel 8 into
 * ir_samples at 10 kHz triggered by TIM3.) */
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1) {
        ir_idx = (ir_idx + 1) % DEMOD_LEN;
    }
}

/* Synchronous demodulator: subtract the mean (DC ambient) from the
 * 38 kHz-modulated signal to get the AC amplitude, which is the
 * scatter signal. We assume the ADC is sampling in sync with the
 * chopper (half-period high, half-period low). */
float optics_scatter(void)
{
    /* Sum even-index (LED on) and odd-index (LED off) separately.
     * scatter = mean(on) - mean(off). */
    int32_t sum_on = 0, sum_off = 0;
    int n_on = 0, n_off = 0;
    for (int i = 0; i < DEMOD_LEN; i += 2) {
        sum_on  += ir_samples[i];
        n_on++;
        if (i + 1 < DEMOD_LEN) {
            sum_off += ir_samples[i + 1];
            n_off++;
        }
    }
    float mean_on  = n_on  ? (float)sum_on  / n_on  : 0.0f;
    float mean_off = n_off ? (float)sum_off / n_off : 0.0f;
    return mean_on - mean_off;
}

float optics_scatter_baseline(void)
{
    return scatter_baseline;
}

void optics_calibrate_baseline(void)
{
    /* Take 1 s of samples with TEC off, no film → pure mirror scatter. */
    HAL_Delay(1100);
    scatter_baseline = optics_scatter();
}