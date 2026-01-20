#include "utils.h"
#include <boost/algorithm/string.hpp>
#include <iostream>
#include <fstream>
#include <stdarg.h>
#include <getopt.h>

#ifndef GIT_HEAD_VERSION
#define GIT_HEAD_VERSION "please define GIT_HEAD_VERSION in compilation to set version"
#endif

using namespace std;

template<class ContainerType> string get_list(const ContainerType &ls, const string &delimeter) {
	string res = "";
	for (auto it = ls.begin(); it != ls.end(); ++it)
		if (it == ls.begin())
			res += *it;
		else
			res += delimeter + *it;
	return res;
}

string get_git_version() {
    return GIT_HEAD_VERSION;
}

void MLOG(bool throw_exp, const char *fmt, ...) {
    char buff[5000];
    va_list args;
    
    va_start(args, fmt);
	vsnprintf(buff, sizeof(buff), fmt, args);
	va_end(args);

    printf("%s", buff);
	fflush(stdout);
    if (throw_exp)
        throw std::runtime_error(buff);
}