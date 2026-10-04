typedef int (*cb_t)(int);
int g_init = SEED;
#define DOUBLE_SEED (SEED * 2)
int dispatch(cb_t cb, int x) {
    int v = x + SEED;
    return cb(v);
}
struct ops { int (*run)(int); };
int via_struct(struct ops *o) {
    return o->run(SEED);
}
void side_effect_fn(int a, struct s *p) {
    log_it(a);
}
void use_key(struct s *p) {
    int k = KEY;
    side_effect_fn(k, p);
}
int seed_fn(int a) {
    g_counter = a;
    return a;
}
int g_counter;
