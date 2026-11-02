#include "types.h"
#include <stdio.h>
#include <string.h>

void to_msg(const S *s, M *m)
{
    m->a = s->a;
    m->b = s->b;
    m->c = s->c;
    m->d = s->d;
}

void relay(const M *m, M *m2, unsigned char *buf)
{
    *m2 = *m;
    memcpy(buf, m, sizeof(M));
}

void dump(const M *m2, FILE *fp)
{
    fwrite(&m2->a, sizeof m2->a, 1, fp);
    fwrite(&m2->b, sizeof m2->b, 1, fp);
    fwrite(&m2->c, sizeof m2->c, 1, fp);
    fwrite(&m2->d, sizeof m2->d, 1, fp);
}

int only_one(const S *s)
{
    return s->a + 1;
}

void x_dump(const struct X *x, FILE *fp)
{
    fprintf(fp, "%d %d %d %d\n", x->a, x->b, x->c, x->d);
}
