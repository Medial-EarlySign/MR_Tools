#ifndef __UTILS____H_
#define __UTILS____H_
#include <string>
using namespace std;

string get_git_version();
void MLOG(bool throw_exp, const char *fmt, ...);
#endif