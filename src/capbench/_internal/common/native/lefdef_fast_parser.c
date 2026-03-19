#define _POSIX_C_SOURCE 200809L

#include "lefdef_fast_parser.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define LFD_INITIAL_CAPACITY 8

typedef struct {
    char** items;
    size_t count;
    size_t capacity;
} LfdTokenList;

static void lfd_zero_memory(void* ptr, size_t size) {
    memset(ptr, 0, size);
}

static char* lfd_strdup_local(const char* src) {
    size_t len;
    char* out;
    if (src == NULL) {
        return NULL;
    }
    len = strlen(src);
    out = (char*)malloc(len + 1);
    if (out == NULL) {
        return NULL;
    }
    memcpy(out, src, len + 1);
    return out;
}

static void lfd_set_error(char** error_message, const char* prefix, const char* detail) {
    size_t prefix_len;
    size_t detail_len;
    char* out;
    if (error_message == NULL || *error_message != NULL) {
        return;
    }
    prefix_len = prefix != NULL ? strlen(prefix) : 0;
    detail_len = detail != NULL ? strlen(detail) : 0;
    out = (char*)malloc(prefix_len + detail_len + 3);
    if (out == NULL) {
        return;
    }
    if (prefix_len > 0) {
        memcpy(out, prefix, prefix_len);
    }
    if (detail_len > 0) {
        if (prefix_len > 0) {
            out[prefix_len] = ':';
            out[prefix_len + 1] = ' ';
            memcpy(out + prefix_len + 2, detail, detail_len);
            out[prefix_len + detail_len + 2] = '\0';
        } else {
            memcpy(out, detail, detail_len);
            out[detail_len] = '\0';
        }
    } else if (prefix_len > 0) {
        out[prefix_len] = '\0';
    } else {
        out[0] = '\0';
    }
    *error_message = out;
}

void lfd_free_error_message(char* message) {
    free(message);
}

static int lfd_ensure_capacity(void** buffer, size_t item_size, size_t* capacity, size_t required) {
    size_t new_capacity;
    void* resized;
    if (*capacity >= required) {
        return 1;
    }
    new_capacity = *capacity > 0 ? *capacity : LFD_INITIAL_CAPACITY;
    while (new_capacity < required) {
        new_capacity *= 2;
    }
    resized = realloc(*buffer, item_size * new_capacity);
    if (resized == NULL) {
        return 0;
    }
    *buffer = resized;
    *capacity = new_capacity;
    return 1;
}

static char* lfd_trim_inplace(char* line) {
    char* start;
    char* end;
    if (line == NULL) {
        return NULL;
    }
    start = line;
    while (*start != '\0' && isspace((unsigned char)*start)) {
        ++start;
    }
    end = start + strlen(start);
    while (end > start && isspace((unsigned char)end[-1])) {
        --end;
    }
    *end = '\0';
    return start;
}

static void lfd_strip_hash_comment(char* line) {
    char* hash;
    hash = strchr(line, '#');
    if (hash != NULL) {
        *hash = '\0';
    }
}

static int lfd_starts_with(const char* line, const char* prefix) {
    size_t prefix_len;
    prefix_len = strlen(prefix);
    return strncmp(line, prefix, prefix_len) == 0;
}

static void lfd_strip_semicolon_inplace(char* text) {
    size_t len;
    if (text == NULL) {
        return;
    }
    len = strlen(text);
    while (len > 0 && isspace((unsigned char)text[len - 1])) {
        text[--len] = '\0';
    }
    if (len > 0 && text[len - 1] == ';') {
        text[--len] = '\0';
    }
    while (len > 0 && isspace((unsigned char)text[len - 1])) {
        text[--len] = '\0';
    }
}

static int lfd_parse_double_list(const char* text, double* out, int count) {
    const char* cur;
    char* endptr;
    int idx;
    cur = text;
    idx = 0;
    while (*cur != '\0' && idx < count) {
        while (*cur != '\0' && !(isdigit((unsigned char)*cur) || *cur == '-' || *cur == '+' || *cur == '.')) {
            ++cur;
        }
        if (*cur == '\0') {
            break;
        }
        out[idx] = strtod(cur, &endptr);
        if (endptr == cur) {
            break;
        }
        ++idx;
        cur = endptr;
    }
    return idx == count;
}

static int lfd_append_token_slice(LfdTokenList* list, const char* start, size_t len) {
    char* token;
    if (!lfd_ensure_capacity((void**)&list->items, sizeof(char*), &list->capacity, list->count + 1)) {
        return 0;
    }
    token = (char*)malloc(len + 1);
    if (token == NULL) {
        return 0;
    }
    memcpy(token, start, len);
    token[len] = '\0';
    list->items[list->count++] = token;
    return 1;
}

static void lfd_free_tokens(LfdTokenList* list) {
    size_t idx;
    if (list == NULL) {
        return;
    }
    for (idx = 0; idx < list->count; ++idx) {
        free(list->items[idx]);
    }
    free(list->items);
    list->items = NULL;
    list->count = 0;
    list->capacity = 0;
}

static int lfd_tokenize(const char* text, LfdTokenList* out, char** error_message) {
    const char* cur;
    lfd_zero_memory(out, sizeof(*out));
    cur = text;
    while (*cur != '\0') {
        const char* start;
        while (*cur != '\0' && isspace((unsigned char)*cur)) {
            ++cur;
        }
        if (*cur == '\0') {
            break;
        }
        if (*cur == '(' || *cur == ')' || *cur == ';') {
            if (!lfd_append_token_slice(out, cur, 1)) {
                lfd_set_error(error_message, "tokenize", "out of memory");
                lfd_free_tokens(out);
                return 0;
            }
            ++cur;
            continue;
        }
        start = cur;
        while (
            *cur != '\0' &&
            !isspace((unsigned char)*cur) &&
            *cur != '(' &&
            *cur != ')' &&
            *cur != ';'
        ) {
            ++cur;
        }
        if (!lfd_append_token_slice(out, start, (size_t)(cur - start))) {
            lfd_set_error(error_message, "tokenize", "out of memory");
            lfd_free_tokens(out);
            return 0;
        }
    }
    return 1;
}

static int lfd_string_equals(const char* lhs, const char* rhs) {
    if (lhs == NULL || rhs == NULL) {
        return 0;
    }
    return strcmp(lhs, rhs) == 0;
}

static int lfd_string_case_equals(const char* lhs, const char* rhs) {
    unsigned char a;
    unsigned char b;
    if (lhs == NULL || rhs == NULL) {
        return 0;
    }
    while (*lhs != '\0' && *rhs != '\0') {
        a = (unsigned char)*lhs++;
        b = (unsigned char)*rhs++;
        if (toupper(a) != toupper(b)) {
            return 0;
        }
    }
    return *lhs == '\0' && *rhs == '\0';
}

static void lfd_replace_string(char** target, const char* src) {
    char* next_value;
    next_value = lfd_strdup_local(src != NULL ? src : "");
    if (next_value == NULL) {
        return;
    }
    free(*target);
    *target = next_value;
}

static int lfd_append_pin_rect(LfdMacro* macro, const LfdPinRect* rect) {
    static size_t capacity = 0;
    (void)capacity;
    if (!lfd_ensure_capacity(
            (void**)&macro->pin_rects,
            sizeof(LfdPinRect),
            &capacity,
            macro->pin_rect_count + 1
        )) {
        return 0;
    }
    macro->pin_rects[macro->pin_rect_count++] = *rect;
    return 1;
}

static int lfd_append_obs_rect(LfdMacro* macro, const LfdObsRect* rect) {
    static size_t capacity = 0;
    (void)capacity;
    if (!lfd_ensure_capacity(
            (void**)&macro->obs_rects,
            sizeof(LfdObsRect),
            &capacity,
            macro->obs_rect_count + 1
        )) {
        return 0;
    }
    macro->obs_rects[macro->obs_rect_count++] = *rect;
    return 1;
}

typedef struct {
    LfdPinRect* items;
    size_t count;
    size_t capacity;
} LfdPinRectVec;

typedef struct {
    LfdObsRect* items;
    size_t count;
    size_t capacity;
} LfdObsRectVec;

typedef struct {
    LfdComponent* items;
    size_t count;
    size_t capacity;
} LfdComponentVec;

typedef struct {
    LfdConnection* items;
    size_t count;
    size_t capacity;
} LfdConnectionVec;

typedef struct {
    LfdRoutingSegment* items;
    size_t count;
    size_t capacity;
} LfdRoutingVec;

typedef struct {
    LfdNet* items;
    size_t count;
    size_t capacity;
} LfdNetVec;

static int lfd_pin_rect_vec_push(LfdPinRectVec* vec, const LfdPinRect* value) {
    if (!lfd_ensure_capacity((void**)&vec->items, sizeof(LfdPinRect), &vec->capacity, vec->count + 1)) {
        return 0;
    }
    vec->items[vec->count++] = *value;
    return 1;
}

static int lfd_obs_rect_vec_push(LfdObsRectVec* vec, const LfdObsRect* value) {
    if (!lfd_ensure_capacity((void**)&vec->items, sizeof(LfdObsRect), &vec->capacity, vec->count + 1)) {
        return 0;
    }
    vec->items[vec->count++] = *value;
    return 1;
}

static int lfd_component_vec_push(LfdComponentVec* vec, const LfdComponent* value) {
    if (!lfd_ensure_capacity((void**)&vec->items, sizeof(LfdComponent), &vec->capacity, vec->count + 1)) {
        return 0;
    }
    vec->items[vec->count++] = *value;
    return 1;
}

static int lfd_connection_vec_push(LfdConnectionVec* vec, const LfdConnection* value) {
    if (!lfd_ensure_capacity((void**)&vec->items, sizeof(LfdConnection), &vec->capacity, vec->count + 1)) {
        return 0;
    }
    vec->items[vec->count++] = *value;
    return 1;
}

static int lfd_routing_vec_push(LfdRoutingVec* vec, const LfdRoutingSegment* value) {
    if (!lfd_ensure_capacity((void**)&vec->items, sizeof(LfdRoutingSegment), &vec->capacity, vec->count + 1)) {
        return 0;
    }
    vec->items[vec->count++] = *value;
    return 1;
}

static int lfd_net_vec_push(LfdNetVec* vec, const LfdNet* value) {
    if (!lfd_ensure_capacity((void**)&vec->items, sizeof(LfdNet), &vec->capacity, vec->count + 1)) {
        return 0;
    }
    vec->items[vec->count++] = *value;
    return 1;
}

static int lfd_macro_vec_push(LfdLefParseResult* result, const LfdMacro* value, size_t* capacity) {
    if (!lfd_ensure_capacity((void**)&result->macros, sizeof(LfdMacro), capacity, result->macro_count + 1)) {
        return 0;
    }
    result->macros[result->macro_count++] = *value;
    return 1;
}

static void lfd_free_pin_rect(LfdPinRect* rect) {
    free(rect->pin_name);
    free(rect->pin_use);
    free(rect->layer);
    lfd_zero_memory(rect, sizeof(*rect));
}

static void lfd_free_obs_rect(LfdObsRect* rect) {
    free(rect->layer);
    lfd_zero_memory(rect, sizeof(*rect));
}

static void lfd_free_macro(LfdMacro* macro) {
    size_t idx;
    free(macro->name);
    for (idx = 0; idx < macro->pin_rect_count; ++idx) {
        lfd_free_pin_rect(&macro->pin_rects[idx]);
    }
    free(macro->pin_rects);
    for (idx = 0; idx < macro->obs_rect_count; ++idx) {
        lfd_free_obs_rect(&macro->obs_rects[idx]);
    }
    free(macro->obs_rects);
    lfd_zero_memory(macro, sizeof(*macro));
}

void lfd_free_lef_parse_result(LfdLefParseResult* result) {
    size_t idx;
    if (result == NULL) {
        return;
    }
    for (idx = 0; idx < result->macro_count; ++idx) {
        lfd_free_macro(&result->macros[idx]);
    }
    free(result->macros);
    lfd_zero_memory(result, sizeof(*result));
}

static void lfd_free_component(LfdComponent* component) {
    free(component->name);
    free(component->cell_type);
    free(component->orient);
    free(component->status);
    lfd_zero_memory(component, sizeof(*component));
}

static void lfd_free_connection(LfdConnection* conn) {
    free(conn->component);
    free(conn->pin);
    lfd_zero_memory(conn, sizeof(*conn));
}

static void lfd_free_routing_segment(LfdRoutingSegment* segment) {
    free(segment->layer);
    free(segment->points_xy);
    lfd_zero_memory(segment, sizeof(*segment));
}

static void lfd_free_net(LfdNet* net) {
    size_t idx;
    free(net->name);
    free(net->use);
    for (idx = 0; idx < net->connection_count; ++idx) {
        lfd_free_connection(&net->connections[idx]);
    }
    free(net->connections);
    for (idx = 0; idx < net->routing_count; ++idx) {
        lfd_free_routing_segment(&net->routing[idx]);
    }
    free(net->routing);
    lfd_zero_memory(net, sizeof(*net));
}

void lfd_free_def_parse_result(LfdDefParseResult* result) {
    size_t idx;
    if (result == NULL) {
        return;
    }
    free(result->design_name);
    free(result->tech_name);
    for (idx = 0; idx < result->component_count; ++idx) {
        lfd_free_component(&result->components[idx]);
    }
    free(result->components);
    for (idx = 0; idx < result->net_count; ++idx) {
        lfd_free_net(&result->nets[idx]);
    }
    free(result->nets);
    for (idx = 0; idx < result->specialnet_count; ++idx) {
        lfd_free_net(&result->specialnets[idx]);
    }
    free(result->specialnets);
    lfd_zero_memory(result, sizeof(*result));
}

static int lfd_add_point(double** points_xy, size_t* count, size_t* capacity, double x, double y) {
    if (!lfd_ensure_capacity((void**)points_xy, sizeof(double) * 2, capacity, *count + 1)) {
        return 0;
    }
    (*points_xy)[(*count) * 2] = x;
    (*points_xy)[(*count) * 2 + 1] = y;
    *count += 1;
    return 1;
}

static int lfd_is_power_name(const char* name) {
    return (
        lfd_string_case_equals(name, "VDD") ||
        lfd_string_case_equals(name, "VDDPE") ||
        lfd_string_case_equals(name, "VPWR") ||
        lfd_string_case_equals(name, "POWER")
    );
}

static int lfd_is_ground_name(const char* name) {
    return (
        lfd_string_case_equals(name, "VSS") ||
        lfd_string_case_equals(name, "VSSPE") ||
        lfd_string_case_equals(name, "VGND") ||
        lfd_string_case_equals(name, "GND") ||
        lfd_string_case_equals(name, "GROUND")
    );
}

static int lfd_parse_component_line(const char* line, int units, LfdComponent* out, char** error_message) {
    LfdTokenList tokens;
    size_t idx;
    lfd_zero_memory(out, sizeof(*out));
    if (!lfd_tokenize(line, &tokens, error_message)) {
        return 0;
    }
    if (tokens.count < 3) {
        lfd_free_tokens(&tokens);
        return 0;
    }
    out->name = lfd_strdup_local(tokens.items[1]);
    out->cell_type = lfd_strdup_local(tokens.items[2]);
    out->orient = lfd_strdup_local("N");
    out->status = lfd_strdup_local("PLACED");
    if (out->name == NULL || out->cell_type == NULL || out->orient == NULL || out->status == NULL) {
        lfd_set_error(error_message, "component parse", "out of memory");
        lfd_free_component(out);
        lfd_free_tokens(&tokens);
        return 0;
    }
    for (idx = 0; idx < tokens.count; ++idx) {
        if ((lfd_string_equals(tokens.items[idx], "PLACED") || lfd_string_equals(tokens.items[idx], "FIXED")) &&
            idx + 5 < tokens.count &&
            lfd_string_equals(tokens.items[idx + 1], "(") &&
            lfd_string_equals(tokens.items[idx + 4], ")")) {
            lfd_replace_string(&out->status, tokens.items[idx]);
            out->x = strtod(tokens.items[idx + 2], NULL) / (double)units;
            out->y = strtod(tokens.items[idx + 3], NULL) / (double)units;
            lfd_replace_string(&out->orient, tokens.items[idx + 5]);
            break;
        }
    }
    lfd_free_tokens(&tokens);
    return 1;
}

static int lfd_parse_connections_from_tokens(const LfdTokenList* tokens, size_t start_idx, LfdConnectionVec* out, char** error_message) {
    size_t idx;
    for (idx = start_idx; idx + 3 < tokens->count; ++idx) {
        LfdConnection conn;
        if (!lfd_string_equals(tokens->items[idx], "(") || !lfd_string_equals(tokens->items[idx + 3], ")")) {
            continue;
        }
        lfd_zero_memory(&conn, sizeof(conn));
        conn.component = lfd_strdup_local(tokens->items[idx + 1]);
        conn.pin = lfd_strdup_local(tokens->items[idx + 2]);
        if (conn.component == NULL || conn.pin == NULL) {
            lfd_set_error(error_message, "net parse", "out of memory");
            lfd_free_connection(&conn);
            return 0;
        }
        if (!lfd_connection_vec_push(out, &conn)) {
            lfd_set_error(error_message, "net parse", "out of memory");
            lfd_free_connection(&conn);
            return 0;
        }
        idx += 3;
    }
    return 1;
}

static int lfd_is_route_keyword(const char* token) {
    return (
        lfd_string_case_equals(token, "ROUTED") ||
        lfd_string_case_equals(token, "NEW") ||
        lfd_string_equals(token, "+") ||
        lfd_string_case_equals(token, "WIDTH") ||
        lfd_string_case_equals(token, "MASK") ||
        lfd_string_case_equals(token, "SPACING") ||
        lfd_string_case_equals(token, "TAPER") ||
        lfd_string_case_equals(token, "TAPERRULE") ||
        lfd_string_case_equals(token, "OFFSET")
    );
}

static int lfd_parse_route_line(const char* line, int units, LfdRoutingSegment* out, char** error_message) {
    LfdTokenList tokens;
    size_t first_paren;
    size_t idx;
    double* points_xy;
    size_t point_count;
    size_t point_capacity;
    double prev_x;
    double prev_y;
    int have_prev_x;
    int have_prev_y;
    char* layer;
    double width;
    int has_width;

    lfd_zero_memory(out, sizeof(*out));
    if (!lfd_tokenize(line, &tokens, error_message)) {
        return 0;
    }

    first_paren = tokens.count;
    for (idx = 0; idx < tokens.count; ++idx) {
        if (lfd_string_equals(tokens.items[idx], "(")) {
            first_paren = idx;
            break;
        }
    }

    layer = NULL;
    width = 0.0;
    has_width = 0;
    for (idx = 0; idx < first_paren; ++idx) {
        char* endptr;
        if (lfd_is_route_keyword(tokens.items[idx])) {
            continue;
        }
        if (layer == NULL) {
            layer = lfd_strdup_local(tokens.items[idx]);
            if (layer == NULL) {
                lfd_set_error(error_message, "route parse", "out of memory");
                lfd_free_tokens(&tokens);
                return 0;
            }
            if (idx + 1 < first_paren) {
                width = strtod(tokens.items[idx + 1], &endptr);
                if (endptr != tokens.items[idx + 1] && *endptr == '\0') {
                    has_width = 1;
                    width /= (double)units;
                }
            }
            continue;
        }
        width = strtod(tokens.items[idx], &endptr);
        if (endptr != tokens.items[idx] && *endptr == '\0') {
            has_width = 1;
            width /= (double)units;
        }
    }
    for (idx = 0; idx + 1 < tokens.count; ++idx) {
        if (lfd_string_case_equals(tokens.items[idx], "WIDTH")) {
            char* endptr;
            width = strtod(tokens.items[idx + 1], &endptr);
            if (endptr != tokens.items[idx + 1] && *endptr == '\0') {
                has_width = 1;
                width /= (double)units;
                break;
            }
        }
    }

    points_xy = NULL;
    point_count = 0;
    point_capacity = 0;
    prev_x = 0.0;
    prev_y = 0.0;
    have_prev_x = 0;
    have_prev_y = 0;
    for (idx = 0; idx + 3 < tokens.count; ++idx) {
        double x_value;
        double y_value;
        if (!lfd_string_equals(tokens.items[idx], "(") || !lfd_string_equals(tokens.items[idx + 3], ")")) {
            continue;
        }
        if (lfd_string_equals(tokens.items[idx + 1], "*")) {
            if (!have_prev_x) {
                idx += 3;
                continue;
            }
            x_value = prev_x;
        } else {
            x_value = strtod(tokens.items[idx + 1], NULL) / (double)units;
        }
        if (lfd_string_equals(tokens.items[idx + 2], "*")) {
            if (!have_prev_y) {
                idx += 3;
                continue;
            }
            y_value = prev_y;
        } else {
            y_value = strtod(tokens.items[idx + 2], NULL) / (double)units;
        }
        if (!lfd_add_point(&points_xy, &point_count, &point_capacity, x_value, y_value)) {
            free(layer);
            free(points_xy);
            lfd_set_error(error_message, "route parse", "out of memory");
            lfd_free_tokens(&tokens);
            return 0;
        }
        prev_x = x_value;
        prev_y = y_value;
        have_prev_x = 1;
        have_prev_y = 1;
        idx += 3;
    }

    lfd_free_tokens(&tokens);
    if (layer == NULL || point_count < 2) {
        free(layer);
        free(points_xy);
        return 0;
    }
    out->layer = layer;
    out->points_xy = points_xy;
    out->point_count = point_count;
    out->width = width;
    out->has_width = has_width;
    return 1;
}

static int lfd_parse_net_start_line(const char* line, int units, int is_special, LfdNet* out, char** error_message) {
    LfdTokenList tokens;
    lfd_zero_memory(out, sizeof(*out));
    if (!lfd_tokenize(line, &tokens, error_message)) {
        return 0;
    }
    if (tokens.count < 2) {
        lfd_free_tokens(&tokens);
        return 0;
    }
    out->name = lfd_strdup_local(tokens.items[1]);
    out->use = lfd_strdup_local(is_special ? "POWER" : "SIGNAL");
    out->is_special = is_special;
    if (out->name == NULL || out->use == NULL) {
        lfd_set_error(error_message, "net parse", "out of memory");
        lfd_free_net(out);
        lfd_free_tokens(&tokens);
        return 0;
    }
    if (is_special && lfd_is_ground_name(out->name)) {
        lfd_replace_string(&out->use, "GROUND");
    } else if (is_special && lfd_is_power_name(out->name)) {
        lfd_replace_string(&out->use, "POWER");
    }
    {
        LfdConnectionVec connections;
        lfd_zero_memory(&connections, sizeof(connections));
        if (!lfd_parse_connections_from_tokens(&tokens, 2, &connections, error_message)) {
            lfd_free_net(out);
            lfd_free_tokens(&tokens);
            return 0;
        }
        out->connections = connections.items;
        out->connection_count = connections.count;
    }
    (void)units;
    lfd_free_tokens(&tokens);
    return 1;
}

static int lfd_parse_lef_line_rect(const char* line, double* coords) {
    return lfd_parse_double_list(line, coords, 4);
}

int lfd_parse_lef_abstracts(const char* file_path, LfdLefParseResult* out, char** error_message) {
    FILE* file;
    char* raw_line;
    size_t raw_capacity;
    ssize_t raw_len;
    int in_macro;
    int in_pin;
    int in_port;
    int in_obs;
    char* current_macro_name;
    char* current_pin_name;
    char* current_pin_use;
    char* current_layer;
    LfdMacro current_macro;
    size_t macro_capacity;
    LfdPinRectVec pin_rects;
    LfdObsRectVec obs_rects;

    lfd_zero_memory(out, sizeof(*out));
    if (error_message != NULL) {
        *error_message = NULL;
    }
    file = fopen(file_path, "r");
    if (file == NULL) {
        lfd_set_error(error_message, "Failed to open LEF file", file_path);
        return 0;
    }

    raw_line = NULL;
    raw_capacity = 0;
    in_macro = 0;
    in_pin = 0;
    in_port = 0;
    in_obs = 0;
    current_macro_name = NULL;
    current_pin_name = NULL;
    current_pin_use = lfd_strdup_local("SIGNAL");
    current_layer = NULL;
    lfd_zero_memory(&current_macro, sizeof(current_macro));
    macro_capacity = 0;
    lfd_zero_memory(&pin_rects, sizeof(pin_rects));
    lfd_zero_memory(&obs_rects, sizeof(obs_rects));

    while ((raw_len = getline(&raw_line, &raw_capacity, file)) != -1) {
        char* line;
        (void)raw_len;
        lfd_strip_hash_comment(raw_line);
        line = lfd_trim_inplace(raw_line);
        if (*line == '\0') {
            continue;
        }
        if (!in_macro) {
            if (lfd_starts_with(line, "MACRO ")) {
                char* name;
                line += 6;
                line = lfd_trim_inplace(line);
                lfd_strip_semicolon_inplace(line);
                name = lfd_strdup_local(line);
                if (name == NULL) {
                    lfd_set_error(error_message, "LEF parse", "out of memory");
                    goto fail;
                }
                current_macro_name = name;
                current_macro.name = lfd_strdup_local(line);
                if (current_macro.name == NULL) {
                    lfd_set_error(error_message, "LEF parse", "out of memory");
                    goto fail;
                }
                in_macro = 1;
                free(current_pin_name);
                current_pin_name = NULL;
                lfd_replace_string(&current_pin_use, "SIGNAL");
                free(current_layer);
                current_layer = NULL;
                pin_rects.count = 0;
                obs_rects.count = 0;
            }
            continue;
        }

        if (lfd_starts_with(line, "END ")) {
            char* end_name;
            line += 4;
            line = lfd_trim_inplace(line);
            lfd_strip_semicolon_inplace(line);
            end_name = line;
            if (in_pin && current_pin_name != NULL && lfd_string_equals(end_name, current_pin_name)) {
                in_pin = 0;
                in_port = 0;
                free(current_pin_name);
                current_pin_name = NULL;
                lfd_replace_string(&current_pin_use, "SIGNAL");
                free(current_layer);
                current_layer = NULL;
                continue;
            }
            if (current_macro_name != NULL && lfd_string_equals(end_name, current_macro_name)) {
                current_macro.pin_rects = pin_rects.items;
                current_macro.pin_rect_count = pin_rects.count;
                current_macro.obs_rects = obs_rects.items;
                current_macro.obs_rect_count = obs_rects.count;
                if (!lfd_macro_vec_push(out, &current_macro, &macro_capacity)) {
                    lfd_set_error(error_message, "LEF parse", "out of memory");
                    goto fail;
                }
                lfd_zero_memory(&current_macro, sizeof(current_macro));
                lfd_zero_memory(&pin_rects, sizeof(pin_rects));
                lfd_zero_memory(&obs_rects, sizeof(obs_rects));
                in_macro = 0;
                in_pin = 0;
                in_port = 0;
                in_obs = 0;
                free(current_macro_name);
                current_macro_name = NULL;
                free(current_pin_name);
                current_pin_name = NULL;
                lfd_replace_string(&current_pin_use, "SIGNAL");
                free(current_layer);
                current_layer = NULL;
                continue;
            }
        }

        if (lfd_string_equals(line, "END")) {
            if (in_port) {
                in_port = 0;
                free(current_layer);
                current_layer = NULL;
                continue;
            }
            if (in_obs) {
                in_obs = 0;
                free(current_layer);
                current_layer = NULL;
                continue;
            }
        }

        if (lfd_starts_with(line, "SIZE ")) {
            double values[2];
            if (lfd_parse_double_list(line, values, 2)) {
                current_macro.size_x = values[0];
                current_macro.size_y = values[1];
            }
            continue;
        }
        if (lfd_starts_with(line, "PIN ")) {
            line += 4;
            line = lfd_trim_inplace(line);
            lfd_strip_semicolon_inplace(line);
            free(current_pin_name);
            current_pin_name = lfd_strdup_local(line);
            if (current_pin_name == NULL) {
                lfd_set_error(error_message, "LEF parse", "out of memory");
                goto fail;
            }
            lfd_replace_string(&current_pin_use, "SIGNAL");
            in_pin = 1;
            in_port = 0;
            free(current_layer);
            current_layer = NULL;
            continue;
        }
        if (in_pin && lfd_starts_with(line, "USE ")) {
            line += 4;
            line = lfd_trim_inplace(line);
            lfd_strip_semicolon_inplace(line);
            lfd_replace_string(&current_pin_use, line);
            continue;
        }
        if (in_pin && lfd_string_equals(line, "PORT")) {
            in_port = 1;
            free(current_layer);
            current_layer = NULL;
            continue;
        }
        if (lfd_string_equals(line, "OBS")) {
            in_obs = 1;
            free(current_layer);
            current_layer = NULL;
            continue;
        }
        if ((in_port || in_obs) && lfd_starts_with(line, "LAYER ")) {
            line += 6;
            line = lfd_trim_inplace(line);
            lfd_strip_semicolon_inplace(line);
            free(current_layer);
            current_layer = lfd_strdup_local(line);
            if (current_layer == NULL) {
                lfd_set_error(error_message, "LEF parse", "out of memory");
                goto fail;
            }
            continue;
        }
        if ((in_port || in_obs) && current_layer != NULL && lfd_starts_with(line, "RECT ")) {
            double coords[4];
            if (lfd_parse_lef_line_rect(line, coords)) {
                if (in_port && in_pin && current_pin_name != NULL) {
                    LfdPinRect rect;
                    lfd_zero_memory(&rect, sizeof(rect));
                    rect.pin_name = lfd_strdup_local(current_pin_name);
                    rect.pin_use = lfd_strdup_local(current_pin_use != NULL ? current_pin_use : "SIGNAL");
                    rect.layer = lfd_strdup_local(current_layer);
                    rect.x0 = coords[0] < coords[2] ? coords[0] : coords[2];
                    rect.x1 = coords[0] > coords[2] ? coords[0] : coords[2];
                    rect.y0 = coords[1] < coords[3] ? coords[1] : coords[3];
                    rect.y1 = coords[1] > coords[3] ? coords[1] : coords[3];
                    if (rect.pin_name == NULL || rect.pin_use == NULL || rect.layer == NULL) {
                        lfd_set_error(error_message, "LEF parse", "out of memory");
                        lfd_free_pin_rect(&rect);
                        goto fail;
                    }
                    if (!lfd_pin_rect_vec_push(&pin_rects, &rect)) {
                        lfd_set_error(error_message, "LEF parse", "out of memory");
                        lfd_free_pin_rect(&rect);
                        goto fail;
                    }
                } else if (in_obs) {
                    LfdObsRect rect;
                    lfd_zero_memory(&rect, sizeof(rect));
                    rect.layer = lfd_strdup_local(current_layer);
                    rect.x0 = coords[0] < coords[2] ? coords[0] : coords[2];
                    rect.x1 = coords[0] > coords[2] ? coords[0] : coords[2];
                    rect.y0 = coords[1] < coords[3] ? coords[1] : coords[3];
                    rect.y1 = coords[1] > coords[3] ? coords[1] : coords[3];
                    if (rect.layer == NULL) {
                        lfd_set_error(error_message, "LEF parse", "out of memory");
                        lfd_free_obs_rect(&rect);
                        goto fail;
                    }
                    if (!lfd_obs_rect_vec_push(&obs_rects, &rect)) {
                        lfd_set_error(error_message, "LEF parse", "out of memory");
                        lfd_free_obs_rect(&rect);
                        goto fail;
                    }
                }
            }
        }
    }

    free(raw_line);
    fclose(file);
    free(current_macro_name);
    free(current_pin_name);
    free(current_pin_use);
    free(current_layer);
    return 1;

fail:
    free(raw_line);
    fclose(file);
    free(current_macro_name);
    free(current_pin_name);
    free(current_pin_use);
    free(current_layer);
    lfd_free_macro(&current_macro);
    {
        size_t idx;
        for (idx = 0; idx < pin_rects.count; ++idx) {
            lfd_free_pin_rect(&pin_rects.items[idx]);
        }
        free(pin_rects.items);
        for (idx = 0; idx < obs_rects.count; ++idx) {
            lfd_free_obs_rect(&obs_rects.items[idx]);
        }
        free(obs_rects.items);
    }
    lfd_free_lef_parse_result(out);
    return 0;
}

int lfd_parse_def_compact(const char* file_path, LfdDefParseResult* out, char** error_message) {
    FILE* file;
    char* raw_line;
    size_t raw_capacity;
    ssize_t raw_len;
    enum { SECTION_NONE, SECTION_COMPONENTS, SECTION_NETS, SECTION_SPECIALNETS } section;
    LfdComponentVec components;
    LfdNetVec nets;
    LfdNetVec specialnets;
    LfdNet current_net;
    int has_current_net;
    int current_net_is_special;

    lfd_zero_memory(out, sizeof(*out));
    if (error_message != NULL) {
        *error_message = NULL;
    }
    out->units = 2000;

    file = fopen(file_path, "r");
    if (file == NULL) {
        lfd_set_error(error_message, "Failed to open DEF file", file_path);
        return 0;
    }

    raw_line = NULL;
    raw_capacity = 0;
    section = SECTION_NONE;
    lfd_zero_memory(&components, sizeof(components));
    lfd_zero_memory(&nets, sizeof(nets));
    lfd_zero_memory(&specialnets, sizeof(specialnets));
    lfd_zero_memory(&current_net, sizeof(current_net));
    has_current_net = 0;
    current_net_is_special = 0;

    while ((raw_len = getline(&raw_line, &raw_capacity, file)) != -1) {
        char* line;
        (void)raw_len;
        lfd_strip_hash_comment(raw_line);
        line = lfd_trim_inplace(raw_line);
        if (*line == '\0') {
            continue;
        }

        if (lfd_starts_with(line, "DESIGN ")) {
            line += 7;
            line = lfd_trim_inplace(line);
            lfd_strip_semicolon_inplace(line);
            lfd_replace_string(&out->design_name, line);
            continue;
        }
        if (lfd_starts_with(line, "TECHNOLOGY ")) {
            line += 11;
            line = lfd_trim_inplace(line);
            lfd_strip_semicolon_inplace(line);
            lfd_replace_string(&out->tech_name, line);
            continue;
        }
        if (lfd_starts_with(line, "UNITS DISTANCE MICRONS")) {
            double unit_value;
            if (!lfd_parse_double_list(line, &unit_value, 1) || unit_value <= 0.0) {
                lfd_set_error(error_message, "DEF parse", "invalid UNITS DISTANCE MICRONS value");
                goto fail;
            }
            out->units = (int)unit_value;
            continue;
        }
        if (lfd_starts_with(line, "DIEAREA")) {
            double coords[4];
            if (out->units <= 0) {
                lfd_set_error(error_message, "DEF parse", "UNITS DISTANCE MICRONS must be positive before DIEAREA");
                goto fail;
            }
            if (lfd_parse_double_list(line, coords, 4)) {
                out->diearea[0] = coords[0] / (double)out->units;
                out->diearea[1] = coords[1] / (double)out->units;
                out->diearea[2] = coords[2] / (double)out->units;
                out->diearea[3] = coords[3] / (double)out->units;
            }
            continue;
        }
        if (lfd_starts_with(line, "COMPONENTS ")) {
            section = SECTION_COMPONENTS;
            continue;
        }
        if (lfd_string_equals(line, "END COMPONENTS")) {
            section = SECTION_NONE;
            continue;
        }
        if (lfd_starts_with(line, "NETS ")) {
            section = SECTION_NETS;
            continue;
        }
        if (lfd_string_equals(line, "END NETS")) {
            section = SECTION_NONE;
            continue;
        }
        if (lfd_starts_with(line, "SPECIALNETS ")) {
            section = SECTION_SPECIALNETS;
            continue;
        }
        if (lfd_string_equals(line, "END SPECIALNETS")) {
            section = SECTION_NONE;
            continue;
        }

        if (section == SECTION_COMPONENTS && lfd_starts_with(line, "- ")) {
            LfdComponent component;
            if (!lfd_parse_component_line(line, out->units, &component, error_message)) {
                goto fail;
            }
            if (component.name != NULL) {
                if (!lfd_component_vec_push(&components, &component)) {
                    lfd_free_component(&component);
                    lfd_set_error(error_message, "DEF parse", "out of memory");
                    goto fail;
                }
            }
            continue;
        }

        if ((section == SECTION_NETS || section == SECTION_SPECIALNETS) && lfd_starts_with(line, "- ")) {
            if (has_current_net) {
                if (current_net_is_special) {
                    if (!lfd_net_vec_push(&specialnets, &current_net)) {
                        lfd_set_error(error_message, "DEF parse", "out of memory");
                        goto fail;
                    }
                } else {
                    if (!lfd_net_vec_push(&nets, &current_net)) {
                        lfd_set_error(error_message, "DEF parse", "out of memory");
                        goto fail;
                    }
                }
                lfd_zero_memory(&current_net, sizeof(current_net));
                has_current_net = 0;
            }
            if (!lfd_parse_net_start_line(line, out->units, section == SECTION_SPECIALNETS, &current_net, error_message)) {
                goto fail;
            }
            has_current_net = 1;
            current_net_is_special = section == SECTION_SPECIALNETS;
            if (line[strlen(line) - 1] == ';') {
                if (current_net_is_special) {
                    if (!lfd_net_vec_push(&specialnets, &current_net)) {
                        lfd_set_error(error_message, "DEF parse", "out of memory");
                        goto fail;
                    }
                } else {
                    if (!lfd_net_vec_push(&nets, &current_net)) {
                        lfd_set_error(error_message, "DEF parse", "out of memory");
                        goto fail;
                    }
                }
                lfd_zero_memory(&current_net, sizeof(current_net));
                has_current_net = 0;
            }
            continue;
        }

        if ((section == SECTION_NETS || section == SECTION_SPECIALNETS) && has_current_net) {
            if (lfd_starts_with(line, "+ USE")) {
                char* value;
                value = line + 5;
                value = lfd_trim_inplace(value);
                lfd_strip_semicolon_inplace(value);
                lfd_replace_string(&current_net.use, value);
            } else if (lfd_starts_with(line, "+ ROUTED") || lfd_starts_with(line, "NEW ")) {
                LfdRoutingSegment route;
                if (!lfd_parse_route_line(line, out->units, &route, error_message)) {
                    goto fail;
                }
                if (route.layer != NULL) {
                    LfdRoutingVec routes;
                    routes.items = current_net.routing;
                    routes.count = current_net.routing_count;
                    routes.capacity = current_net.routing_count;
                    if (!lfd_routing_vec_push(&routes, &route)) {
                        lfd_set_error(error_message, "DEF parse", "out of memory");
                        lfd_free_routing_segment(&route);
                        goto fail;
                    }
                    current_net.routing = routes.items;
                    current_net.routing_count = routes.count;
                }
            }
            if (line[strlen(line) - 1] == ';') {
                if (current_net_is_special) {
                    if (!lfd_net_vec_push(&specialnets, &current_net)) {
                        lfd_set_error(error_message, "DEF parse", "out of memory");
                        goto fail;
                    }
                } else {
                    if (!lfd_net_vec_push(&nets, &current_net)) {
                        lfd_set_error(error_message, "DEF parse", "out of memory");
                        goto fail;
                    }
                }
                lfd_zero_memory(&current_net, sizeof(current_net));
                has_current_net = 0;
            }
        }
    }

    if (has_current_net) {
        if (current_net_is_special) {
            if (!lfd_net_vec_push(&specialnets, &current_net)) {
                lfd_set_error(error_message, "DEF parse", "out of memory");
                goto fail;
            }
        } else {
            if (!lfd_net_vec_push(&nets, &current_net)) {
                lfd_set_error(error_message, "DEF parse", "out of memory");
                goto fail;
            }
        }
        lfd_zero_memory(&current_net, sizeof(current_net));
        has_current_net = 0;
    }

    out->components = components.items;
    out->component_count = components.count;
    out->nets = nets.items;
    out->net_count = nets.count;
    out->specialnets = specialnets.items;
    out->specialnet_count = specialnets.count;

    free(raw_line);
    fclose(file);
    return 1;

fail:
    free(raw_line);
    fclose(file);
    if (has_current_net) {
        lfd_free_net(&current_net);
    }
    {
        size_t idx;
        for (idx = 0; idx < components.count; ++idx) {
            lfd_free_component(&components.items[idx]);
        }
        free(components.items);
        for (idx = 0; idx < nets.count; ++idx) {
            lfd_free_net(&nets.items[idx]);
        }
        free(nets.items);
        for (idx = 0; idx < specialnets.count; ++idx) {
            lfd_free_net(&specialnets.items[idx]);
        }
        free(specialnets.items);
    }
    lfd_free_def_parse_result(out);
    return 0;
}
