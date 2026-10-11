#define foo(x) ((x) + 1)
int (foo)(int x) { return x; }
int use_foo(void) { return (foo)(3); }
