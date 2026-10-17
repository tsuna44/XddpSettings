#include "e.hpp"
void Holder::loops() {
    for (auto &p : foos_) p->f();
    for (auto &b : bars_) b->f();
    for (auto &kv : by_name_) kv.second->f();
    for (auto &s : xs_) s.f();
    for (auto &s : ys_) s.f();
}
void exprs(Baz &baz, Foo *pf, std::vector<Foo> v, int i) {
    auto x = std::make_shared<Foo>(); x->f();
    auto y = new Bar(); y->f();
    Bar().f();
    baz.bar()->f();
    make_bar()->f();
    (*pf).f();
    v[i].f();
    baz.aut().f();
    baz.over(1).f();
    baz.tmpl<Foo>().f();
}
void Derived::use() { Base<int>::member_->f(); }
void novis() {
    { Foo q; q.f(); }
    q.go();
}
void lam() {
    Foo s;
    auto g = [&](Bar s) { s.f(); };
    s.go();
    try { g(Bar()); } catch (Bar &s) { s.go(); }
    if (Bar *s = make_bar()) { s->f(); }
    if (auto s = make_bar(); s) { s->go(); }
}
void Holder::bind() {
    auto [k, s] = std::make_pair(1, Foo());
    s.f();
    for (auto &[s, lvl] : pairs_) s->go();
}
void fnarg(Foo s) {
    auto g = [&] { std::function<void(Bar s)> h; s.f(); };
}
void cap(Foo s) {
    auto g = [w = s.lock()](Bar s) { s.go(); };
}
void lamx(Foo x) {
    auto x = [&] { auto [a, b] = std::make_pair(1, 2); return Bar(); }();
    x.go();
}
void shadow(Foo s) {
    s.f();
    { Bar s; s.f(); }
    s.go();
}
void Holder::wr(int v) {
    { Foo obj; obj.n_ = v; }
    { Foo obj; obj.n_ = v + 1; }
}
