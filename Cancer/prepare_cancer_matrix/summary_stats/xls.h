// History leftover - Windows xls are replaced by files in directories.

#ifndef __XLS__
#define __XLS__

#include "read_data.h"
#include <fstream>

// Dummy sheet - simply a csv file


void xls_create(const char* path);
void xls_add_params(data_set_t& ds);

using namespace std;

class xls_sheet_t {
private:
	ofstream sheet;
	bool newLine = true;
public:
	xls_sheet_t(const char* name);
	~xls_sheet_t(void) {
		sheet.close();
	}

	void nl(void) {
		sheet << "\n";
		newLine = true;
	}

	void w(const char* value, const char* cmnt = 0) {
		if (! sheet.is_open()) {
			fprintf(stderr, "Error: Trying to write unopen file\n");
			throw "";
		}
		if (!newLine)
			sheet << ",";
		sheet << value;
		if (cmnt)
			sheet << " /*" << cmnt << "*/";
		newLine = false;
	}

	void w(std::string value, std::string cmnt = "NO_COMMENT") {
		if (cmnt == "NO_COMMENT") {
			w(value.c_str());
		}
		else {
			w(value.c_str(), cmnt.c_str());
		}
	}

	void w(double value, std::string cmnt = "NO_COMMENT") {
		if (!sheet.is_open()) {
			fprintf(stderr, "Error: Trying to write unopen file\n");
			throw "";
		}
		if (!newLine)
			sheet << ",";
		sheet << value;
		if (cmnt != "NO_COMMENT")
			sheet << " /*" << cmnt << "*/";
		newLine = false;
	}
};
#endif

