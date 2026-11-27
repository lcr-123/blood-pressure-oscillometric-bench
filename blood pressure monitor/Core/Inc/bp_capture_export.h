#ifndef BP_CAPTURE_EXPORT_H
#define BP_CAPTURE_EXPORT_H
#include "bp_algorithm.h"

/* Writer returns1 only if the entire line was transmitted. No GPIO or IWDG here. */
typedef uint8_t (*BP_CaptureWriter_t)(const char *line);
uint8_t BP_CaptureExport_Begin(void);
void BP_CaptureExport_Cancel(void);
void BP_CaptureExport_Task(BP_CaptureWriter_t writer);
uint8_t BP_CaptureExport_IsActive(void);
#endif
