from __future__ import print_function
from collections import defaultdict
import glob
import argparse
from common import *

parser = argparse.ArgumentParser()
parser.add_argument('--in_AHDCodes_file', default='/server/Data/THIN1601/THINAncil1601/text/AHDCodes1601.txt',type=argparse.FileType('r'))
parser.add_argument('--in_AHDReadcodes_file', default='/server/Data/THIN1601/THINAncil1601/text/Readcodes1601.txt', type=argparse.FileType('r'))
parser.add_argument('--in_AHDlookups_file', default='/server/Data/THIN1601/THINAncil1601/text/AHDlookups1601.txt', type=argparse.FileType('r'))
parser.add_argument('--in_AHD_files_prefix', default='/server/Data/THIN1601/THINDB1601/')
parser.add_argument('--in_ID2NR_file', type=argparse.FileType('r'))
parser.add_argument('--out_clinical_files_prefix')
args = parser.parse_args()

smoking_medcodes = \
{
"1374.00":{"desc":"Moderate smoker - 10-19 cigs/d", "cigs":19  },
"1375.00":{"desc":"Heavy smoker - 20-39 cigs/day", "cigs":39	 },	
"1373.00":{"desc":"Light smoker - 1-9 cigs/day", "cigs":9	 },	
"1379.00":{"desc":"Ex-moderate smoker (10-19/day)", "cigs":19  },
"137A.00":{"desc":"Ex-heavy smoker (20-39/day)", "cigs":39  },
"1378.00":{"desc":"Ex-light smoker (1-9/day)", "cigs":9   },
"1372.00":{"desc":"Trivial smoker - < 1 cig/day", "cigs":1   },
"1376.00":{"desc":"Very heavy smoker - 40+cigs/d", "cigs":49  },
}

id2nr = read_id2nr(args.in_ID2NR_file)

err_file_name = args.out_clinical_files_prefix + ".clinical_stat"
err_file = file(err_file_name, 'a')
eprint("appending to", err_file_name)

in_file_names = glob.glob(args.in_AHD_files_prefix)
eprint("about to process", len(in_file_names), "files")
for in_file_name in in_file_names:
    pracid = in_file_name[-5:]
    eprint("reading from", in_file_name)
    
    stats = {"unknown_id": 0, "bad_ahdflag": 0, "non_numeric_data": 0, "read": 0, "wrote": 0}
    
    data = defaultdict(list)
    for l in file(in_file_name):
        stats["read"] += 1
        patid, eventdate, ahdcode, ahdflag, data1, data2, data3, data4, data5, data6, medcode = parse_ahd_line(l)
        combid = pracid + patid
        if combid not in id2nr:
            stats["unknown_id"] += 1
            continue
        if ahdflag != 'Y':
            stats["bad_ahdflag"] += 1
            continue
        
        def add_numeric_to_data(combid, signal, eventdate, v):
            if not is_number(v):
                stats["non_numeric_data"] += 1
            else:
                data[signal].append((id2nr[combid], signal, eventdate, float(v)))
        def add_categorical_to_data(combid, signal, eventdate, v):
                data[signal].append((id2nr[combid], signal, eventdate, v))
            
        if ahdcode == '1005010500': #Blood Presure
            if not is_number(data1):
                data1 = -1
            if not is_number(data2):
                data2 = -2                
            data["BP"].append((id2nr[combid], "BP", eventdate, int(data1), int(data2)))
        if ahdcode == '1005010200': #Weight 
            add_numeric_to_data(combid, "WEIGHT", eventdate, data1)
            if data3 != '':
                add_numeric_to_data(combid, "BMI", eventdate, data3)
        if ahdcode == '1005010100': #Height
            add_numeric_to_data(combid, "HEIGHT", eventdate, data1)
        if ahdcode == '1003040000': #Smoking
            smoke_status = {"N": 0, "D": 1, "Y": 2}
            if data1 in smoke_status:
                code = smoke_status[data1]
                cigs = -1
                if medcode in smoking_medcodes:
                    cigs = smoking_medcodes[medcode]["cigs"]
                if is_number(data2) and 0 < int(data2) < 60:
                    cigs = int(data2)
                data["SMOKING"].append((id2nr[combid], "SMOKING", eventdate, int(code), int(cigs)))
                if is_number(data6):
                    data["STOPPED_SMOKING"].append((id2nr[combid], "STOPPED_SMOKING", eventdate, data6.ljust(8, "0")))
                    
        if ahdcode == '1003050000': #Alcohol
            alcohol_units = -1
            if data2 != '' and is_number(data2) and 0 < int(data2) < 100:
                alcohol_units  = int(data2)                        
            alcohol_status = {"N": 0, "D": 0, "Y": 1}
            code = None
            if data1 in alcohol_status:
                code = alcohol_status[data1]
            elif data1 == '' and alcohol_units == 0:
                code = alcohol_status["N"]
            if code is not None:
                data["ALCOHOL"].append((id2nr[combid], "ALCOHOL", eventdate, int(code), int(alcohol_units)))
        if ahdcode == '1009300000': #Pulse
            alcohol_units = -1
            if data1 != '' and is_number(data1) and 50 < int(data1) < 150:
                add_numeric_to_data(combid, "PULSE", eventdate, data1)
        if ahdcode == '1001400080':
            qualifier = data4
            if qualifier == '':
                add_categorical_to_data(combid, "FECAL_TEST", eventdate, 'EMPTY_THIN_FIELD')
            else:
                add_categorical_to_data(combid, "FECAL_TEST", eventdate, qualifier)
        if ahdcode == '1001400169':
            qualifier = data4
            if qualifier == '':
                add_categorical_to_data(combid, "Colonscopy", eventdate, 'EMPTY_THIN_FIELD')
            else:
                add_categorical_to_data(combid, "Colonscopy", eventdate, qualifier)            
            
    for k, v in data.iteritems():
        v.sort()
        out_file_name = args.out_clinical_files_prefix + k
        eprint("appending to", out_file_name)
        out_file = file(out_file_name, 'a')
        for l in v:
            print("\t".join(map(str, l)), file=out_file)

    write_stats(stats, pracid, err_file)
    
