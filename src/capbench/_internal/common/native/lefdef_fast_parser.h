#ifndef CAPBENCH_LEFDEF_FAST_PARSER_H
#define CAPBENCH_LEFDEF_FAST_PARSER_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    char* pin_name;
    char* pin_use;
    char* layer;
    double x0;
    double y0;
    double x1;
    double y1;
} LfdPinRect;

typedef struct {
    char* layer;
    double x0;
    double y0;
    double x1;
    double y1;
} LfdObsRect;

typedef struct {
    char* name;
    double size_x;
    double size_y;
    LfdPinRect* pin_rects;
    size_t pin_rect_count;
    LfdObsRect* obs_rects;
    size_t obs_rect_count;
} LfdMacro;

typedef struct {
    LfdMacro* macros;
    size_t macro_count;
} LfdLefParseResult;

typedef struct {
    char* component;
    char* pin;
} LfdConnection;

typedef struct {
    char* layer;
    double* points_xy;
    size_t point_count;
    double width;
    int has_width;
} LfdRoutingSegment;

typedef struct {
    char* name;
    LfdConnection* connections;
    size_t connection_count;
    LfdRoutingSegment* routing;
    size_t routing_count;
    char* use;
    int is_special;
} LfdNet;

typedef struct {
    char* name;
    char* cell_type;
    double x;
    double y;
    char* orient;
    char* status;
} LfdComponent;

typedef struct {
    char* design_name;
    char* tech_name;
    int units;
    double diearea[4];
    LfdComponent* components;
    size_t component_count;
    LfdNet* nets;
    size_t net_count;
    LfdNet* specialnets;
    size_t specialnet_count;
} LfdDefParseResult;

int lfd_parse_lef_abstracts(const char* file_path, LfdLefParseResult* out, char** error_message);
void lfd_free_lef_parse_result(LfdLefParseResult* result);

int lfd_parse_def_compact(const char* file_path, LfdDefParseResult* out, char** error_message);
void lfd_free_def_parse_result(LfdDefParseResult* result);

void lfd_free_error_message(char* message);

#ifdef __cplusplus
}
#endif

#endif
