#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 15:37:34 2015

@author: avi
"""

import csv
import sys

def get_year_date(s_in):
    s1 = s_in.split(' ')
    ymd = s1[0].split('-')
    year = ymd[0]
    date = str(10000*int(ymd[0])++100*int(ymd[1])+int(ymd[2]))
    return [year, date]
  
def read_dict(fname,mydict,from_code,to_code):
    with open(fname,'r') as fdict:
        for line in fdict:
            elems = line.split('\t')
            if elems[0] == "DEF" and int(elems[1])>=from_code and int(elems[1])<=to_code:
                elems[2].strip();
                a = elems[2]
                a = a [:-1] 
                #print "#>",elems[0],elems[2],a,elems[1]
                mydict[a] = elems[1]
                
  
def write_uniq_tuples(fout,tup_list):
    f = open(fout,'w')
    i = 0
    prev_s = ' '
    print "\nWriting output file ",fout
    for tup in tup_list:
        i = i + 1
        if (i%100000 == 0):
            sys.stdout.write('*')
            sys.stdout.flush()
        s = ' '.join(map(str,tup)) + '\n'
        if s != prev_s:
           f.write(s)
        prev_s = s
    f.close()
    sys.stdout.write('\n')
        
def prep_demographics(fname,fout):
    print "preparing demographics from file",fname
    mylist = []
    i = 0
    with open(fname,'rb') as csvfile:       
        reader = csv.reader(csvfile, delimiter=',')
        next(reader,None)
        for row in reader:
            i = i + 1
            if i%100000 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            if row[2] == "ז":
                tup1 = [row[0],"GENDER",1]
            else:
                tup1 = [row[0],"GENDER",2]
            mylist.append(tup1)

            yd = get_year_date(row[1])

            tup2 = [row[0],"BDATE",yd[1]]
            mylist.append(tup2)

            tup3 = [row[0],"BYEAR",yd[0]]
            mylist.append(tup3)

            yd = get_year_date(row[3])
            tup4 = [row[0],"JOIN_DATE",yd[1]]
            mylist.append(tup4)
            
            if (row[5]=='2' and row[6]=='2') or (row[5]=='2' and row[6]=='8'):
                yd = get_year_date(row[4])
                tup5 = [row[0],"LEAVE_DATE",yd[1]]
                mylist.append(tup5)
                
            if (row[5]=='2' and row[6]=='8'):
                yd = get_year_date(row[4])
                tup6 = [row[0],"DEATH",yd[1]]
                mylist.append(tup6)    
        
            tup7 = [row[0],"BRANCH",row[8]]
            mylist.append(tup7)

            tup8 = [row[0],"DISTRICT",row[10]]
            mylist.append(tup8)            

            yd = get_year_date(row[4])
            tup9 = [row[0],"Censor",yd[1],int(row[5])*1000+int(row[6])]
            mylist.append(tup9)
            
        mylist.sort(key = lambda x : (int(x[0]),x[1]))
        write_uniq_tuples(fout,mylist)

def prep_sig_col3(name,fname,fout,col_id,col_date,col_val,parse_date):
    print "preparing ",name,"from file",fname
    mylist = []
    i = 0
    prev_tup = []
    with open(fname,'rb') as csvfile:       
        reader = csv.reader(csvfile, delimiter=',')
        next(reader,None)
        for row in reader:
            i = i + 1
            if i%100000 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            if parse_date!=0:
                yd = get_year_date(row[col_date])
                date = yd[1]
            else:
                date = row[col_date]
            tup = [row[col_id],name,date,row[col_val]]
            if tup != prev_tup and int(row[col_id]) != 0:    
                mylist.append(tup)
            prev_tup = tup
        mylist.sort(key = lambda x : (int(x[0]),x[1],int(x[2])))
        write_uniq_tuples(fout,mylist)

def prep_labsig(name,fname,fout,col_id,col_sig,col_date,col_val,parse_date):
    print "preparing ",name,"from file",fname
    mylist = []
    i = 0
    j = 0
    max_lines = 10000000
    prev_tup = []
    with open(fname,'rb') as csvfile:       
        reader = csv.reader(csvfile, delimiter=',')
        #reader = csv.reader(csvfile, delimiter=' ')
        next(reader,None)
        for row in reader:
            #print row
            i = i + 1
            if i%10000 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            if parse_date!=0:
                yd = get_year_date(row[col_date])
                date = yd[1]
            else:
                date = row[col_date]

            tup = [row[col_id],row[col_sig],date,row[col_val]]
            if tup != prev_tup and int(row[col_id]) != 0:
                mylist.append(tup)
            prev_tup = tup
            if i==max_lines:
                mylist.sort(key = lambda x : (int(x[0]),int(x[1]),int(x[2])))
                fout_part = fout + ".part"+str(j)
                write_uniq_tuples(fout_part,mylist)
                j = j + 1
                i = 0
                mylist = []
        mylist.sort(key = lambda x : (int(x[0]),int(x[1]),int(x[2])))
        fout_part = fout + ".part"+str(j)
        write_uniq_tuples(fout_part,mylist)        
        
def prep_drugsig(name,fname,fout,col_id,col_date,col_val,col_span,parse_date):
    print "preparing ",name,"from file",fname
    mylist = []
    i = 0
    j = 0
    max_lines = 50000000
    prev_tup = []
    with open(fname,'rb') as csvfile:       
        reader = csv.reader(csvfile, delimiter=',')
        next(reader,None)
        for row in reader:
            i = i + 1
            if i%100000 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            if parse_date!=0:
                yd = get_year_date(row[col_date])
                date = yd[1]
            else:
                date = row[col_date]
            span = row[col_span]
            span.strip()
            if (span == ""):
                span = 0    
            tup = [row[col_id],"Drug",date,100000+int(row[col_val]),span]
            if tup != prev_tup and int(row[col_id]) != 0:            
                mylist.append(tup)
            prev_tup = tup
            if i==max_lines:
                print "before sort"
                mylist.sort(key = lambda x : (int(x[0]),int(x[2]),int(x[3])))
                print "after sort"
                fout_part = fout + ".part"+str(j)
                write_uniq_tuples(fout_part,mylist)
                j = j + 1
                i = 0
                mylist = []
        print "before sort"
        mylist.sort(key = lambda x : (int(x[0]),int(x[2]),int(x[3])))
        print "after sort"
        fout_part = fout + ".part"+str(j)
        write_uniq_tuples(fout_part,mylist)                
            
def prep_sig_col2(name,fname,fout,col_id,col_date,parse_date):
    print "preparing ",name,"from file",fname
    mylist = []
    i = 0
    prev_tup = []
    with open(fname,'rb') as csvfile:       
        reader = csv.reader(csvfile, delimiter=',')
        next(reader,None)
        for row in reader:
            i = i + 1
            if i%100000 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            if parse_date!=0:
                yd = get_year_date(row[col_date])
                date = yd[1]
            else:
                date = row[col_date]
            tup = [row[col_id],name,date]
            if tup != prev_tup and int(row[col_id]) != 0:
                mylist.append(tup)
            prev_tup = tup
        mylist.sort(key = lambda x : (int(x[0]),x[1],int(x[2])))
        write_uniq_tuples(fout,mylist) 
   
def prep_hosp(dict_fname,fname,fout):
    loc_dict = {}
    dep_dict = {}
    mylist = []
    read_dict(dict_fname,loc_dict,30000,30999)
    read_dict(dict_fname,dep_dict,31000,31999)
    nskip = 0;
    with open(fname,'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        next(reader,None)
        for row in reader:
            pid = row[0]
            date = row[4]
            days = row[6]
            a = row[7].decode('iso-8859-8').encode('utf-8')
            b = row[8].decode('iso-8859-8').encode('utf-8')
            if a in loc_dict.keys() and b in dep_dict.keys() and int(pid)>0 :
#                print row[0],mydict[a],a,mydict[b],b
                 tup = [pid,"Hospitalization",date,days] 
                 mylist.append(tup)
                 tup = [pid,"Hospitalization_Loc",date,loc_dict[a]]
                 mylist.append(tup)
                 tup = [pid,"Hospitalization_Dep",date,dep_dict[b]]
                 mylist.append(tup)
            else:
                nskip = nskip + 1
                print "##>",a,"<####>",b,"<##",nskip
    mylist.sort(key = lambda x : (int(x[0]),x[1],int(x[2])))
    write_uniq_tuples(fout,mylist)
 
#def prep_diagnosis(dict_fname,dual_dict_)
   
in_dir1 = "/server/Data/Maccabi_JUL2014/RCVD_21DEC2015/"
in_dir2 = "/server/Data/Maccabi_JUL2014/RCVD_19NOV2015/"
##in_dir3 = "/server/Data/Maccabi_JUL2014/RCVD_17FEB2015/"
out_dir = "/server/Work/Users/Avi/inframed/prep_maccabi_dec2015/"
#prep_demographics(in_dir1+"Demographics.csv",out_dir+"demographics")
#prep_sig_col3("SMOKING",in_dir1+"Smoking.txt",out_dir+"smoking",0,2,1,1)
##tools/parse_urine.pl /server/Data/Maccabi_JUL2014/RCVD_21DEC2015/Urine\ Lab\ Tests.txt | sort -k1n -k2n -k3n > urine 
#prep_sig_col3("Active_Cancer",in_dir2+"Active_Cancer.txt",out_dir+"active_cancer",0,1,2,1)
#prep_sig_col3("BMI",in_dir2+"BMI.txt",out_dir+"bmi",0,1,2,1)
#prep_sig_col3("Colonscopy",in_dir2+"Colonoscopy_DATA.csv",out_dir+"colonscopy",0,3,5,0)
#prep_sig_col2("Gastro_Visits",in_dir2+"Gastro_Visits.csv",out_dir+"gastro_visits",0,1,0)
#prep_sig_col3("Height",in_dir2+"Height.txt",out_dir+"height",0,1,2,1)
#prep_sig_col3("Weight",in_dir2+"Weight.txt",out_dir+"weight",0,1,2,1)
#prep_labsig("Lab2004",in_dir2+"LabsData_2004.txt",out_dir+"lab2004",0,1,2,3,1)
#prep_labsig("Lab2008",in_dir2+"LabsData_2008.txt",out_dir+"lab2008",0,1,2,3,1)
#prep_labsig("Lab2012",in_dir2+"LabsData_2012.txt",out_dir+"lab2012",0,1,2,3,1)
#prep_labsig("Lab2015",in_dir2+"LabsData_2015.txt",out_dir+"lab2015",0,1,2,3,1)
prep_labsig("LabCRP",out_dir+"CRP_G6PD_TIBC_2015-FEB-17.parsed",out_dir+"lab_crp",0,1,2,3,1)
##tools/parse_urine.pl /server/Data/Maccabi_JUL2014/RCVD_19NOV2015/Occult\ blood\ test.csv | grep -v "##" > fecal
#prep_drugsig("Medication2004",in_dir2+"Medications_2004.txt",out_dir+"Drugs2004",0,1,2,3,0);
#prep_drugsig("Medication2008",in_dir2+"Medications_2008.txt",out_dir+"Drugs2008",0,1,2,3,0);
#prep_drugsig("Medication2012",in_dir2+"Medications_2012.txt",out_dir+"Drugs2012",0,1,2,3,0);
#prep_drugsig("Medication2015",in_dir2+"Medications_2015.txt",out_dir+"Drugs2015",0,1,2,3,0);
#prep_hosp(out_dir+"dict.hospitalizations",in_dir2+"Hospitalization.txt",out_dir+"hospitalizations")
#less Registry.21Dec15 | awk -F"\t" '(NR>1){a=$4; if (a=="") a=9; print $1"\t"a"\t"$2"\t"$3}' | sort -k1n -k3n > ../registry

