from __future__ import print_function
from collections import defaultdict
import sys
import argparse
from os.path import join

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
    
parser = argparse.ArgumentParser()
parser.add_argument('--in_demography_file', type=argparse.FileType('r'), default='/server/Data/THIN1601/PatientDemography1601/patient_demography.csv')
parser.add_argument('--start_from_id', type=int, default=5000000)
parser.add_argument('--out_new_ID2NR_file', type=argparse.FileType('w'), required=True)
parser.add_argument('--out_demography_folder', required=True)
args = parser.parse_args()

eprint('writing new ID2NR')

new_id2nr = {}
seen_old, seen_new = 0, 0
skipped_invalid_patflag = defaultdict(int)
processed = defaultdict(int)
args.in_demography_file.readline() # skip header

def open_for_write(f):
	fname = join(args.out_demography_folder, f)
	eprint("writing:", fname)
	return open(fname, 'w')
prac_file = open_for_write("thin_prac")
main_demo_file = open_for_write("thin_demographic")
small_demo_file = open_for_write("Demographics")
byears_file = open_for_write("byears")
censor_file = open_for_write("censor")
stats_file = open_for_write("thin_demo_stats")

for l in args.in_demography_file:
    combid,pracid,patid,patflag,active,age,dob,sex,regstat,startdate,enddate,regdate,compdate,\
    visdate,amrdate,collectiondate,xferdate,deathdte,smoking,smokedate,alcohol,alcoholunits,\
    alcoholdate,height,heightdate,weight,bmi,weightdate = l.split(',')
    
    if patflag not in set(['A', 'C', 'D']):
        skipped_invalid_patflag[pracid] += 1
        continue
    if combid in new_id2nr:
        eprint("error! combid", combid, "seen twice!")
        exit()
    seen_new += 1
    if seen_new % 1000000 == 0:
        eprint(seen_new,)
    new_id2nr[combid] = args.start_from_id+seen_new
    processed[pracid] += 1
    print("\t".join(map(str,[new_id2nr[combid] , "PRAC", "PRAC_" + pracid])),file=prac_file)
    print("\t".join(map(str,[new_id2nr[combid] , "BYEAR", dob[-4:]])),file=main_demo_file)
    print("\t".join(map(str,[new_id2nr[combid] , "BDATE", dob[-4:]+dob[3:5]+dob[0:2]])),
          file=main_demo_file)
    print("\t".join(map(str,[new_id2nr[combid] , "STARTDATE", startdate[-4:]+startdate[3:5]+startdate[0:2]])),
          file=main_demo_file)
    print("\t".join(map(str,[new_id2nr[combid] , "ENDDATE", enddate[-4:]+enddate[3:5]+enddate[0:2]])),
          file=main_demo_file)          
    print("\t".join(map(str,[new_id2nr[combid] , "GENDER", 1 if sex == 'M' else 2])),file=main_demo_file)
    if len(deathdte)>0:
        #print("\t".join(map(str,[new_id2nr[combid] , "DEATHYEAR", deathdte[-4:]])),file=main_demo_file)
        print("\t".join(map(str,[new_id2nr[combid] , "DEATHDATE", deathdte[-4:]+deathdte[3:5]+deathdte[0:2]])),
              file=main_demo_file)
            
    print("\t".join(map(str,[combid, new_id2nr[combid]])), file=args.out_new_ID2NR_file)
    
    if enddate == "18/01/2016": # we cant rely on the active flag, sometimes its Y and the patient left (e.g. a9937025J)
        stat = "1 1" # regular
        print(" ".join(map(str,[new_id2nr[combid], stat, startdate[-4:]+startdate[3:5]+startdate[0:2]])),file=censor_file)
    else:
        if len(deathdte) > 0:
            stat = "2 8" # dead
        elif len(xferdate) > 0:
            stat = "2 2" # transferred
        else:
            stat = "2 9" # unknown
        print(" ".join(map(str,[new_id2nr[combid], stat, enddate[-4:]+enddate[3:5]+enddate[0:2]])),file=censor_file)                
    print(" ".join(map(str,[new_id2nr[combid], dob[-4:]])),file=byears_file)
    print(" ".join(map(str,[new_id2nr[combid], dob[-4:], sex])),file=small_demo_file)    
            
for k, v in processed.iteritems():
    print("processed", k, v, file=stats_file)
for k, v in skipped_invalid_patflag.iteritems():
    print("skipped_invalid_patflag", k, v, file=stats_file)
        
