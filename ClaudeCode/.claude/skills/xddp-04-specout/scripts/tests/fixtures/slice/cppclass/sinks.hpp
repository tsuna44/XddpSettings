#include <exception>
#include <memory>
namespace app {
class sink;
using sink_ptr = std::shared_ptr<sink>;
class sink {
public:
    virtual ~sink() = default;
    virtual void log(int v) = 0;
    virtual void flush() = 0;
};
class base_sink : public sink {
public:
    void log(int v) override { sink_it_(v); }
    void flush() override { flush_(); }
protected:
    virtual void sink_it_(int v) = 0;
    virtual void flush_() = 0;
    int level_;
};
class file_sink : public base_sink {
public:
    file_sink(int n) : size_(n) {}
    void set(int size_) { this->size_ = size_; }
    void sink_it_(int v) override { size_ += v; }
    void flush_() override { size_ = 0; }
    int size_;
};
class rotating_sink : public file_sink {
public:
    void flush_() override { rotations_ = 1; }
    int rotations_;
};
class null_sink : public base_sink {
public:
    void sink_it_(int v) override { (void)v; }
    void flush_() override {}
};
class error_t : public std::exception {
public:
    void report(int code) { code_ = code; }
    int code_;
};
template <typename T> class crtp : public T {
public:
    void tick() { count_ = 1; }
    int count_;
};
class plain {
public:
    void helper();
    int value_;
};
struct attr_t {
    int extra;
};
inline void set_extra(attr_t *a, int v) { a->extra = v; }
class helper_t {
public:
    int size() const { return count_; }
    const char *name() const { return label_; }
    int count_;
    const char *label_;
};
struct src_loc {
    const char *name;
};
src_loc make_loc();
class holder {
public:
    file_sink *fs_;
    void run() { fs_->sink_it_(9); }
};
}
