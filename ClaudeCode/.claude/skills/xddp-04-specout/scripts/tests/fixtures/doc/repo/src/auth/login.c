#include <stdio.h>

int login_check(const char *user) {
    int rc = session_start(user);
    return rc;
}

int login_other(void) {
    return 0;
}
