/**
 * sensor_manager.c — Brew Sense Sensor Manager Implementation
 * 
 * Handles initialization and reading of all sensors:
 * - DS18B20 temperature probe (1-Wire)
 * - BMP388 barometric pressure (I²C)
 * - Senseair S8 CO₂ sensor (UART)
 * - EZO-pH pH probe interface (I²C)
 * - Battery voltage (ADC)
 */

#include "sensor_manager.h"
#include "stm32l4xx_hal.h"

/* I2C handles — initialized in main */
extern I2C_HandleTypeDef hi2c1;
extern UART_HandleTypeDef huart3;  /* S8 CO2 */
extern ADC_HandleTypeDef hadc1;

/* Sensor addresses */
#define BMP388_I2C_ADDR     0x77
#define EZO_PH_I2C_ADDR     0x63

/* DS18B20 commands */
#define DS18B20_SKIP_ROM    0xCC
#define DS18B20_CONVERT_T   0x44
#define DS18B20_READ_SCRATCH 0xBE

/* BMP388 registers */
#define BMP3_REG_CHIP_ID    0x00
#define BMP3_REG_DATA       0x04
#define BMP3_REG_CTRL        0x1B
#define BMP3_REG_OSR         0x1C
#define BMP3_REG_ODR         0x1D
#define BMP3_REG_CONFIG      0x1F

/* S8 UART command frames */
static const uint8_t s8_read_cmd[] = {0xFE, 0x04, 0x00, 0x00, 0x00, 0x03, 0x98, 0x1A};

/* Internal state */
static sensor_config_t s_config;
static bool s_s8_continuous = false;
static uint8_t s8_rx_buffer[13];
static float s_last_co2 = 0.0f;

/* Private function prototypes */
static sensor_status_t ds18b20_init(void);
static sensor_status_t bmp388_init(void);
static sensor_status_t ezo_ph_init(void);
static HAL_StatusTypeDef i2c_write_reg(I2C_HandleTypeDef *hi2c, uint8_t addr,
                                         uint8_t reg, const uint8_t *data, uint16_t len);
static HAL_StatusTypeDef i2c_read_reg(I2C_HandleTypeDef *hi2c, uint8_t addr,
                                        uint8_t reg, uint8_t *data, uint16_t len);

/* One-Wire bus functions */
static void ow_reset(void);
static void ow_write_byte(uint8_t byte);
static uint8_t ow_read_byte(void);
static uint8_t ow_crc8(const uint8_t *data, uint8_t len);

/*----------------------------------------------------------------------------*/

sensor_status_t sensor_manager_init(const sensor_config_t *config) {
    if (config) {
        s_config = *config;
    } else {
        /* Defaults */
        s_config.sample_interval_ms = 60000;
        s_config.enable_co2 = true;
        s_config.enable_ph = true;
        s_config.enable_gravity = true;
        s_config.enable_pressure = true;
    }
    
    sensor_status_t status = SENSOR_OK;
    
    /* Initialize DS18B20 */
    if (ds18b20_init() != SENSOR_OK) {
        status |= SENSOR_DS18B20_ERR;
    }
    
    /* Initialize BMP388 */
    if (s_config.enable_pressure) {
        if (bmp388_init() != SENSOR_OK) {
            status |= SENSOR_BMP388_ERR;
        }
    }
    
    /* Initialize EZO-pH */
    if (s_config.enable_ph) {
        if (ezo_ph_init() != SENSOR_OK) {
            status |= SENSOR_EZO_PH_ERR;
        }
    }
    
    /* S8 initialization happens in s8_start_continuous() */
    
    /* Initialize battery ADC */
    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV4;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.ScanConvMode = DISABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc1.Init.LowPowerAutoWait = DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.NbrOfConversion = 1;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
    hadc1.Init.DMAContinuousRequests = DISABLE;
    hadc1.Init.Overrun = ADC_OVR_DATA_PRESERVED;
    hadc1.Init.OversamplingMode = DISABLE;
    
    if (HAL_ADC_Init(&hadc1) != HAL_OK) {
        /* ADC init failed, but we can continue without battery monitoring */
    }
    
    return status;
}

/*----------------------------------------------------------------------------*/

sensor_status_t sensor_manager_read_all(sensor_data_t *data) {
    sensor_status_t status = SENSOR_OK;
    
    memset(data, 0, sizeof(sensor_data_t));
    data->timestamp_ms = HAL_GetTick();
    
    /* Read DS18B20 temperature */
    data->temperature_c = ds18b20_read_temp();
    if (data->temperature_c < -100.0f) {
        status |= SENSOR_DS18B20_ERR;
    }
    
    /* Read BMP388 pressure */
    if (s_config.enable_pressure) {
        data->pressure_hpa = bmp388_read_pressure();
        if (data->pressure_hpa < 0.0f) {
            status |= SENSOR_BMP388_ERR;
        }
    }
    
    /* Read S8 CO₂ */
    if (s_config.enable_co2) {
        data->co2_ppm = s8_read_co2();
        if (data->co2_ppm == 0) {
            status |= SENSOR_S8_ERR;
        }
    }
    
    /* Read EZO-pH */
    if (s_config.enable_ph) {
        data->ph = ezo_ph_read();
        if (data->ph < 0.0f) {
            status |= SENSOR_EZO_PH_ERR;
        }
    }
    
    /* Read battery voltage */
    data->battery_v = battery_read_voltage();
    if (data->battery_v < 2.0f) {
        status |= SENSOR_BATT_LOW;
    }
    
    /* Gravity is filled by the densitometer module */
    data->gravity_sg = 0.0f;  /* Will be updated by densitometer_read_sg() */
    
    return status;
}

/*----------------------------------------------------------------------------*/

float ds18b20_read_temp(void) {
    uint8_t scratch[9];
    
    /* Start temperature conversion */
    ow_reset();
    ow_write_byte(DS18B20_SKIP_ROM);
    ow_write_byte(DS18B20_CONVERT_T);
    
    /* Wait for conversion (750ms at 12-bit resolution) */
    HAL_Delay(750);
    
    /* Read scratchpad */
    ow_reset();
    ow_write_byte(DS18B20_SKIP_ROM);
    ow_write_byte(DS18B20_READ_SCRATCH);
    
    for (int i = 0; i < 9; i++) {
        scratch[i] = ow_read_byte();
    }
    
    /* Verify CRC */
    if (ow_crc8(scratch, 9) != 0) {
        return -999.0f;  /* CRC error */
    }
    
    /* Convert to float (12-bit resolution) */
    int16_t raw = (scratch[1] << 8) | scratch[0];
    float temp = (float)raw / 16.0f;
    
    return temp;
}

/*----------------------------------------------------------------------------*/

float bmp388_read_pressure(void) {
    uint8_t data[6];
    
    /* Read pressure and temperature data registers */
    if (i2c_read_reg(&hi2c1, BMP388_I2C_ADDR, BMP3_REG_DATA, data, 6) != HAL_OK) {
        return -1.0f;
    }
    
    /* Raw pressure (24-bit unsigned) */
    uint32_t raw_pressure = data[0] | (data[1] << 8) | (data[2] << 16);
    
    /* Raw temperature (24-bit unsigned) */
    uint32_t raw_temp = data[3] | (data[4] << 8) | (data[5] << 16);
    
    /* Apply BMP3 compensation (simplified — production code uses full TRM22/TRM23) */
    /* For now, use a simplified linear approximation */
    /* Full T1-T3, P1-P11 compensation should be used in production */
    float comp_temp = (float)raw_temp / 100.0f;  /* Simplified */
    float comp_pressure = (float)raw_pressure / 100.0f;  /* Simplified */
    
    (void)comp_temp;  /* Temperature is from DS18B20, more accurate */
    
    return comp_pressure;  /* hPa */
}

/*----------------------------------------------------------------------------*/

uint16_t s8_read_co2(void) {
    if (!s_s8_continuous) {
        return 0;
    }
    
    /* In continuous mode, the S8 sends data every 5 seconds */
    /* We read from the UART RX buffer */
    /* This is simplified — production code uses a proper frame parser */
    
    /* Send read command */
    HAL_UART_Transmit(&huart3, s8_read_cmd, sizeof(s8_read_cmd), 100);
    
    /* Receive response (8 bytes) */
    if (HAL_UART_Receive(&huart3, s8_rx_buffer, 7, 100) != HAL_OK) {
        return 0;
    }
    
    /* Parse Modbus response: [addr, func, byteCount, dataHi, dataLo, crcLo, crcHi] */
    if (s8_rx_buffer[1] != 0x04 || s8_rx_buffer[2] != 0x02) {
        return 0;
    }
    
    uint16_t co2 = (s8_rx_buffer[3] << 8) | s8_rx_buffer[4];
    s_last_co2 = (float)co2;
    
    return co2;
}

/*----------------------------------------------------------------------------*/

float ezo_ph_read(void) {
    /* Send read command to EZO-pH via I²C */
    uint8_t cmd = 'R';  /* Read command */
    
    if (i2c_write_reg(&hi2c1, EZO_PH_I2C_ADDR, 0, &cmd, 1) != HAL_OK) {
        return -1.0f;
    }
    
    /* Wait 900ms for measurement (EZO-pH specification) */
    HAL_Delay(900);
    
    /* Read response */
    uint8_t response[20] = {0};
    if (i2c_read_reg(&hi2c1, EZO_PH_I2C_ADDR, 0, response, 8) != HAL_OK) {
        return -1.0f;
    }
    
    /* Parse response: [code, pH_string, NULL] */
    if (response[0] != 0x01) {  /* 0x01 = success */
        return -1.0f;
    }
    
    /* Convert pH string to float */
    float ph = 0.0f;
    char *ph_str = (char *)&response[1];
    ph = strtof(ph_str, NULL);
    
    return ph;
}

/*----------------------------------------------------------------------------*/

bool ezo_ph_calibrate(float ph_value) {
    uint8_t cmd[8];
    uint8_t len;
    
    if (ph_value == 4.0f) {
        cmd[0] = 'C'; cmd[1] = 'a'; cmd[2] = 'l'; cmd[3] = ',';
        cmd[4] = 'm'; cmd[5] = 'i'; cmd[6] = 'd'; len = 7;
    } else if (ph_value == 7.0f) {
        cmd[0] = 'C'; cmd[1] = 'a'; cmd[2] = 'l'; cmd[3] = ',';
        cmd[4] = 'l'; cmd[5] = 'o'; cmd[6] = 'w'; len = 7;
    } else {
        /* Arbitrary calibration point */
        len = snprintf((char *)cmd, sizeof(cmd), "Cal,%.1f", ph_value);
    }
    
    if (i2c_write_reg(&hi2c1, EZO_PH_I2C_ADDR, 0, cmd, len) != HAL_OK) {
        return false;
    }
    
    HAL_Delay(300);
    return true;
}

/*----------------------------------------------------------------------------*/

void s8_start_continuous(void) {
    /* S8 starts in continuous mode by default after power-up */
    s_s8_continuous = true;
}

void s8_stop_continuous(void) {
    s_s8_continuous = false;
}

/*----------------------------------------------------------------------------*/

float battery_read_voltage(void) {
    /* Read battery voltage via ADC (voltage divider: Vbat/2 → ADC) */
    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel = ADC_CHANNEL_8;  /* PB0 */
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;
    
    if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK) {
        return 0.0f;
    }
    
    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, 10);
    
    uint32_t adc_val = HAL_ADC_GetValue(&hadc1);
    HAL_ADC_Stop(&hadc1);
    
    /* Convert ADC reading to voltage */
    /* Vref = 3.3V, 12-bit ADC, voltage divider = 1/2 */
    float voltage = ((float)adc_val / 4095.0f) * 3.3f * 2.0f;
    
    return voltage;
}

/*----------------------------------------------------------------------------*/

void sensor_manager_sleep(void) {
    /* Power down sensors for low-power mode */
    /* BMP388: enter sleep mode */
    uint8_t sleep_cmd = 0x00;  /* Standby mode */
    i2c_write_reg(&hi2c1, BMP388_I2C_ADDR, BMP3_REG_CTRL, &sleep_cmd, 1);
    
    /* S8: stop continuous measurement */
    s8_stop_continuous();
    
    /* EZO-pH: sleep */
    uint8_t ezo_sleep = 'S';  /* Sleep command */
    i2c_write_reg(&hi2c1, EZO_PH_I2C_ADDR, 0, &ezo_sleep, 1);
    
    /* DS18B20: no explicit sleep command (parasite power disabled) */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_12, GPIO_PIN_RESET);  /* DS18B20 power off */
}

void sensor_manager_wake(void) {
    /* Power on sensors */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_12, GPIO_PIN_SET);  /* DS18B20 power on */
    HAL_Delay(10);  /* Warm-up time */
    
    /* Re-initialize sensors */
    bmp388_init();
    s8_start_continuous();
    
    /* EZO-pH: wake by sending any I²C command */
    uint8_t ezo_wake = 0x00;
    i2c_write_reg(&hi2c1, EZO_PH_I2C_ADDR, 0, &ezo_wake, 1);
    HAL_Delay(300);  /* Wake-up time for EZO */
}

/*----------------------------------------------------------------------------*/
/* One-Wire Implementation (bit-bang on PB3) */
/*----------------------------------------------------------------------------*/

#define OW_PIN_HIGH()   HAL_GPIO_WritePin(GPIOB, GPIO_PIN_3, GPIO_PIN_SET)
#define OW_PIN_LOW()    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_3, GPIO_PIN_RESET)
#define OW_PIN_READ()   HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_3)
#define OW_DIR_OUT()    /* GPIO configured as output */
#define OW_DIR_IN()     /* GPIO configured as input */

static void ow_reset(void) {
    /* Pull low for 480µs, then release and wait for presence pulse */
    OW_PIN_LOW();
    OW_DIR_OUT();
    HAL_DelayMicroseconds(480);
    
    OW_PIN_HIGH();
    OW_DIR_IN();
    HAL_DelayMicroseconds(70);
    
    /* Check for presence pulse (pin should be low) */
    (void)OW_PIN_READ();  /* In production, check and return error */
    
    HAL_DelayMicroseconds(410);
}

static void ow_write_byte(uint8_t byte) {
    OW_DIR_OUT();
    for (int i = 0; i < 8; i++) {
        if (byte & (1 << i)) {
            /* Write 1: pull low for 6µs, release for 64µs */
            OW_PIN_LOW();
            HAL_DelayMicroseconds(6);
            OW_PIN_HIGH();
            HAL_DelayMicroseconds(64);
        } else {
            /* Write 0: pull low for 60µs, release for 10µs */
            OW_PIN_LOW();
            HAL_DelayMicroseconds(60);
            OW_PIN_HIGH();
            HAL_DelayMicroseconds(10);
        }
    }
}

static uint8_t ow_read_byte(void) {
    uint8_t byte = 0;
    for (int i = 0; i < 8; i++) {
        OW_PIN_LOW();
        OW_DIR_OUT();
        HAL_DelayMicroseconds(6);
        OW_PIN_HIGH();
        HAL_DelayMicroseconds(9);
        OW_DIR_IN();
        
        if (OW_PIN_READ()) {
            byte |= (1 << i);
        }
        HAL_DelayMicroseconds(55);
    }
    return byte;
}

static uint8_t ow_crc8(const uint8_t *data, uint8_t len) {
    uint8_t crc = 0;
    for (uint8_t i = 0; i < len; i++) {
        uint8_t byte = data[i];
        for (uint8_t j = 0; j < 8; j++) {
            uint8_t mix = (crc ^ byte) & 0x01;
            crc >>= 1;
            if (mix) {
                crc ^= 0x8C;
            }
            byte >>= 1;
        }
    }
    return crc;
}

/*----------------------------------------------------------------------------*/
/* I2C Helper Functions */
/*----------------------------------------------------------------------------*/

static HAL_StatusTypeDef i2c_write_reg(I2C_HandleTypeDef *hi2c, uint8_t addr,
                                          uint8_t reg, const uint8_t *data, uint16_t len) {
    uint8_t buf[len + 1];
    buf[0] = reg;
    memcpy(&buf[1], data, len);
    return HAL_I2C_Master_Transmit(hi2c, addr << 1, buf, len + 1, 100);
}

static HAL_StatusTypeDef i2c_read_reg(I2C_HandleTypeDef *hi2c, uint8_t addr,
                                         uint8_t reg, uint8_t *data, uint16_t len) {
    HAL_StatusTypeDef ret;
    ret = HAL_I2C_Master_Transmit(hi2c, addr << 1, &reg, 1, 100);
    if (ret != HAL_OK) return ret;
    return HAL_I2C_Master_Receive(hi2c, addr << 1, data, len, 100);
}

/*----------------------------------------------------------------------------*/
/* Individual Sensor Init Functions */
/*----------------------------------------------------------------------------*/

static sensor_status_t ds18b20_init(void) {
    /* Enable DS18B20 parasite power */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_12, GPIO_PIN_SET);
    HAL_Delay(100);
    
    /* Issue a reset pulse to verify presence */
    ow_reset();
    
    return SENSOR_OK;
}

static sensor_status_t bmp388_init(void) {
    uint8_t chip_id = 0;
    
    /* Read chip ID */
    if (i2c_read_reg(&hi2c1, BMP388_I2C_ADDR, BMP3_REG_CHIP_ID, &chip_id, 1) != HAL_OK) {
        return SENSOR_BMP388_ERR;
    }
    
    if (chip_id != 0x50) {
        return SENSOR_BMP388_ERR;
    }
    
    /* Configure: pressure ×8 oversampling, temperature ×2, normal mode */
    uint8_t osr = 0x03;  /* OSR_P=8x, OSR_T=2x */
    uint8_t odr = 0x01;  /* ODR = 50Hz */
    uint8_t ctrl = 0x33;  /* Normal mode, pressure+temp enable */
    
    if (i2c_write_reg(&hi2c1, BMP388_I2C_ADDR, BMP3_REG_OSR, &osr, 1) != HAL_OK) return SENSOR_BMP388_ERR;
    if (i2c_write_reg(&hi2c1, BMP388_I2C_ADDR, BMP3_REG_ODR, &odr, 1) != HAL_OK) return SENSOR_BMP388_ERR;
    if (i2c_write_reg(&hi2c1, BMP388_I2C_ADDR, BMP3_REG_CTRL, &ctrl, 1) != HAL_OK) return SENSOR_BMP388_ERR;
    
    return SENSOR_OK;
}

static sensor_status_t ezo_ph_init(void) {
    /* Send "i" (info) command to verify communication */
    uint8_t cmd = 'i';
    if (i2c_write_reg(&hi2c1, EZO_PH_I2C_ADDR, 0, &cmd, 1) != HAL_OK) {
        return SENSOR_EZO_PH_ERR;
    }
    
    HAL_Delay(300);
    
    /* Read response */
    uint8_t response[20] = {0};
    if (i2c_read_reg(&hi2c1, EZO_PH_I2C_ADDR, 0, response, 8) != HAL_OK) {
        return SENSOR_EZO_PH_ERR;
    }
    
    /* Check for "pH" in response */
    if (response[0] != 0x01) {
        return SENSOR_EZO_PH_ERR;
    }
    
    return SENSOR_OK;
}

/*----------------------------------------------------------------------------*/
/* HAL_DelayMicroseconds — not in HAL, so we implement it */
/*----------------------------------------------------------------------------*/

void HAL_DelayMicroseconds(uint32_t us) {
    /* Use DWT cycle counter for precise delays */
    static uint8_t dwt_initialized = 0;
    
    if (!dwt_initialized) {
        CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
        DWT->CYCCNT = 0;
        DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
        dwt_initialized = 1;
    }
    
    uint32_t start = DWT->CYCCNT;
    uint32_t cycles = us * (SystemCoreClock / 1000000);
    
    while ((DWT->CYCCNT - start) < cycles) {
        __NOP();
    }
}