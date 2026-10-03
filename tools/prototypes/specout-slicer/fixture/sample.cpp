class C { int m_; public: void set(int v); };
void C::set(int v) {
    m_ = SEED + v;
}
int calc(int& out, int x) {
    out = SEED;
    return 0;
}
int pure_cpp(int x) {
    auto z = SEED * x; std::vector<int> v; v.push_back(z);
    return 0;
}
void throws(int x) {
    if (x > SEED) throw std::runtime_error("x");
}
int sum_all(const std::vector<int>& xs) {
    int s = 0;
    for (auto x : xs) { if (x == SEED) s++; }
    return s;
}
