#ifndef __ALGOMARKER___H_
#define __ALGOMARKER___H_

#include <vector>
#include <cassert>
#include <string>
#ifdef __linux__ 
#include <dlfcn.h>
#else
#include <windows.h>
#endif

#include "utils.h"



using namespace std;
#define AM_OK_RC									0
#define AM_TYPE_MEDIAL_INFRA					1

class AlgoMarker;

void* load_sym(void* lib_h, const char* sym_name, bool exit_on_fail = true)
{
	printf("Loading %s ... ", sym_name);
#ifdef __linux__ 
	void* ret = dlsym(lib_h, sym_name);
	if (ret == nullptr) {
		char * err = (char*)dlerror();
		printf("Failed: %s\n", err);
#else
	void* ret = GetProcAddress((HMODULE)lib_h, sym_name);
	if (ret == nullptr) {
		printf("Failed\n");
#endif
		if (exit_on_fail) {
			MLOG(true, "Failed loading shared library\n");
			return NULL;
		}
	}
	printf("OK\n");
	return ret;
}

class DynAM {
public:
	typedef int(*t_AM_API_Create)(int am_type, AlgoMarker **new_am);
	typedef int(*t_AM_API_Load)(AlgoMarker * pAlgoMarker, const char *config_fname);
	typedef int(*t_AM_API_AdditionalLoad)(AlgoMarker * pAlgoMarker, const int load_type, const char *load);
	typedef int(*t_AM_API_ClearData)(AlgoMarker * pAlgoMarker);
	typedef int(*t_AM_API_AddDataByType)(AlgoMarker * pAlgoMarker, const char *data, char **messages);
	typedef int(*t_AM_API_CalculateByType)(AlgoMarker *pAlgoMarker, int CalcType, char *request, char **responses);
	typedef void(*t_AM_API_DisposeAlgoMarker)(AlgoMarker*);
	typedef void(*t_AM_API_Dispose)(char *);
	typedef void(*t_AM_API_Discovery)(AlgoMarker *pAlgoMarker, char **resp);
	typedef void(*t_AM_API_DebugRepMemory)(AlgoMarker *pAlgoMarker, char **resp);
	void *addr_AM_API_Create = nullptr;
	void *addr_AM_API_Load = nullptr;
	void *addr_AM_API_AdditionalLoad = nullptr;
	void *addr_AM_API_ClearData = nullptr;
	void *addr_AM_API_AddDataByType = nullptr;
	void *addr_AM_API_CalculateByType = nullptr;
	void *addr_AM_API_DisposeAlgoMarker = nullptr;
	void *addr_AM_API_Dispose = nullptr;
	void *addr_AM_API_Discovery = nullptr;
	void *addr_AM_API_DebugRepMemory = nullptr;
	// returns index in sos
	static int load(const char * am_fname) {
        printf("Loading %s ... ", am_fname);
#ifdef __linux__ 
        void* lib_handle = dlopen(am_fname, RTLD_NOW); //RTLD_LAZY
#else
		void* lib_handle = (void*)LoadLibrary(am_fname);
#endif
        if (lib_handle == NULL) {
#ifdef __linux__ 
            char * err = (char*)dlerror();
            if (err) printf("%s\n", err);
#else
			printf("Failed loading %s\n", am_fname);
#endif
            return -1;
        }
        sos.push_back(DynAM());
        so = &sos.back();
        printf("OK\n");
        so->addr_AM_API_Create = load_sym(lib_handle, "AM_API_Create");
        so->addr_AM_API_Load = load_sym(lib_handle, "AM_API_Load");
        so->addr_AM_API_AdditionalLoad = load_sym(lib_handle, "AM_API_AdditionalLoad");
        so->addr_AM_API_ClearData = load_sym(lib_handle, "AM_API_ClearData");
        so->addr_AM_API_AddDataByType = load_sym(lib_handle, "AM_API_AddDataByType");
        so->addr_AM_API_CalculateByType = load_sym(lib_handle, "AM_API_CalculateByType");
        so->addr_AM_API_DisposeAlgoMarker = load_sym(lib_handle, "AM_API_DisposeAlgoMarker");
        so->addr_AM_API_Dispose = load_sym(lib_handle, "AM_API_Dispose");
        so->addr_AM_API_Discovery = load_sym(lib_handle, "AM_API_Discovery", false);
		so->addr_AM_API_DebugRepMemory = load_sym(lib_handle, "AM_API_DebugRepMemory", false);
        return (int)sos.size() - 1;
    }
	static DynAM* so;
	static std::vector<DynAM> sos;
	static void set_so_id(int id) { assert(id >= 0 && id < (int)sos.size()); so = &sos[id]; };

	static int AM_API_ClearData(AlgoMarker * pAlgoMarker) {
        return (*((DynAM::t_AM_API_ClearData)DynAM::so->addr_AM_API_ClearData))
		(pAlgoMarker);
    }
	static void AM_API_DisposeAlgoMarker(AlgoMarker * pAlgoMarker) {
        (*((DynAM::t_AM_API_DisposeAlgoMarker)DynAM::so->addr_AM_API_DisposeAlgoMarker))
		(pAlgoMarker);
    }
	static void AM_API_Dispose(char *data) {
        (*((DynAM::t_AM_API_Dispose)DynAM::so->addr_AM_API_Dispose))
		(data);
    }
	static int AM_API_Create(int am_type, AlgoMarker **new_am) {
        return (*((DynAM::t_AM_API_Create)DynAM::so->addr_AM_API_Create))
		(am_type, new_am);
    }
	static int AM_API_Load(AlgoMarker * pAlgoMarker, const char *config_fname) {
        if (DynAM::so->addr_AM_API_Load == NULL)
		    printf("AM_API_Load is NULL\n");
	    else
		    printf("running AM_API_Load\n");
	    return (*((DynAM::t_AM_API_Load)DynAM::so->addr_AM_API_Load))
		    (pAlgoMarker, config_fname);
    }
	static int AM_API_AdditionalLoad(AlgoMarker * pAlgoMarker, const int load_type, const char *load) {
        return (*((DynAM::t_AM_API_AdditionalLoad)DynAM::so->addr_AM_API_AdditionalLoad))
		    (pAlgoMarker, load_type, load);
    }
	static int AM_API_AddDataByType(AlgoMarker * pAlgoMarker, const char *data, char **messages) {
        return (*((DynAM::t_AM_API_AddDataByType)DynAM::so->addr_AM_API_AddDataByType))
		(pAlgoMarker, data, messages);
    }
	static int AM_API_CalculateByType(AlgoMarker *pAlgoMarker, int CalcType, char *request, char **responses) {
        return (*((DynAM::t_AM_API_CalculateByType)DynAM::so->addr_AM_API_CalculateByType))
		(pAlgoMarker, CalcType, request, responses);
    }
	static void AM_API_Discovery(AlgoMarker *pAlgoMarker, char **resp) {
        if (DynAM::so->addr_AM_API_Load == NULL) {
		    printf("AM_API_Discovery is NULL\n");
		    return;
	    }
	    return (*((DynAM::t_AM_API_Discovery)DynAM::so->addr_AM_API_Discovery))
		    (pAlgoMarker, resp);
    }

	static void AM_API_DebugRepMemory(AlgoMarker *pAlgoMarker, char **resp) {
        if (DynAM::so->addr_AM_API_Load == NULL) {
		    printf("AM_API_Discovery is NULL\n");
		    return;
	    }
	    return (*((DynAM::t_AM_API_DebugRepMemory)DynAM::so->addr_AM_API_DebugRepMemory))
		    (pAlgoMarker, resp);
    }

	static bool initialized() { return (sos.size() > 0); }
};

DynAM* DynAM::so = nullptr;
std::vector<DynAM> DynAM::sos;

void load_library(const char * library_path) {
	if (DynAM::load(library_path) < 0)
		printf("Error\n");
}

void create_api_interface(AlgoMarker *&test_am) {
	if (DynAM::AM_API_Create((int)AM_TYPE_MEDIAL_INFRA, &test_am) != AM_OK_RC) {
		MLOG(true, "ERROR: Failed creating test algomarker\n");
	}
}

void initialize_algomarker(const char *amconfig, AlgoMarker *&test_am)
{
	// Load
	printf("Loading AM\n");
	int rc = DynAM::AM_API_Load(test_am, amconfig);
	printf("Loaded\n");
	if (rc != AM_OK_RC) {
		printf("ERROR: Failed loading algomarker %s ERR_CODE: %d\n", amconfig, rc);
	}
	fflush(stdout);
}

string load_data( AlgoMarker *am, const string &in_jsons, int &load_status) {
	DynAM::AM_API_ClearData(am);
    
	printf("read %zu characters from input json\n", in_jsons.length());
    char *out_messages;
    string msgs;
	load_status = DynAM::AM_API_AddDataByType(am, in_jsons.c_str(), &out_messages);
	if (out_messages != NULL) {
		msgs = string(out_messages); //New line for each message:
		printf("AddDataByType has messages:\n");
		printf("%s\n", msgs.c_str());
	}
	DynAM::AM_API_Dispose(out_messages);
	if (load_status != AM_OK_RC)
		printf("Error code returned from calling AddDataByType: %d\n", load_status);
    return msgs;
}
#endif