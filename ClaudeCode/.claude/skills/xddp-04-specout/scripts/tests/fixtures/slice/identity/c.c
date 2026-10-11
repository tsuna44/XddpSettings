#include "lib.h"
void call_dup_c(int x) { if (x == SEED) dup(); }
void call_only_static(int x) { if (x == SEED) only_static(); }
void call_fp(int x) { fp_var(SEED); }
