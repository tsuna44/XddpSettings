#include "macros.h"
#ifndef MY_FEATURE
#include "other.h"
#endif
#if defined(MY_FEATURE) && \
    defined(MACROS_H)
int feature_on(void);
#endif

MY_NS_BEGIN
namespace sinks {

class base_sink {
public:
    VIRTUAL void flush_();
    MAYBE_VIRTUAL void log_(int v);
};

MY_API int g_level = 0;

MY_INLINE void base_sink::flush_() {
    g_level = 1;
}

template <typename M>
MY_EXPORT void holder<M>::flush_all() {
    g_level = 2;
}

MY_ALIAS void a::b::wrapper::run() {
    g_level = 3;
}

ALL_STATIC int s_all(void) { return 1; }
SOME_STATIC int s_some(void) { return 2; }

// MY_INLINE is used in comments only
/*
 MY_INLINE in a block comment
*/
MY_INLINE int also(int x) { return x; } /* MY_INLINE */
const char *msg = "MY_INLINE";

} // namespace sinks
MY_NS_END

MY_NESTED_BEGIN
MY_NODISCARD int nested_fn() { return 1; }
MY_NESTED_END
