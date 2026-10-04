#include "SEED.h"
/* SEED in a block comment */
static int proto_fn(int SEED);
int typed_proto(struct SEED *p);
#define WRAP(x) call_it(SEED, x)
int g_val = SEED;
static int
multi_line_head(int a,
                int b)
{
    // SEED only in a line comment
    const char *s = "SEED in a string";
    if (a == SEED)
        b++;
    return SEED;
}
int with_label(int x) {
    goto SEED;
SEED:
    return x;
}
int head_hit(int SEED) {
    return 0;
}
struct st { int SEED; };
