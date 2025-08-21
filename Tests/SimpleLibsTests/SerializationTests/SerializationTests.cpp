#include <Logger/Logger/Logger.h>
#include <MedProcessTools/MedProcessTools/SerializableObject.h>
#include <MedProcessTools/MedProcessTools/MedSamples.h>
#include <MedUtils/MedUtils/MedUtils.h>
#include "Catch-master/single_include/catch.hpp"
#define LOCAL_SECTION LOG_CONVERT
#define LOCAL_LEVEL	LOG_DEF_LEVEL

//=============================================================================
int serialize_test1(int n_samples, int n_preds)
{
	vector<MedSample> vms(n_samples);

	for (int i=0; i<n_samples; i++) {
		vms[i].id = i;
		vms[i].outcome = (float)i+2;
		vms[i].outcomeTime = 2000+i*10;
		vms[i].time = 1000 + i*5;
		vms[i].prediction.resize(n_preds);
		for (int j=0; j<n_preds; j++)
			vms[i].prediction[j] = rand_1();
	}

	string pref = "MedSamples Orig (" + to_string(n_samples) + ")";
	for (int i=0; i<n_samples; i++) vms[i].print(pref + "[" + to_string(i) + "]");

	vector<unsigned char> blob;
	size_t size = MedSerialize::get_size(vms);
	blob.resize(size);
	size_t serialize_size = MedSerialize::serialize(&blob[0], vms);

	vector<MedSample> dvms;
	size_t deserialize_size = MedSerialize::deserialize(&blob[0], dvms);

	MLOG("size %d serialize_size %d deserialize_size %d\n", size, serialize_size, deserialize_size);

	n_samples = (int)dvms.size();
	pref = "MedSamples Deserailized (" + to_string(n_samples) + ")";
	for (int i=0; i<n_samples; i++) dvms[i].print(pref + "[" + to_string(i) + "]");

	return 0;

}

//=============================================================================
int serialize_test2()
{
	vector<string> vms ={ "This ", "is ", "a ", "test ", "for ", "vector<string>" };

	vector<unsigned char> blob;
	size_t size = MedSerialize::get_size(vms);
	blob.resize(size);
	size_t serialize_size = MedSerialize::serialize(&blob[0], vms);

	vector<string> dvms;
	size_t deserialize_size = MedSerialize::deserialize(&blob[0], dvms);

	MLOG("size %d serialize_size %d deserialize_size %d\n", size, serialize_size, deserialize_size);

	int n_samples = (int)dvms.size();
	for (int i=0; i<n_samples; i++) MLOG("%s", dvms[i].c_str());
	MLOG("\n");

	return 0;

}

//=============================================================================
int serialize_test3()
{
	vector<int> vms ={3,1,4,1,5 };

	vector<unsigned char> blob;
	size_t size = MedSerialize::get_size(vms);
	blob.resize(size);
	size_t serialize_size = MedSerialize::serialize(&blob[0], vms);

	vector<int> dvms;
	size_t deserialize_size = MedSerialize::deserialize(&blob[0], dvms);

	MLOG("size %d serialize_size %d deserialize_size %d\n", size, serialize_size, deserialize_size);

	int n_samples = (int)dvms.size();
	for (int i=0; i<n_samples; i++) MLOG("%d ", dvms[i]);
	MLOG("\n");

	return 0;

}

//=============================================================================
int serialize_test4(int nrows, int nvec, int len_vecs)
{
	map<string,vector<vector<float>>> my_map, new_map;

	for (int i=0; i<nrows; i++) {
		string name = "ROW_"+to_string(i);
		vector<vector<float>> vecs;
		vecs.resize(nvec);
		for (int j=0; j<nvec; j++) {
			for (int k=0; k<len_vecs; k++)
				vecs[j].push_back((float)100*j+(float)k+rand_1());
		}

		MLOG("before i %d %s vecs.size %d vecs[0].size %d\n", i, name.c_str(), vecs.size(), vecs[0].size());
		my_map[name] = vecs;
	}

	vector<unsigned char> blob;
	size_t size = MedSerialize::get_size(my_map);
	blob.resize(size);
	size_t serialize_size = MedSerialize::serialize(&blob[0], my_map);

	size_t deserialize_size = MedSerialize::deserialize(&blob[0], new_map);

	MLOG("size %d serialize_size %d deserialize_size %d\n", size, serialize_size, deserialize_size);

	int n_samples = (int)new_map.size();
	int i =0;
	for (auto& elem : new_map) {
		MLOG("name(%d): %s :: vecs.size %d :: ", i++, elem.first.c_str(), (int)elem.second.size());
		int j = 0;
		for (auto& vecs : elem.second) {
			MLOG(" vecs.size %d vecs[%d] ", vecs.size(), j++);
			for (auto &v : vecs)
				MLOG(" %f", v);
		}
		MLOG("\n");
	}

	return 0;

}

//=============================================================================
int serialize_test5(int nrows, int nvec)
{
	map<string, vector<float>> my_map, new_map;

	for (int i=0; i<nrows; i++) {
		string name = "ROW_"+to_string(i);
		vector<float> vecs;
		for (int j=0; j<nvec; j++) 
			vecs.push_back((float)100*i+(float)j+rand_1());

		MLOG("before i %d %s vecs.size %d\n", i, name.c_str(), vecs.size());
		my_map[name] = vecs;
	}

	vector<unsigned char> blob;
	size_t size = MedSerialize::get_size(my_map);
	blob.resize(size);
	size_t serialize_size = MedSerialize::serialize(&blob[0], my_map);

	size_t deserialize_size = MedSerialize::deserialize(&blob[0], new_map);

	MLOG("size %d serialize_size %d deserialize_size %d\n", size, serialize_size, deserialize_size);

	int n_samples = (int)new_map.size();
	int i =0;
	for (auto& elem : new_map) {
		MLOG("name(%d): %s :: vecs.size %d :: ", i++, elem.first.c_str(), (int)elem.second.size());
		for (auto &v : elem.second)
			MLOG(" %f", v);
		MLOG("\n");
	}

	return 0;

}

//=============================================================================
int serialize_test6(int nrows, int nvec, int len_vecs)
{
	map<string, vector<vector<float>>> my_map;
	vector<map<string, vector<vector<float>>>> new_map(3);

	for (int i=0; i<nrows; i++) {
		string name = "ROW_"+to_string(i);
		vector<vector<float>> vecs;
		vecs.resize(nvec);
		for (int j=0; j<nvec; j++) {
			for (int k=0; k<len_vecs; k++)
				vecs[j].push_back((float)100*j+(float)k+rand_1());
		}

		MLOG("before i %d %s vecs.size %d vecs[0].size %d\n", i, name.c_str(), vecs.size(), vecs[0].size());
		my_map[name] = vecs;
	}

	vector<unsigned char> blob;
	size_t size = MedSerialize::get_size(my_map, my_map, my_map);
	blob.resize(size);
	size_t serialize_size = MedSerialize::serialize(&blob[0], my_map, my_map, my_map);

	size_t deserialize_size = MedSerialize::deserialize(&blob[0], new_map[0], new_map[1], new_map[2]);

	MLOG("size %d serialize_size %d deserialize_size %d\n", size, serialize_size, deserialize_size);

	for (int v=0; v<3; v++) {
		int n_samples = (int)new_map[v].size();
		int i = 0;
		for (auto& elem : new_map[v]) {
			MLOG("name(%d): %s :: vecs.size %d :: ", i++, elem.first.c_str(), (int)elem.second.size());
			int j = 0;
			for (auto& vecs : elem.second) {
				MLOG(" vecs.size %d vecs[%d] ", vecs.size(), j++);
				for (auto &v : vecs)
					MLOG(" %f", v);
			}
			MLOG("\n");
		}
	}
	return 0;

}


//=============================================================================
TEST_CASE("serialization tests", "[serialization]")
{

	MLOG("==========================================\n");
	serialize_test2();
	MLOG("==========================================\n");
	serialize_test3();
	MLOG("==========================================\n");
	serialize_test1(5, 5);
	MLOG("==========================================\n");
	serialize_test1(25, 0);
	MLOG("==========================================\n");
	serialize_test5(5, 10);
	MLOG("==========================================\n");
	serialize_test4(10, 2, 5);
	MLOG("==========================================\n");
	serialize_test4(7, 3, 3);
	MLOG("==========================================\n");
	serialize_test6(5, 2, 3);
	MLOG("==========================================\n");
}