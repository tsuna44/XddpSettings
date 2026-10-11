#include "lib.h"
int g_noext_b;
int g_twice;
void b_writer(int v) { g_noext_b = v; }
static void dup(void) { b_g = 1; }
static int s_count;
void b_uses(void) { s_count = 1; }
void shadow_field(void) { struct st server; server.dirty = 1; }
typedef int (*cb_t)(int);
cb_t fp_var;
