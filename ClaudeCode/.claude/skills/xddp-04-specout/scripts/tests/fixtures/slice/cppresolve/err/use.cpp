#include "good.hpp"
void free_decl();
void use_err() { free_decl(); }
void ok() { ns1::run(); Solo::run(); }
void in_err() { (ns1::run(), ; }
void in_err2() { (Solo::run(), ; }
