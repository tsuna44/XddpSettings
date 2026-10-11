#ifndef LIB_H
#define LIB_H
#ifdef __cplusplus
extern "C" {
#endif
extern int g_ext;
extern int a_g, b_g, c_g, o_g;
extern struct master *bm;
#ifdef __cplusplus
}
#endif
static int h_static_var;
static inline int h_inline_b(int x) { return x + 1; }
static inline int h_inline_a(int x) { return h_inline_b(x); }
static inline int h_ret(void) { return SEED; }
int proto_with_param(int g_v);
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define MIN2 1
#endif
