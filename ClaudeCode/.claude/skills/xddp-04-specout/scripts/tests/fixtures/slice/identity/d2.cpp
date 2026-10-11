namespace { int count; }
struct X { static int sm() { return SEED; } int size(); void set(); void touch(); void stamp(); int x_; };
static int size;
int X::size() { return SEED; }
void X::set() { x_ = SEED; }
void X::touch() { this->x_ = 1; }
void X::stamp() { last_secs_ = SEED; }
int use_size(X &x) { return x.size(); }
void bump(void) { count++; }
int opt(int n = g_limit);
