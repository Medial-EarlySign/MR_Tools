// Read two lists - pos and neg
void readlists(char *list0, char *list1) {
	fprintf(stderr,"Reading -%s- and -%s-\n",list0,list1) ;

	FILE *fpos = fopen(list1,"r") ;
	FILE *fneg = fopen(list0,"r") ;
	assert(fpos != NULL && fneg != NULL) ;

	map<int, pair<int,int> > ids ;
	int id,date ;

	while(!(feof(fpos))) {
		assert(fscanf(fpos,"%d %d\n",&id,&date) == 2) ;
		pair<int, int> entry(1,date) ;
		ids[id] = entry ;
	}
	fclose(fpos) ;

	while(!(feof(fneg))) {
		assert(fscanf(fneg,"%d %d\n",&id,&date) == 2) ;
		if (ids.find(id) != ids.end() && ids[id].first == 1) {
			fprintf(stderr,"Id %d appears in both lists. Ignored\n",id) ;
			ids.erase(id) ;
		} else {
			pair<int, int> entry(2,date) ;
			ids[id] = entry ;
		}
	}
	fclose(fneg) ;

	for(int i=0; i<idnameptr; i++)
		lines[i][7] = 0 ;

	for (map<int,pair<int, int> >::iterator it=ids.begin(); it!=ids.end(); it++) {
		id = it->first ;
		int type = (it->second).first ;
		int date = (it->second).second ;

		if (line_nos.find(id) != line_nos.end()) {
			for (unsigned int i=0; i<line_nos[id].size(); i++) {
				int iline = line_nos[id][i] ;
				lines[iline][7] = type ;
				lines[iline][8] = date ;
			}
		}
	}
}

// Print the 'lines' matrix into a file
void writefile(char *out)
{

	// Shrink
	int iout = 0 ;
	for(int i=0; i<idnameptr; i++) {
		if (lines[i][7] == 1 || lines[i][7] == 2) {
			assert(iout < MAX_LOCAL_LINES) ;
			memcpy(local_lines[iout],lines[i],enumlistcol*sizeof(double)) ;
			iout ++ ;
		}
	}

	fprintf(stderr,"Downsized : %d => %d\n",idnameptr,iout) ;

	char fname[256] ;
	sprintf(fname,"%s.bin",out) ;

	fprintf(stderr,"Trying to write to %s\n",fname) ;

	FILE *fout ;
	fout = fopen(fname, "wb");
	assert(fout != NULL) ;

	fwrite(&iout, 1, sizeof(iout), fout);
	fwrite(local_lines, iout, sizeof(local_lines[0]), fout);
	fclose(fout);

	/*
	sprintf(fname,"%s.txt",out) ;
	fout =fopen( fname, "w");
	assert(fout != NULL) ;

	for(int i =0; i<enumlistcol-1; i++)
		fprintf(fout,"%s\t", headers[i]);
	fprintf(fout,"%s\n",headers[enumlistcol-1]) ;
	

	for(int i=0; i<iout; i++) {
		for(int j=0; j<enumlistcol-1; j++)
			fprintf(fout,"%f\t", lines[i][j]);
		fprintf(fout,"%f\n",local_lines[i][enumlistcol-1]) ;
	}

	fclose(fout);
	*/
}

void sort_and_write_file(char *out)
{

	// Shrink
	int iout = 0 ;
	for(int i=0; i<idnameptr; i++) {
		if (lines[i][7] == 1 || lines[i][7] == 2) {
			assert(iout < MAX_LOCAL_LINES) ;
			memcpy(local_lines[iout],lines[i],enumlistcol*sizeof(double)) ;
			iout ++ ;
		}
	}

	fprintf(stderr,"Downsized : %d => %d\n",idnameptr,iout) ;

	// Sort
	qsort(local_lines, iout, sizeof(local_lines[0]), compare);

	// Print
	char fname[256] ;
	sprintf(fname,"%s.bin",out) ;

	fprintf(stderr,"Trying to write to %s\n",fname) ;

	FILE *fout ;
	fout = fopen(fname, "wb");
	assert(fout != NULL) ;

	fwrite(&iout, 1, sizeof(iout), fout);
	fwrite(local_lines, iout, sizeof(local_lines[0]), fout);
	fclose(fout);
}
