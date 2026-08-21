/*
 * uv_lure.h — 395nm UV LED lure scheduling (day/night duty cycling)
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */
#ifndef ECHO_TRAP_UV_LURE_H
#define ECHO_TRAP_UV_LURE_H

void uv_lure_init(void);
void uv_lure_update(float ambient_lux);
void uv_lure_off(void);
void uv_lure_override(uint8_t duty);

#endif /* ECHO_TRAP_UV_LURE_H */