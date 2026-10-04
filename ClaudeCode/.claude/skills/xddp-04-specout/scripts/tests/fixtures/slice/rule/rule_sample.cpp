namespace ns {
class Widget {
public:
    Widget(int v) : value_(v) { init(SEED); }
    ~Widget() { release(SEED); }
    bool operator==(const Widget& o) const { return o.value_ == SEED; }
    int get() const { return SEED; }
    int value_;
};
int Widget::compute(int x) {
    auto f = [&](int y) { return y + SEED; };
    return f(x);
}
template <typename T>
T twice(T v) {
    return v * SEED;
}
}  // namespace ns
Widget::Widget(const Widget& o) : value_(o.value_) {
    use(SEED);
}
