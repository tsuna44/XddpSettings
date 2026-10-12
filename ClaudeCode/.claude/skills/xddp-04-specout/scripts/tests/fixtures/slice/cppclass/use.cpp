#include "sinks.hpp"
namespace app {
void plain::helper() { value_ = 2; }
namespace detail {
int g_state;
}
void detail_touch(int v);
void use_sinks(file_sink &fs, null_sink *ns, sink_ptr sp, base_sink *bs, plain &pl) {
    fs.sink_it_(1);
    ns->sink_it_(2);
    sp->log(3);
    bs->sink_it_(4);
    pl.helper();
    auto a = make_sink();
    a->sink_it_(5);
}
using text_t = std::string;
void use_names(const char *name, text_t t, std::vector<int> v, helper_t &h) {
    int size = 0;
    size = t.size() + v.size();
    h.size();
    const char *p = make_loc().name;
    (void)name; (void)p;
}
template <typename T> void tsize(T &t) { t.size(); }
void call_free() {
    helper();
}
}
void detail::compute(int v) { g_state = v; }
