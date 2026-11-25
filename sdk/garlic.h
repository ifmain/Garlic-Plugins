#ifndef GARLIC_GPF_H
#define GARLIC_GPF_H
#include <stdint.h>

/* One capability per package. Route selection is evaluated before each open attempt. */
enum garlic_route { GARLIC_CONTINUE, GARLIC_PRIMARY, GARLIC_ADDITIONAL };
int32_t route_next(int32_t primary_available, int32_t additional_available, int32_t attempt);

/* Optional host dialers for user-configured peers. No socket handles or credentials enter Wasm. */
enum garlic_transport { GARLIC_HTTP=1, GARLIC_HTTPS, GARLIC_SOCKS4, GARLIC_SOCKS5, GARLIC_SSH };
int32_t route_transport(int32_t kind, int32_t reserved, int32_t flags);

/* Logical viewport: 320 x 240. Colors are 0xRRGGBB. Coordinates are signed. */
typedef struct { int32_t x, y, width, height, rgb; } GarlicRect;
typedef struct { uint32_t count; GarlicRect rectangles[128]; } GarlicFrame;
GarlicFrame *ui_frame(int32_t x, int32_t y, int32_t pressed, int32_t elapsed_ms);
#endif
