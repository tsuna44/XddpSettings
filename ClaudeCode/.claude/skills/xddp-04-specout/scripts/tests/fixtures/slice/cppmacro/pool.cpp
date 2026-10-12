EXT_NS_BEGIN
namespace details {
int g_counter = 0;
EXT_INLINE pool::pool(int q_max_items,
                       int threads_n)
    : q_(q_max_items) {
    g_total = 1;
}

} // namespace details
EXT_NS_END
