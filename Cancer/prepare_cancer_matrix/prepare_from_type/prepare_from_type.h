// Print the 'lines' matrix into a file

int last_cancer_dates[] = {20091231,20111231,20111231,20121231 /*20091231*/, 20991231} ; // Regular/Full/Complete/THIN Runs/Unlimited

void writefile(char *file_name)
{

	FILE *fout ;
	fout = fopen(file_name, "wb");
	assert(fout != NULL) ;

	fwrite(&idnameptr, 1, sizeof(idnameptr), fout);
	fwrite(lines, idnameptr, sizeof(lines[0]), fout);
	fclose(fout);

	return ;
}

void writefile(char *file_name, int gender)
{

	FILE *fout ;
	fout = fopen(file_name, "wb");
	assert(fout != NULL) ;

	int num = 0 ;
	for (int i=0; i<idnameptr; i++) {
		if (lines[i][4] == gender)
			num ++ ;
	}

	fwrite(&num, 1, sizeof(idnameptr), fout);
	for (int i=0; i<idnameptr; i++) {
		if (lines[i][4] == gender)
			fwrite(lines[i],sizeof(lines[0]),1,fout);
	}

	fclose(fout);

	return ;
}

void write_txtfile(char *file_name)
{

	FILE *fout ;
	fout = fopen(file_name, "wb");
	assert(fout != NULL) ;

	for(int i =0; i<enumlistcol-1; i++)
		fprintf(fout,"%s\t", headers[i]);
	fprintf(fout,"%s\n",headers[enumlistcol-1]) ;
	

	for(int i=0; i<idnameptr; i++) {
		for(int j=0; j<enumlistcol-1; j++)
			fprintf(fout,"%f\t", lines[i][j]);
		fprintf(fout,"%f\n",lines[i][enumlistcol-1]) ;
	}

	fclose(fout);
	return ;
}

// Read list of cancers and mark relevant ones
void readlist (vector<string>& relevant, int igroup) {
	FILE *fin = fopen(GRP_FILE,"r") ;
	assert(fin != NULL) ;

	relevant.clear() ;

	char *ptr;
	while(!(feof(fin))) {

		char *usebuf = buf;
		if (fgets(usebuf, 4096, fin) == NULL)
			break ;

		ptr = strpbrk(usebuf," ");
		assert(ptr != NULL) ;

		buf1[0] = usebuf;
		buf1[0][(int)(ptr-usebuf)]='\0';
		int id = atoi(buf1[0]) ;

		if (id == igroup) {
			usebuf = ptr+1;
			ptr=strpbrk(usebuf,"\n") ;
			assert(ptr != NULL) ;
			buf1[1] = usebuf ;
			buf1[1][(int)(ptr-usebuf)] = '\0' ;
			relevant.push_back(buf1[1]) ;
		}
	}
}


// Read full-cancer registry and mark according to relevant groups
void readrasham(vector<string>& relevant,int type) {

	FILE *fin = fopen("\\\\server\\Data\\macabi4\\DataFrom27-12-11\\cancer_register_22-12-11.csv","r") ;
	assert(fin != NULL) ;

	for (int i=0; i<idnameptr; i++)
		lines[i][7] = 0 ;

	int lineno=0;
	char *ptr;
	while(!(feof(fin)))
	{
	 
		char *usebuf = buf;
		fgets(usebuf, 4096, fin);
		lineno++;
		 
		if (lineno%10000==0) fprintf(stderr,"Rasham: <%d>\n", lineno);
		int l=0;
		do 
		{
			
			ptr = strpbrk(usebuf,",");
			buf1[l] = usebuf;
			if (ptr==NULL) {
				ptr = strpbrk(usebuf,"\n") ;
				if (ptr != NULL)
					buf1[l][(int)(ptr-usebuf)] = '\0' ;
				break ;
			} else
				buf1[l][(int)(ptr-usebuf)]='\0';
			 
			l++;
			usebuf = ptr+1;
			 
		} while (usebuf!=NULL);

		if (strcmp(buf1[0],"NUMERATOR")==0)
			continue ;

		int idnum = atoi(buf1[0]) ;
		int year=0;
		int month=0;
		int day =0;

		int chplace =0;
		sscanf(&buf1[4][chplace],"%d", &day);
		
		while(buf1[4][chplace]!='/') chplace++;
		chplace++;
		sscanf(&buf1[4][chplace],"%d", &month);
		while(buf1[4][chplace]!='/') chplace++;
		chplace++;
		sscanf(&buf1[4][chplace],"%d", &year);

		int date = year*100*100+month*100+day;
		int registry_days = get_days(date) ;

		char group[4096] ;
		sprintf(group,"%s,%s,%s",buf1[5],buf1[6],buf1[7]) ;

		int ingroup = 0 ;
		for (unsigned int i=0; i<relevant.size(); i++) {
			if (strcmp(relevant[i].c_str(),group)==0) {
				ingroup = 1 ;
				break ;
			}
		}
		
		if (line_nos.find(idnum) != line_nos.end()) {
			for (unsigned int i=0; i<line_nos[idnum].size(); i++) {
				int iline = line_nos[idnum][i] ;

				if (lines[iline][7] == 0 || date < lines[iline][8] ) {
					int test_days = get_days((int) lines[iline][1]) ;
					if (ingroup || test_days - registry_days < DAYS_TO_HEALING) {
						lines[iline][8] = date ;
						if (date > last_cancer_dates[type])
							lines[iline][7] = -1 ;
						else
							lines[iline][7] = ingroup ? 1 : 3 ;
					}
				}
			}
		}

	}

	int tot[3] = {0,0,0} ;
	for (int i=0; i<idnameptr; i++) {
		if (lines[i][7] == 0) {
			tot[0]++ ;
		} else if (lines[i][7] == 1) {
			tot[1]++ ;
		} else
			tot[2]++ ;
	}

	printf("Counts : %d healthy, %d in group, %d other\n",tot[0],tot[1],tot[2]) ;
}

void read_rasham(vector<string>& relevant, int type, string reg_fn="") {

	if (reg_fn == "") {
		reg_fn = REG_FILE;
	}
	FILE *fin = fopen(reg_fn.c_str(), "r") ;
	assert(fin != NULL) ;

	for (int i=0; i<idnameptr; i++)
		lines[i][7] = 0 ;

	int lineno=0;
	char *ptr;
	while(!(feof(fin))){ 
		char *usebuf = buf;
		fgets(usebuf, 4096, fin);
		lineno++;
	 
		if (lineno%10000==0) fprintf(stderr,"Rasham: <%d>\n", lineno);
		int l=0;

		do {	
			ptr = strpbrk(usebuf,",");
			buf1[l] = usebuf;
			
			if (ptr==NULL) {
				ptr = strpbrk(usebuf,"\n") ;
				if (ptr != NULL)
					buf1[l][(int)(ptr-usebuf)] = '\0' ;
				break ;
			} else
				buf1[l][(int)(ptr-usebuf)]='\0';
			
			l++;
			usebuf = ptr+1;
			
		} while (usebuf!=NULL);

		if (strcmp(buf1[0],"NUMERATOR")==0)
			continue ;
		
		int idnum = atoi(buf1[0]) ;
		int year=0;
		int month=0;
		int day =0;

		int chplace =0;
		sscanf(&buf1[5][chplace],"%d", &month);
		while(buf1[5][chplace]!='/') chplace++;
		chplace++;
		sscanf(&buf1[5][chplace],"%d", &day);
		while(buf1[5][chplace]!='/') chplace++;
		chplace++;
		sscanf(&buf1[5][chplace],"%d", &year);

		int date = year*100*100+month*100+day;
		int registry_days = get_days(date) ;

		char group[4096] ;
		sprintf(group,"%s,%s,%s",buf1[14],buf1[15],buf1[16]) ;

		int ingroup = 0 ;
		for (unsigned int i=0; i<relevant.size(); i++) {
			if (strcmp(relevant[i].c_str(),group)==0) {
				ingroup = 1 ;
				break ;
			}
		}

		int mec_stage = atoi(buf1[4]) ;
	
		if (line_nos.find(idnum) != line_nos.end()) {
			for (unsigned int i=0; i<line_nos[idnum].size(); i++) {
				int iline = line_nos[idnum][i] ;

				if (lines[iline][7] == 0 || date < lines[iline][8] ) {
					int test_days = get_days((int) lines[iline][1]) ;
					if (ingroup || test_days - registry_days < DAYS_TO_HEALING) {
						lines[iline][8] = date ;
						if (date > last_cancer_dates[type])
							lines[iline][7] = -1 ;
						else
//							lines[iline][7] = (ingroup ? 1 : 3) ;
							lines[iline][7] = (ingroup ? 1 : 3) + (mec_stage/10.0) ;
					}
				}
			}
		}
	}

	fprintf(stderr,"%d ...\n",idnameptr) ;
	int tot[3] = {0,0,0} ;
	for (int i=0; i<idnameptr; i++) {
		if (lines[i][7] == 0) {
			tot[0]++ ;
		} else if ((int)(lines[i][7]) == 1) {
			tot[1]++ ;
		} else
			tot[2]++ ;
	}

	printf("Counts : %d healthy, %d in group, %d other\n",tot[0],tot[1],tot[2]) ;
}

void readNewRasham(vector<string>& relevant, int type) {

	FILE *fin = fopen(REG_FILE,"r") ;
	assert(fin != NULL) ;

	for (int i=0; i<idnameptr; i++)
		lines[i][7] = 0 ;

	int lineno=0;
	char *ptr;
	while(!(feof(fin)))
	{
	 
		char *usebuf = buf;
		fgets(usebuf, 4096, fin);
		lineno++;
		 
		if (lineno%10000==0) fprintf(stderr,"Rasham: <%d>\n", lineno);
		int l=0;
		do 
		{
			
			ptr = strpbrk(usebuf,",");
			buf1[l] = usebuf;
			if (ptr==NULL) {
				ptr = strpbrk(usebuf,"\n") ;
				if (ptr != NULL)
					buf1[l][(int)(ptr-usebuf)] = '\0' ;
				break ;
			} else
				buf1[l][(int)(ptr-usebuf)]='\0';
			 
			l++;
			usebuf = ptr+1;
			 
		} while (usebuf!=NULL);

		if (strcmp(buf1[0],"NUMERATOR")==0)
			continue ;

		int idnum = atoi(buf1[0]) ;
		int year=0;
		int month=0;
		int day =0;

		int chplace =0;
		sscanf(&buf1[5][chplace],"%d", &month);
		while(buf1[5][chplace]!='/') chplace++;
		chplace++;
		sscanf(&buf1[5][chplace],"%d", &day);
		while(buf1[5][chplace]!='/') chplace++;
		chplace++;
		sscanf(&buf1[5][chplace],"%d", &year);

		int date = year*100*100+month*100+day;
		int registry_days = get_days(date) ;

		char group[4096] ;
		sprintf(group,"%s,%s,%s",buf1[14],buf1[15],buf1[16]) ;

		int ingroup = 0 ;
		for (unsigned int i=0; i<relevant.size(); i++) {
			if (strcmp(relevant[i].c_str(),group)==0) {
				ingroup = 1 ;
				break ;
			}
		}

		int mec_stage = atoi(buf1[4]) ;
		
		if (line_nos.find(idnum) != line_nos.end()) {
			for (unsigned int i=0; i<line_nos[idnum].size(); i++) {
				int iline = line_nos[idnum][i] ;

				if (lines[iline][7] == 0 || date < lines[iline][8] ) {
					int test_days = get_days((int) lines[iline][1]) ;
					if (ingroup || test_days - registry_days < DAYS_TO_HEALING) {
						lines[iline][8] = date ;
						if (date > last_cancer_dates[type])
							lines[iline][7] = -1 ;
						else
							lines[iline][7] = (ingroup ? 1 : 3) + (mec_stage/10.0) ;
//							lines[iline][7] = (ingroup ? 1 : 3) ;
					}
				}
			}
		}

	}

	int tot[3] = {0,0,0} ;
	for (int i=0; i<idnameptr; i++) {
		if (lines[i][7] == 0) {
			tot[0]++ ;
		} else if (lines[i][7] == 1) {
			tot[1]++ ;
		} else
			tot[2]++ ;
	}

	printf("Counts : %d healthy, %d in group, %d other\n",tot[0],tot[1],tot[2]) ;
}

int read_ids_list(char *fname,map<int,int>& ids_list) {

	FILE *fp = fopen(fname,"r") ;
	if (fp == NULL) {
		fprintf(stderr,"Cannot open %s for reading\n",fname) ;
		return -1 ;
	}

	int id ;
	while (!feof(fp)) {
		int rc = fscanf(fp,"%d\n",&id);
		if (rc == EOF)
			return 0 ;

		if (rc != 1) {
			fprintf(stderr,"Cannot read from file %s\n",fname) ;
			return -1 ;
		}

		ids_list[id] = 1 ;
	}

	return 0 ;
}

// Read list of cancers and mark relevant ones
void read_list (vector<string>& relevant, int igroup) {
	FILE *fin = fopen(GRP_FILE,"r") ;
	assert(fin != NULL) ;

	relevant.clear() ;

	char *ptr;
	while(!(feof(fin))) {

		char *usebuf = buf;
		if (fgets(usebuf, 4096, fin) == NULL)
			break ;

		ptr = strpbrk(usebuf," ");
		assert(ptr != NULL) ;

		buf1[0] = usebuf;
		buf1[0][(int)(ptr-usebuf)]='\0';
		int id = atoi(buf1[0]) ;

		if (id == igroup) {
			usebuf = ptr+1;
			ptr=strpbrk(usebuf,"\n") ;
			assert(ptr != NULL) ;
			buf1[1] = usebuf ;
			buf1[1][(int)(ptr-usebuf)] = '\0' ;
			relevant.push_back(buf1[1]) ;
		}
	}
}

