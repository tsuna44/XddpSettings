class Box {
public:
    ~Box();
    Box& operator+=(int v);
    int size() const;
};
Box::~Box() {
    count_ = SEED;
}
Box& Box::operator+=(int v) {
    total_ = v + SEED;
    return *this;
}
int Box::size() const {
    return SEED;
}
template <typename T>
T pick(T a) {
    return a + SEED;
}
