#pragma once
class sink {
public:
    void flush();
    void log(int v);
    void helper() const;
};
void helper();
namespace detail {
inline void log(int v) { (void)v; }
void f();
}
