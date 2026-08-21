/* optics.h — IR scatter detector */
#ifndef OPTICS_H
#define OPTICS_H

void  optics_init(void);
float optics_scatter(void);
float optics_scatter_baseline(void);
void  optics_calibrate_baseline(void);

#endif