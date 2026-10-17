#include "b.hpp"
void run() { helper(); }
void detail::f() { helper(); }
void sink::flush() { helper(); }
void (*hp)() = helper;
template <typename F> void make() { F::template create<int>(); }
template <typename T> void tbar() { bar<int>(); }
void tobj(sink &s) { s.template flush<int>(); }
