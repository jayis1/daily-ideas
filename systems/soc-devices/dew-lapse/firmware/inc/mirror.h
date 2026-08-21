/* mirror.h — mirror film detection & tracking */
#ifndef MIRROR_H
#define MIRROR_H

int  mirror_track(float t_mirror, float t_ref, float *setpoint);
int  mirror_phase(void);
void mirror_reset(void);

#endif