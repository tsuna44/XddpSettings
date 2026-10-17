#pragma once
#define NS real
#define ns_low lowreal
namespace a {
class X {
public:
    virtual void foo();
    int m_;
};
class Y : public X {
public:
    void foo() override;
};
class H {
public:
    X *px;
};
class Only {
public:
    void go();
};
}
namespace b {
class X {
public:
    void foo();
};
}
class X {
public:
    void foo();
};
namespace outer {
namespace inner {
class X {
public:
    void foo();
};
}
}
namespace NS {
class W {
public:
    void go();
};
}
namespace ns_low {
class W {
public:
    void go();
};
}
