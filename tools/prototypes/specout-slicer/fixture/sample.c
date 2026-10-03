#define SET_FLAG(V, F) (V) |= (F)
int g_count;
static int helper_pure(int a) { return a * 2; }
void helper_writes_global(int a) { g_count = a; }
int ret_flow(int x) {
    int y = SEED + x;
    return y;
}
void local_only(int x) {
    int tmp = SEED;
    tmp++;
    (void)helper_pure(tmp);
}
void out_param(struct s *p) {
    p->v = SEED;
}
void global_write(void) {
    g_count = SEED;
}
void control_dep(int x) {
    if (x == SEED) helper_writes_global(1);
}
int early_return(int x) {
    if (x == SEED) return -1;
    return 0;
}
void macro_write(struct s *p) {
    SET_FLAG(p->flags, SEED);
}
void local_struct(void) {
    struct s v; v.x = SEED; use_nothing();
}
void static_state(void) {
    static int cnt; cnt += SEED;
}
void heap_ptr(struct tbl *t) {
    struct s *e = lookup(t); e->v = SEED;
}
int void_early(int x) {
    if (x == SEED)
        goto out;
    helper_writes_global(2);
out:
    return 0;
}
#define DERIVED (SEED + 1)
void flow_order(struct s *c) {
    if (c->argc == 3) {
        helper_pure(1);
    }
    modify(c, SEED);
    return;
}
void branch_exit(struct s *c) {
    if (c->argc == 3) {
        SET_FLAG(c->flags, SEED);
        return;
    } else if (c->argc > 3) {
        helper_writes_global(1);
        return;
    }
    helper_writes_global(c->argc);
}
#define CHECK_FLAG(V, F) ((V) & (F))
int check_only(struct s *p) {
    int r = 0;
    if (CHECK_FLAG(p->flags, SEED)) r = 1;
    return 0;
}
