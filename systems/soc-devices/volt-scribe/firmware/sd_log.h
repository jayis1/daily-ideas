/*
 * volt-scribe — sd_log.h
 */

#ifndef SD_LOG_H
#define SD_LOG_H

void sdlog_init(void);
int  sdlog_open(const char *prefix);
int  sdlog_write(const char *data);
int  sdlog_close(const char *filename);
int  sdlog_get_sequence(void);
const char *sdlog_get_filename(void);

#endif