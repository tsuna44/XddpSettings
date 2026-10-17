#pragma once
#include <functional>
#include <map>
#include <memory>
#include <string>
#include <utility>
#include <vector>
class Bar;
class Foo {
public:
    void f();
    void go();
    Foo *lock();
    int n_;
};
class Bar {
public:
    void f();
    void go();
};
class Baz {
public:
    Bar *bar();
    auto aut();
    Foo over(int v);
    Bar over(long v);
    template <class T> T tmpl();
};
using bar_ptr = std::shared_ptr<Bar>;
Bar *make_bar();
template <typename M> class Base {
protected:
    Bar *member_;
};
class Derived : public Base<int> {
public:
    void use();
};
class Holder {
public:
    std::vector<std::shared_ptr<Foo>> foos_;
    std::vector<bar_ptr> bars_;
    std::map<std::string, std::shared_ptr<Bar>> by_name_;
    std::vector<Foo> xs_;
    std::vector<Bar> ys_;
    std::vector<std::pair<Foo *, int>> pairs_;
    Foo s;
    void loops();
    void bind();
    void wr(int v);
};
