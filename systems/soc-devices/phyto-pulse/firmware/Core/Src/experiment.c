/*
 * experiment.c — Guided experiment engine
 * Phyto Pulse — Plant Electrophysiology Recorder
 */

#include "experiment.h"
#include "main.h"
#include <string.h>

static const experiment_t experiments[MAX_EXPERIMENTS] = {
    [EXP_VENUS_SNAP] = {
        .id = 0,
        .name = "Venus Flytrap Snap",
        .plant = "Dionaea muscipula",
        .instructions = {
            "1. Clip E1 to trap leaf",
            "2. Clip E2 to stem",
            "3. Touch trigger hair",
            "4. Touch again <20s",
        },
        .num_instructions = 4,
        .duration_ms = 60000,
        .expected_ap_min = 10.0f,
        .expected_ap_max = 100.0f,
        .expected_event_count = 2,
        .uses_stimulus = true,
    },
    [EXP_MIMOSA_FOLD] = {
        .id = 1,
        .name = "Mimosa Pudica Fold",
        .plant = "Mimosa pudica",
        .instructions = {
            "1. Clip E1 to petiole",
            "2. Clip E2 to stem",
            "3. Touch petiole base",
        },
        .num_instructions = 3,
        .duration_ms = 30000,
        .expected_ap_min = 5.0f,
        .expected_ap_max = 80.0f,
        .expected_event_count = 1,
        .uses_stimulus = true,
    },
    [EXP_LIGHT_DARK] = {
        .id = 2,
        .name = "Light-Dark Transition",
        .plant = "Any",
        .instructions = {
            "1. Clip E1 to leaf",
            "2. Clip E2 to stem",
            "3. Cover leaf (dark)",
            "4. Wait 5 min",
            "5. Uncover (light)",
        },
        .num_instructions = 5,
        .duration_ms = 600000,
        .expected_ap_min = 0.0f,
        .expected_ap_max = 50.0f,
        .expected_event_count = 0,  /* SWP event, not AP */
        .uses_stimulus = false,
    },
    [EXP_WOUNDING] = {
        .id = 3,
        .name = "Wounding Response",
        .plant = "Any",
        .instructions = {
            "1. Clip E1 to leaf",
            "2. Clip E2 to stem",
            "3. Cut leaf tip",
            "4. Watch for VP",
        },
        .num_instructions = 4,
        .duration_ms = 300000,
        .expected_ap_min = 5.0f,
        .expected_ap_max = 50.0f,
        .expected_event_count = 1,
        .uses_stimulus = false,
    },
    [EXP_COLD_SHOCK] = {
        .id = 4,
        .name = "Cold Shock",
        .plant = "Any",
        .instructions = {
            "1. Clip E1 to leaf",
            "2. Clip E2 to stem",
            "3. Touch ice to stem",
        },
        .num_instructions = 3,
        .duration_ms = 60000,
        .expected_ap_min = 5.0f,
        .expected_ap_max = 80.0f,
        .expected_event_count = 3,
        .uses_stimulus = true,
    },
    [EXP_ELECTRO_STIM] = {
        .id = 5,
        .name = "Electrical Stimulation",
        .plant = "Any",
        .instructions = {
            "1. Clip E1 to stem",
            "2. Clip E2 to stem (distal)",
            "3. Press STIM button",
            "4. Watch for AP",
        },
        .num_instructions = 4,
        .duration_ms = 30000,
        .expected_ap_min = 10.0f,
        .expected_ap_max = 100.0f,
        .expected_event_count = 1,
        .uses_stimulus = true,
    },
    [EXP_CIRCADIAN] = {
        .id = 6,
        .name = "Circadian Rhythm",
        .plant = "Any",
        .instructions = {
            "1. Clip E1 to leaf",
            "2. Clip E2 to stem",
            "3. Record 24h",
            "4. Watch SWP trend",
        },
        .num_instructions = 4,
        .duration_ms = 86400000,
        .expected_ap_min = 0.0f,
        .expected_ap_max = 20.0f,
        .expected_event_count = 0,
        .uses_stimulus = false,
    },
    [EXP_DROUGHT] = {
        .id = 7,
        .name = "Drought Stress",
        .plant = "Any",
        .instructions = {
            "1. Clip E1 to leaf",
            "2. Clip E2 to stem",
            "3. No water 2h+",
            "4. Watch SWP shift",
        },
        .num_instructions = 4,
        .duration_ms = 7200000,
        .expected_ap_min = 0.0f,
        .expected_ap_max = 30.0f,
        .expected_event_count = 0,
        .uses_stimulus = false,
    },
};

static int8_t  g_current_exp = -1;
static uint32_t g_exp_start_ms = 0;

const experiment_t *experiment_get(uint8_t id)
{
    if (id >= MAX_EXPERIMENTS) return NULL;
    return &experiments[id];
}

uint8_t experiment_count(void) { return MAX_EXPERIMENTS; }

int experiment_start(uint8_t id)
{
    if (id >= MAX_EXPERIMENTS) return -1;
    g_current_exp = (int8_t)id;
    g_exp_start_ms = HAL_GetTick();
    return 0;
}

bool experiment_is_running(void) { return g_current_exp >= 0; }
int8_t experiment_current(void) { return g_current_exp; }

void experiment_update(uint32_t timestamp_ms, const spike_event_t *events, int n_events)
{
    if (g_current_exp < 0) return;
    const experiment_t *exp = &experiments[g_current_exp];
    if (timestamp_ms - g_exp_start_ms > exp->duration_ms) {
        /* Auto-stop after duration */
        g_current_exp = -1;
    }
}

bool experiment_check_pass(uint8_t id, const spike_event_t *events, int n_events,
                            float *out_amplitude, uint16_t *out_count)
{
    if (id >= MAX_EXPERIMENTS) return false;
    const experiment_t *exp = &experiments[id];

    float max_amp = 0;
    int ap_count = 0;
    for (int i = 0; i < n_events; i++) {
        if (events[i].classification == EVENT_AP) {
            ap_count++;
            float a = fabsf(events[i].amplitude_mv);
            if (a > max_amp) max_amp = a;
        }
    }

    if (out_amplitude) *out_amplitude = max_amp;
    if (out_count) *out_count = ap_count;

    /* Pass if we got at least the expected number of APs in range */
    if (exp->expected_event_count > 0) {
        return ap_count >= exp->expected_event_count &&
               max_amp >= exp->expected_ap_min &&
               max_amp <= exp->expected_ap_max;
    }
    /* SWP-based experiments: check amplitude in range */
    return max_amp <= exp->expected_ap_max;
}

void experiment_stop(void)
{
    g_current_exp = -1;
}

void experiment_trigger_stimulus(void)
{
    /* Drive PC817 optocoupler: pulse STIM_EN high for 50 ms */
    HAL_GPIO_WritePin(STIM_EN_GPIO_Port, STIM_EN_Pin, GPIO_PIN_SET);
    HAL_Delay(50);
    HAL_GPIO_WritePin(STIM_EN_GPIO_Port, STIM_EN_Pin, GPIO_PIN_RESET);
}