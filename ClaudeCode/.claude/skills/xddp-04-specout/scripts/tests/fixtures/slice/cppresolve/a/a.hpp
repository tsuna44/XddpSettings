#pragma once
#include <utility>
namespace level {
enum level_enum { trace, critical };
}
enum class async_msg_type { log, flush, terminate };
namespace fmt_impl {
inline int format(const char *s) { return s != nullptr; }
}
namespace fmt_lib = fmt_impl;
namespace util {
class cfg {
public:
    static int flush();
};
}
namespace cfg {
inline int reload() { return 0; }
}
namespace yy {
inline void flush() {}
}
class logger {
public:
    void flush();
    void swap(logger &o);
    int format(const char *s);
    int level() const;
    void close();
    void critical(const char *m);
    int lvl_;
};
