#include "lib.h"
#define LOOP_VARS int node, nnode
#ifndef MIN
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#endif
#define MIN2 (SEED + 2)
#define LOCALMAC (SEED + 3)
static int s_count;
int g_noext;
int g_ext;
int g_twice;
static int fw(void);
static char *fw2(void);
int fw(void) { return SEED; }
char *fw2(void) { return 0; }
static void s_writer(int v) { s_count = v; }
static int s_ret(void) { return SEED; }
static void dup(void) { a_g = 1; }
static void only_static(void) { o_g = 1; }
#define CALL_DUP() dup()
void bgp_clear(int v) {
    LOOP_VARS;
    nnode = SEED;
}
void writes_s_count(void) { s_count = SEED; }
void writes_g_noext(void) { g_noext = SEED; }
void writes_g_ext(void) { g_ext = SEED; }
void writes_h_static(void) { h_static_var = SEED; }
void calls_s_writer(void) { s_writer(SEED); }
void calls_b_writer(void) { b_writer(SEED); }
void call_dup(int x) { if (x == SEED) dup(); }
void via_macro(int x) { if (x == SEED) CALL_DUP(); }
void block_extern(void) { extern int g_blk; g_blk = SEED; }
void reads_blk(void) { extern int g_blk; use(g_blk); }
#ifdef FEATURE
int g_init2 = SEED;
#endif
static int cnt = 0;
void min_user(int x) { use(MIN(x, 1)); }
void reads_twice(void) { use(g_twice); }
struct st { int g_v; };
int g_v;
void member_arrow(struct st *p) { p->g_v = 1; }
struct st init_st = { .g_v = 1 };
void shadow(void) { int g_v = 0; use(g_v); }
void reads_gv(void) { use(g_v); }
static struct st srv;
void writes_srv(void) { srv.dirty = 1; }
