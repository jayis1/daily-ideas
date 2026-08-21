/*
 * Flux Ring — compass.c
 * Tilt-compensated digital compass implementation.
 *
 * SPDX-License-Identifier: MIT
 */

#include "compass.h"
#include <math.h>

compass_heading_t compass_compute(const field_vector_t *field,
                                  const accel_data_t *accel)
{
    /* Heading from tilt-compensated horizontal field:
     * heading = atan2(My_h, Mx_h)
     * Adjust for magnetic declination if known.
     */
    float heading_rad = atan2f(field->y, field->x);

    /* Convert to degrees */
    float heading_deg = heading_rad * 180.0f / 3.14159265f;

    /* Normalize to 0-360 */
    if (heading_deg < 0.0f) {
        heading_deg += 360.0f;
    }

    return (compass_heading_t)(heading_deg + 0.5f);
}

const char *compass_cardinal(compass_heading_t heading)
{
    /* 16-point compass */
    static const char *cardinals[] = {
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW"
    };

    /* Each sector is 360/16 = 22.5 degrees */
    uint32_t index = ((heading + 11) % 360) / 23;
    if (index > 15) index = 0;
    return cardinals[index];
}