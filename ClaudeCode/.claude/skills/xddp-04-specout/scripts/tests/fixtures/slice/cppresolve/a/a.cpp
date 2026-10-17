#include "a.hpp"
#include <unistd.h>
using namespace level;
void logger::flush() {
    lvl_ = level::critical;
    lvl_ = static_cast<int>(async_msg_type::flush);
    lvl_ = fmt_lib::format("x");
    ::close(lvl_);
    logger o;
    std::swap(lvl_, o.lvl_);
    level::level_enum e = level::trace;
    (void)e;
    lvl_ = util::cfg::flush();
    yy::flush();
    critical("m");
}
template <typename T> void tq() { T::flush(); }
