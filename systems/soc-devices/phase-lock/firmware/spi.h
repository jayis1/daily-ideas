/*
 * spi.h — minimal SPI1 driver for the microSD card (PA5/PA7/PA13, CS=PB8)
 *         plus a thin SD-card block layer + file-write helper.
 */
#ifndef SPI_H
#define SPI_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

void    spi_init(void);
uint8_t spi_xfer(uint8_t b);
bool    sd_card_init(void);
void    sd_file_write_start(const char *prefix, uint16_t run_id, const char *header);
void    sd_file_append(const char *data);
void    sd_file_write_end(void);

#endif /* SPI_H */