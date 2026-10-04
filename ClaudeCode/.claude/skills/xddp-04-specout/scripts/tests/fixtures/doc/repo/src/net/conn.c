int conn_open(int fd) {
    return login_check("x") + shared(fd);
}
