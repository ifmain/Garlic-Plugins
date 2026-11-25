#include "garlic.h"

int32_t route_transport(int32_t kind, int32_t reserved, int32_t flags) {
    if (reserved || flags) return GARLIC_CONTINUE;
    return kind >= GARLIC_HTTP && kind <= GARLIC_SSH ? kind : GARLIC_CONTINUE;
}

/* Try an explicitly configured additional connection first. On a retry prefer
   the ordinary VPN pool. Garlic handles authentication and socket lifetime. */
int32_t route_next(int32_t primary, int32_t additional, int32_t attempt) {
    if (attempt == 0 && additional) return GARLIC_ADDITIONAL;
    if (primary) return GARLIC_PRIMARY;
    if (additional) return GARLIC_ADDITIONAL;
    return GARLIC_CONTINUE;
}
