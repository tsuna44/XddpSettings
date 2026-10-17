#include "c.hpp"
namespace a {
void use_a(X &x) { x.foo(); }
}
namespace b {
void use_b(X &x) { x.foo(); }
}
void use_q(a::X &x, b::X &y) { x.foo(); y.foo(); }
void use_g(X &x) { x.foo(); }
void use_h(a::H &h) { h.px->foo(); }
void use_y(a::Y &y) { y.foo(); }
void use_w(real::W &w, lowreal::W &v) { w.go(); v.go(); }
void a::X::foo() { m_ = 1; }
namespace b {
void X::foo() {}
}
