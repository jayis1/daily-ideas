/*
 * pyro-balance / Core/Src/sd_logger.c — FATFS CSV + binary logging.
 */
#include "sd_logger.h"
#include "tga.h"
#include <stdio.h>
static FIL g_file; static FATFS g_fs; static bool g_sd_ok=false;

void sd_init(void){
    if (f_mount(&g_fs,"0:",1)==FR_OK) g_sd_ok=true;
}
bool sd_present(void){ return g_sd_ok; }

void sd_open_run(uint32_t method_id){
    if(!g_sd_ok) return;
    char name[32]; snprintf(name,sizeof(name),"0:/tga_%lu.csv",method_id);
    if (f_open(&g_file,name,FA_CREATE_ALWAYS|FA_WRITE)==FR_OK){
        f_printf(&g_file,"# Pyro Balance TGA run method=%lu\n",method_id);
        f_printf(&g_file,"time_s,temp_c,mass_mg,mass_pct,dtg_pct_per_min\n");
    }
}
void sd_log_point(float temp_c,float mass_mg,float mass_pct,float dtg,uint32_t t_ms){
    if(!g_sd_ok) return;
    f_printf(&g_file,"%lu,%.3f,%.3f,%.3f,%.4f\n",t_ms/1000,temp_c,mass_mg,mass_pct,dtg);
    f_sync(&g_file);
}
void sd_close_run(void){
    if(!g_sd_ok) return;
    const tga_run_t* r = tga_get();
    f_printf(&g_file,"# steps=%u residual_pct=%.3f\n",(unsigned)r->step_count,r->residual_pct);
    for (uint8_t i=0;i<r->step_count;i++){
        if(r->steps[i].valid)
            f_printf(&g_file,"# step %u onset=%.1f peak=%.1f endset=%.1f dmass=%.3f\n",
                i,r->steps[i].onset_c,r->steps[i].peak_c,r->steps[i].endset_c,r->steps[i].dmass_pct);
    }
    f_close(&g_file);
}
void sd_log_event(const char* msg){
    if(!g_sd_ok) return;
    f_printf(&g_file,"# event: %s\n",msg);
}
void sd_dump(const char* path, uint8_t* buf, uint32_t len){
    if(!g_sd_ok) return;
    FIL f; if(f_open(&f,path,FA_CREATE_ALWAYS|FA_WRITE)==FR_OK){ UINT w; f_write(&f,buf,len,&w); f_close(&f);}