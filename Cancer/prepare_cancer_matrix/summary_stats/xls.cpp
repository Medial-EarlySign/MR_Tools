// History leftover - Windows xls are replaced by files in directories.

#include "read_data.h"
#include <string>

#include "xls.h"

#include <iostream>
#include <boost/filesystem.hpp>
#include <algorithm>

std::string g_book;// Replace Excel book with directory

void xls_create(const char *_path)
{
	g_book = string(_path);
	boost::filesystem::path p{ g_book };
	try {
		create_directory(p);
	}
	catch (...) {
		fprintf(stderr, "Cannot create directory %s\n", _path);
		throw "creating directory";
	}
}

void xls_add_params(data_set_t& ds)
{

	string file_name = g_book + "/Parameters";
	ofstream of(file_name);
	if (! of.is_open()) {
		fprintf(stderr, "Cannot open file %s for writing\n", file_name.c_str());
		throw "openning file";
	}

	of << "DataSet," << ds.source << "\n";
	for (params_t::iterator it = ds.params.begin(); it != ds.params.end(); it++)
		of << it->first << "," << it->second << "\n";
}

xls_sheet_t::xls_sheet_t(const char* name)
{
	if (g_book.empty()) {
		fprintf(stderr, "Error: Trying to add a file to undefined directory\n");
		throw "";
	}

	
	string file_name = g_book + "/" + name;
	std::replace(file_name.begin(), file_name.end(), ' ', '_');
	sheet.open(file_name, std::ofstream::out | std::ofstream::app);
	if (!sheet.is_open()) {
		fprintf(stderr, "Cannot open file %s for writing\n", file_name.c_str());
		throw "";
	}
}






