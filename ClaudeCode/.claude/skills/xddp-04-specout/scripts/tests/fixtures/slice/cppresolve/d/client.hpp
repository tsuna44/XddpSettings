#pragma once
namespace net {
class base {
public:
    virtual void close();
    void reset();
};
#ifdef _WIN32
class client : public base {
public:
    void close() override;
    void send(int v);
    void win_only();
    int fd_;
};
#else
class client {
public:
    void close();
    void send(int v);
    long fd_;
};
#endif
}
