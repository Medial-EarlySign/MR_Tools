from Configuration import Configuration
from common import *
from signal_mapping_api import *
from signal_unit_api import *
from therapy import *
from medical_to_registry import *
from prep_med import *
import os, re, subprocess, traceback, random
from datetime import datetime

def search_fp(ptrn):
    cfg = Configuration()
    raw_path = fixOS(cfg.doc_source_path)
    search_term = ptrn.lower()
    ahd_code_name = list(filter(lambda f: f.lower().startswith(search_term) ,os.listdir(raw_path)))
    if len(ahd_code_name) != 1:
        raise NameError('coudn''t find %s'%ptrn)
    ahd_code_name = ahd_code_name[0]
    return ahd_code_name

def open_for_write(f):
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    if not(os.path.exists(os.path.join(out_folder, 'demo'))):
        os.makedirs(os.path.join(out_folder, 'demo'))
    fname = os.path.join(out_folder, 'demo', f)
    #eprint("writing:", fname)
    return open(fname, 'w')

def add_numeric_to_data(data, stats, id, signal, eventdate, v):
    if not is_number(v):
        stats["non_numeric_data"] += 1
    else:
        data[signal].append((id, signal, eventdate, float(v)))
def add_categorical_to_data(data, id, signal, eventdate, v):
    data[signal].append((id, signal, eventdate, v))

def read_demo_line(prev_demo_patid, fr):
    demo_l = fr.readline().strip()
    if len(demo_l) == 0:
        raise
    demo_patid, demo_signal, demo_val = demo_l.split()
    demo_patid = int(demo_patid)
    if prev_demo_patid > demo_patid:
        eprint("ERROR! previous demo_patid %d > current demo_patid %d" % 
        (prev_demo_patid, demo_patid))
        raise
    return demo_patid, demo_signal, demo_val

def load_smoking():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.doc_source_path)
    data_path = fixOS(cfg.raw_source_path)
    code_folder = fixOS(cfg.code_folder)
    demo_path = os.path.join(out_folder, 'demo', 'thin_demographic')

    smoke_dir = os.path.join(out_folder, 'enrich_smoking')
    if not(os.path.exists(smoke_dir)):
        os.makedirs(smoke_dir)
    
    err_file_name = os.path.join(smoke_dir ,"STAT_SMOKING_JOIN")
    err_file = file(err_file_name, 'w')
    out_file_name = os.path.join(smoke_dir, "SMOKING_JOIN")
    out_file = io.open(out_file_name, 'w', newline= '')
    eprint("writing to", err_file_name, out_file_name)

    readcodes_name = list(filter(lambda f: f.startswith('Readcodes') ,os.listdir(raw_path)))
    if len(readcodes_name) != 1:
        raise NameError('coudn''t find readcodes_name')
    readcodes_name = readcodes_name[0]
    lines = getLines(raw_path, readcodes_name)
    ahd_read_codes = read_ahd_read_codes(lines)
    create_id2nr()
    lines = getLines(out_folder, 'ID2NR')
    id2nr = read_id2nr(lines)

    demo_patid = -1

    in_file_names = list(filter(lambda f: f.startswith('ahd.') ,os.listdir(data_path)))
    eprint("about to process", len(in_file_names), "files")
    fr = open(demo_path, 'r')
    for in_file_name in in_file_names:
        pracid = in_file_name[-5:]
        eprint("reading from", in_file_name)

        stats = {"unknown_id": 0,\
            "bad_ahdflag": 0, "demo_read": 0, "demo_skipped": 0, "demo_miss": 0, "ahd_read": 0, "wrote": 0}

        out_file.write(unicode("\t".join("numerator yob sex evntdate data1 data2 data5 data6 medcode desc".split()) + '\n'))
        for l in file(os.path.join(data_path,in_file_name)):            
            patid, eventdate, ahdcode, ahdflag, data1, data2, data3, data4, data5, data6, medcode = parse_ahd_line(l)
            combid = pracid + patid
            if combid not in id2nr:
                stats["unknown_id"] += 1
                continue
            if ahdflag != 'Y':
                stats["bad_ahdflag"] += 1
                continue
            if ahdcode != "1003040000":
                continue
            
            stats["ahd_read"] += 1
                
            patid = id2nr[combid]
            while demo_patid < patid:
                # new smoking patient, reset values and look for patient id in demo
                stats["demo_skipped"] += 1
                demo_yob, demo_enddate, demo_gender = None, None, None 
                demo_patid, demo_signal, demo_val = read_demo_line(demo_patid, fr)
                    
            while demo_patid == patid:
                # try to extract the demographics we need
                if demo_signal == 'BYEAR':
                    demo_yob = int(demo_val)
                if demo_signal == 'GENDER':
                    demo_gender = int(demo_val)
                if demo_signal == 'ENDDATE':
                    demo_enddate = int(demo_val[:4])
                if all(x is not None for x in [demo_yob, demo_enddate, demo_gender]):
                    break
                stats["demo_read"] += 1            
                demo_patid, demo_signal, demo_val = read_demo_line(demo_patid, fr)
                
            if all(x is not None for x in [demo_yob, demo_enddate, demo_gender]) and demo_patid == patid:
                # if we have the demo we need            
                out_file.write(unicode("\t".join(map(str,[patid, str(demo_yob) + "0000", demo_gender, eventdate, data1, data2, data5, data6, medcode, ahd_read_codes[medcode]])) + '\n'))
            else:
                stats["demo_miss"] += 1
        write_stats(stats, pracid, err_file)
    fr.close()
    err_file.close()
    out_file.close()

    print('running CMD to group:')
    if os.path.exists(os.path.join(smoke_dir, 'SMOKING_JOIN_GROUPED')):
        os.remove(os.path.join(smoke_dir, 'SMOKING_JOIN_GROUPED'))
    cmd = """cat %s | grep -v numerator | """%( os.path.join(smoke_dir, 'SMOKING_JOIN')) + \
    """perl -F"\\t" -ane '{map {$F[$_]="." if ($F[$_] eq "")} (0..$#F); print join("\\t", @F);}' """ + \
    """ | /server/Work/Users/Ido/bedtools2/bin/groupBy -g 1,2,3 -c 4,5,6,7,8,10 -o collapse,collapse,collapse,collapse,collapse,collapse """ + \
    """ > %s"""%(os.path.join(smoke_dir, 'SMOKING_JOIN_GROUPED'))
    p = subprocess.call(cmd, shell=True)

    if (p != 0 or not(os.path.exists(os.path.join(smoke_dir, 'SMOKING_JOIN_GROUPED')))):
        print ('Error in running Command on Smoking to group. CMD was:\n%s'%cmd)
        raise NameError('stop')
    
    print('Running Final Command')
    if os.path.exists(os.path.join(smoke_dir, 'QTY_SMX')):
        os.remove(os.path.join(smoke_dir, 'QTY_SMX'))
    cmd ="""cat %s | perl %s --qtySmxFileName=%s 2>%s"""%(\
    os.path.join(smoke_dir, 'SMOKING_JOIN_GROUPED'), os.path.join(os.environ['MR_ROOT'], 'Projects', 'Scripts', 'Perl-scripts', 'thin_check_nlst_criteria.pl'), \
    os.path.join(smoke_dir, 'QTY_SMX_tmp') , os.path.join(smoke_dir, 'STDERR_QTY_SMX'))
    p = subprocess.call(cmd, shell=True)

    if (p != 0 or not(os.path.exists(os.path.join(smoke_dir, 'QTY_SMX_tmp')))):
        print ('Error in running Command on Smoking final command. CMD was:\n%s'%cmd)
        raise NameError('stop')

    cmd = """cat %s | awk 'BEGIN {FS="\t"} {print $1"\tSMOKING_ENRICHED\t"$2"\t"$3"\t"$4"\t"$5}' | sort -k1 -n > %s"""%(os.path.join(smoke_dir, 'QTY_SMX_tmp'), os.path.join(smoke_dir, 'QTY_SMX'))
    p = subprocess.call(cmd, shell=True)

    if (p != 0 or not(os.path.exists(os.path.join(smoke_dir, 'QTY_SMX')))):
        print ('Error in running Command on Smoking sort command. CMD was:\n%s'%cmd)
        raise NameError('stop')
    print('Done')

def load_registry():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.doc_source_path)
    data_path = fixOS(cfg.raw_source_path)
    code_folder = fixOS(cfg.code_folder)
    readcodes_name = list(filter(lambda f: f.startswith('Readcodes') ,os.listdir(raw_path)))
    if len(readcodes_name) != 1:
        raise NameError('coudn''t find readcodes_name')
    readcodes_name = readcodes_name[0]
    lines = getLines(raw_path, readcodes_name)
    if not(os.path.exists(os.path.join( out_folder, 'registry'))):
        os.makedirs(os.path.join( out_folder, 'registry'))
    ahd_read_codes = read_ahd_read_codes(lines)
    
    icdo_2_desc = read_icdo_file(getLines(code_folder ,'ICD-O'))
    codes_2_details = read_medcode_file(getLines(code_folder , 'thin_cancer_medcodes_20161103.txt'), ahd_read_codes)
    med2icd = read_medcode_2_icdo_file(getLines(code_folder , 'medcode_2_icdo.txt'))
    translate_cancer_types_table = read_translate_cancer_types_file(getLines(code_folder,'translate_cancer_types.txt'))
    

    create_id2nr()
    lines = getLines(out_folder, 'ID2NR')
    id2nr = read_id2nr(lines)

    in_file_names = list(filter(lambda f: f.startswith('medical.') ,os.listdir(data_path)))
    eprint("about to process", len(in_file_names), "files")

    reg_file_name = os.path.join( out_folder, 'registry',  "REG")
    eprint("writing to %s" % (reg_file_name))
    stats_file_name = os.path.join( out_folder, 'registry',  "reg_stats")
    stats_file = open(stats_file_name, 'w')
    
    reg_lines = []
    for in_filename in in_file_names:
        pracid = in_filename[-5:]
        eprint("reading from %s, pracid = %s" % (in_filename, pracid))
        
        stats = {"unknown_id": 0, "invalid_medflag":0, "read": 0, "wrote": 0}

        prev_combid = -1
        pat_recs = []
        fp= open(os.path.join(data_path, in_filename), 'r')
        fp_lines = fp.readlines()
        fp.close()
        for l in fp_lines:
            stats["read"] += 1
            patid, eventdate, enddate, datatype, medcode, medflag, staffid, source,\
            episode, nhsspec, locate, textid, category, priority, medinfo, inprac,\
            private, medid, consultid, sysdate, modified = parse_medical_line(l)

            combid = pracid + patid 
            if combid not in id2nr:
                stats["unknown_id"] += 1            
                continue
            if medflag not in ['R', 'S']:
                stats["invalid_medflag"] += 1
                continue
            stats["wrote"] += 1
            if prev_combid != combid:
                if prev_combid != -1:
                    handle_single_pat(reg_lines, prev_combid, pat_recs, id2nr, codes_2_details, med2icd, icdo_2_desc, translate_cancer_types_table, ahd_read_codes)
                prev_combid = combid
                pat_recs = []
                
            pat_recs.append({"medcode": medcode, "eventdate": eventdate})
        write_stats(stats, pracid, stats_file)
    if combid in id2nr:
        handle_single_pat(reg_lines, combid, pat_recs, id2nr, codes_2_details, med2icd, icdo_2_desc, translate_cancer_types_table, ahd_read_codes)

    stats_file.close()
    reg_file = open(reg_file_name, 'w')
    reg_lines = sorted(reg_lines, key = lambda l : int(l.split('\t')[0]))
    reg_file = io.open(reg_file_name, 'w', newline='')
    reg_file.writelines(list(map(lambda ln: unicode(ln), reg_lines)))
    reg_file.close()


def load_clinical():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.doc_source_path)
    data_path = fixOS(cfg.raw_source_path)
    create_id2nr()
    lines = getLines(out_folder, 'ID2NR')
    id2nr = read_id2nr(lines)
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
    if not (os.path.exists(os.path.join(out_folder, 'clinical'))):
        os.makedirs(os.path.join(out_folder, 'clinical'))
    err_file_name = os.path.join(out_folder, 'clinical',"clinical_stat")
    err_file = file(err_file_name, 'w')
    eprint("appending to", err_file_name)

    in_file_names = list(filter(lambda f: f.startswith('ahd.') ,os.listdir(data_path)))
    eprint("about to process", len(in_file_names), "files")
    for in_file_name in in_file_names:
        pracid = in_file_name[-5:]
        eprint("reading from", in_file_name)
        
        stats = {"unknown_id": 0, "bad_ahdflag": 0, "non_numeric_data": 0, "read": 0, "wrote": 0}
        
        data = defaultdict(list)
        fp = open(os.path.join(data_path, in_file_name), 'r')
        fp_lines = fp.readlines()
        fp.close()
        for l in fp_lines:
            stats["read"] += 1
            patid, eventdate, ahdcode, ahdflag, data1, data2, data3, data4, data5, data6, medcode = parse_ahd_line(l)
            combid = pracid + patid
            if combid not in id2nr:
                stats["unknown_id"] += 1
                continue
            if ahdflag != 'Y':
                stats["bad_ahdflag"] += 1
                continue
            
            if ahdcode == '1005010500': #Blood Presure
                if not is_number(data1):
                    data1 = -1
                if not is_number(data2):
                    data2 = -2                
                data["BP"].append((id2nr[combid], "BP", eventdate, int(data1), int(data2)))
            if ahdcode == '1005010200': #Weight 
                add_numeric_to_data(data, stats, id2nr[combid], "WEIGHT", eventdate, data1)
                if data3 != '':
                    add_numeric_to_data(data, stats, id2nr[combid], "BMI", eventdate, data3)
            if ahdcode == '1005010100': #Height
                if is_number(data1):
                    data1 = float(data1) * 100 #convert to CM
                add_numeric_to_data(data, stats, id2nr[combid], "HEIGHT", eventdate, data1)
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
                if data1 != '' and is_number(data1):
                    add_numeric_to_data(data, stats, id2nr[combid], "PULSE", eventdate, data1)
            if ahdcode == '1001400080':
                qualifier = data4
                if qualifier == '':
                    add_categorical_to_data(data, id2nr[combid], "FECAL_TEST", eventdate, 'EMPTY_THIN_FIELD')
                else:
                    add_categorical_to_data(data, id2nr[combid], "FECAL_TEST", eventdate, qualifier)
            if ahdcode == '1001400169':
                qualifier = data4
                if qualifier == '':
                    add_categorical_to_data(data, id2nr[combid], "Colonscopy", eventdate, 'EMPTY_THIN_FIELD')
                else:
                    add_categorical_to_data(data, id2nr[combid], "Colonscopy", eventdate, qualifier)            
                
        for k, v in data.items():
            v.sort()
            out_file_name = os.path.join(out_folder, 'clinical', k)
            eprint("appending to", out_file_name)
            out_file = io.open(out_file_name, 'a', newline= '')
            for l in v:
                out_file.write(unicode("\t".join(map(str, l)) + '\n'))
            out_file.close()

        write_stats(stats, pracid, err_file)


def load_therapy():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.doc_source_path)
    prep_rec_from_to()
    path = fixOS(cfg.raw_source_path) + '/'
    path2 = raw_path + '/'
    path3 = os.path.join(out_folder, 'therapy') 
    if not(os.path.exists(path2)):
        os.makedirs(path2)
    if not(os.path.exists(path3)):
        os.makedirs(path3)

    # prepare the actual therapy files
    drates = {}
    create_id2nr()
    lines = getLines(out_folder, 'ID2NR')
    id2nr = read_id2nr(lines)
    read_dosage_rates(os.path.join(fixOS(cfg.code_folder),"dosage_rate"),drates)
    s = "abcdefghij"
    #s = "fghij"
    for i in range(len(s)):
        prep_drug_sig_looper(path,path3 + '/',s[i:i+1],drates,id2nr)

def load_medical():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.doc_source_path)
    data_path = fixOS(cfg.raw_source_path)
    create_id2nr()
    lines = getLines(out_folder, 'ID2NR')
    id2nr = read_id2nr(lines)

    if not(os.path.exists( os.path.join(out_folder, 'medical' ))):
        os.makedirs(os.path.join(out_folder, 'medical'))

    in_file_names = list(filter(lambda f: f.startswith('medical.') ,os.listdir(data_path)))
    eprint("about to process", len(in_file_names), "files")

    medcode_file_name = os.path.join(out_folder, 'medical', "MEDCODE")
    nhsspec_file_name = os.path.join(out_folder, 'medical',  "NHSSPEC")
    if not(os.path.exists(medcode_file_name)) or os.path.getsize(medcode_file_name)  == 0 or not(os.path.exists(nhsspec_file_name)):
        eprint("writing to %s, %s" % (medcode_file_name, nhsspec_file_name))

        medcode_file = io.open(medcode_file_name, 'w', newline = '')
        nhsspec_file = io.open(nhsspec_file_name, 'w', newline = '')
        load_stats_fp = open(os.path.join(out_folder, 'medical', 'all_prac.stats'), 'w')

        flags_inpatien = set(map(lambda c:c ,'gaZVSGHAD'))
        flags_outpatient = set(map(lambda c:c ,'CERIKPY1')) 
        flags_day_case = set(map(lambda c:c ,'BWbkp'))
        cat_to_name = dict()
        cat_to_name['INPATIENT'] = flags_inpatien
        cat_to_name['OUTPATIENT'] = flags_outpatient
        cat_to_name['DAY_CASE'] = flags_day_case
        flags_all = set()
        for tmp, flags in cat_to_name.items():
            flags_all.update(flags)
        # main loop
        for in_filename in in_file_names:
            pracid = in_filename[-5:]
            eprint("reading from %s, pracid = %s" % (in_filename, pracid))
            
            stats = {"unknown_id": 0, "invalid_medflag":0, "read": 0, "wrote": 0}
            
            out_data = [[], []]

            fp = open(os.path.join(data_path, in_filename) ,'r')
            fp_lines = fp.readlines()
            fp.close()
            for l in fp_lines:
                stats["read"] += 1
                patid, eventdate, enddate, datatype, medcode, medflag, staffid, source,\
                episode, nhsspec, locate, textid, category, priority, medinfo, inprac,\
                private, medid, consultid, sysdate, modified =\
                parse_medical_line(l)
                
                combid = pracid + patid
                if combid not in id2nr:
                    stats["unknown_id"] += 1
                    continue
                if medflag not in ['R', 'S']:
                    stats["invalid_medflag"] += 1
                    continue
                out_data[0].append([id2nr[combid], "MEDCODE", eventdate, medcode])
                if len(nhsspec) > 0 and nhsspec != "000" and source in flags_all:
                    fl = None
                    for cat, flags in cat_to_name.items():
                        if source in flags:
                            fl = cat
                            break
                    if fl is None:
                        raise NameError('coudn''t find category')
                    out_data[1].append([id2nr[combid], "NHSSPEC", eventdate, nhsspec, fl])

            write_stats(stats, pracid, load_stats_fp)
            for i, f in enumerate([medcode_file, nhsspec_file]):
                out_data[i].sort()
                for l in out_data[i]:
                    f.write(unicode("\t".join(map(str,l))+ '\n'))
        print('Done creating initiale files')
    print('Preparing other files')
    
    path1 = os.path.join(out_folder, 'medical')
    #path = "/server/Work/Users/Ido/THIN_ETL/medical/"
    path = os.path.join(out_folder,'NonNumeric')

    groups = [["RC_Demographic","0"], ["RC_History","12R"], ["RC_Diagnostic_Procedures","34"], ["RC_Radiology","5"], ["RC_Procedures","678Z"], ["RC_Admin","9"], ["RC_Diagnosis","ABCDEFGHJKLMNPQ"],["RC_Injuries","STU"]]
    L2G = {}
    prep_L2G(groups,L2G)

    #alls = "abcdefghij"
    
    seyfa = "AHDCODE"
    seyfa2 = "ahdsigs_tmp"
    #seyfa = "_MEDCODE"
    #seyfa2 = "_medsigs"
    #for i in range(len(alls)):
    #l = alls[i:i+1]
    src_f = os.path.join(path, seyfa)
    tar_p = os.path.join(path1, seyfa2)
    print ("working on %s"%src_f)
    if os.path.exists(tar_p) and os.path.getsize(tar_p) > 0:
        print('Skipping %s'%tar_p)
    else:
        prep_med_signal_file(src_f , tar_p,L2G)

    print('sorting')
    seyfa2 = 'ahdsigs'
    cmd = 'sort -k1 -n %s > %s'%(tar_p, os.path.join(path1, seyfa2))
    p = subprocess.call(cmd, shell=True)

    if (p != 0 or not(os.path.exists(os.path.join(path1, seyfa2)))):
        print ('Error in running Command to sort ahdsigs CMD was:\n%s'%cmd)
        #raise NameError('stop')
    
    #erase temp
    #seyfa = "_AHDCODE"
    #seyfa2 = "_ahdsigs"
    path = os.path.join(out_folder, 'medical')
    seyfa = "MEDCODE"
    seyfa2 = "medsigs_tmp"
    
    src_f = os.path.join(path, seyfa)
    tar_p = os.path.join(path1, seyfa2)
    print ("working on %s"%src_f)
    if os.path.exists(tar_p) and os.path.getsize(tar_p) > 0:
        print('Skipping %s'%tar_p)
    else:
        prep_med_signal_file(src_f, tar_p,L2G)

    print('sorting')
    seyfa2 = 'medsigs'
    cmd = 'sort -k1 -n %s > %s'%(tar_p, os.path.join(path1, seyfa2))
    p = subprocess.call(cmd, shell=True)

    if (p != 0 or not(os.path.exists(os.path.join(path1, seyfa2)))):
        print ('Error in running Command to sort medsigs CMD was:\n%s'%cmd)
        #raise NameError('stop')
    #erase temp

def load_imms():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.doc_source_path)
    data_path = fixOS(cfg.raw_source_path)
    create_id2nr()
    lines = getLines(out_folder, 'ID2NR')
    id2nr = read_id2nr(lines)

    if not(os.path.exists( os.path.join(out_folder, 'imms' ))):
        os.makedirs(os.path.join(out_folder, 'imms'))

    ahd_code_name = list(filter(lambda f: f.startswith('AHDCodes') ,os.listdir(raw_path)))
    if len(ahd_code_name) != 1:
        raise NameError('coudn''t find AHDCodes')
    ahd_code_name = ahd_code_name[0]

    lines = getLines(raw_path, ahd_code_name)
    ahd_codes = read_ahd_codes(lines)

    err_file_name = os.path.join( out_folder, 'imms', "imms_stat")
    err_file = file(err_file_name, 'w')
    out_file_name = os.path.join( out_folder, 'imms',  "IMMS")
    out_file = io.open(out_file_name, 'w', newline = '')
    eprint("writing to", err_file_name, out_file_name)

    in_file_names = list(filter(lambda f: f.startswith('ahd.') ,os.listdir(data_path)))
    eprint("about to process", len(in_file_names), "files")
    outlines = set()
    for in_file_name in in_file_names:
        pracid = in_file_name[-5:]
        eprint("reading from", in_file_name)
        
        stats = {"unknown_id": 0, "bad_ahdflag": 0, "read": 0, "wrote": 0}
        
        data = defaultdict(list)
        fp = open(os.path.join(data_path ,in_file_name), 'r')
        fp_lines = fp.readlines()
        fp.close()
        for l in fp_lines:
            stats["read"] += 1
            patid, eventdate, ahdcode, ahdflag, data1, data2, data3, data4, data5, data6, medcode = parse_ahd_line(l)
            combid = pracid + patid
            if combid not in id2nr:
                stats["unknown_id"] += 1
                continue
            if ahdflag != 'Y':
                stats["bad_ahdflag"] += 1
                continue
            if ahdcode in ahd_codes and ahd_codes[ahdcode]["datafile"] == "IMMS":
                outlines.add("\t".join([str(id2nr[combid]), "IMMS", eventdate, ahd_codes[ahdcode]["desc"]]) + '\n')

        write_stats(stats, pracid, err_file)
    err_file.close()
    outlines = list(outlines)
    outlines.sort(key = lambda ln : int(ln.split('\t')[0]))   
    out_file.writelines(list(map(lambda ln : unicode(ln),outlines)))
    out_file.close()
            

def load_pvi():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    create_id2nr()
    lines = getLines(out_folder, 'ID2NR')
    id2nr = read_id2nr(lines)

    if not(os.path.exists( os.path.join(out_folder, 'pvi' ))):
        os.makedirs(os.path.join(out_folder, 'pvi'))
    err_file_name = os.path.join(out_folder, 'pvi' ,"pvi_stat")
    err_file = file(err_file_name, 'w')
    out_file_name = os.path.join(out_folder, 'pvi' ,"PVI")
    out_file = io.open(out_file_name, 'w', newline = '')
    eprint("writing to", err_file_name, out_file_name)
    
    data_path = fixOS(cfg.raw_source_path)
    
    in_file_names = list(filter(lambda f: f.startswith('pvi.') ,os.listdir(data_path)))
    eprint("about to process", len(in_file_names), "files")
    outlines = set()
    for in_file_name in in_file_names:
        pracid = in_file_name[-5:]
        eprint("reading from", in_file_name)
        stats = {"unknown_id": 0, "read": 0, "wrote": 0}    
        data = defaultdict(list)
        fp = open(os.path.join(data_path ,in_file_name), 'r')
        fp_lines = fp.readlines()
        fp.close()
        for l in fp_lines:
            stats["read"] += 1
            patid, flags, eventdate = l[0:4],l[4:16],l[16:24]
            combid = pracid + patid
            if combid not in id2nr:
                stats["unknown_id"] += 1
                continue
            outlines.add("\t".join(map(str, [id2nr[combid], "PVI", eventdate, "PVI_" + flags])) + '\n')

        write_stats(stats, pracid, err_file)
    err_file.close()
    outlines = list(outlines)
    outlines.sort(key = lambda ln: int(ln.split('\t')[0]))
    out_file.writelines(list(map(lambda ln : unicode(ln),outlines)))
    out_file.close()
        

def create_id2nr(previous_id2nr=None ,year = datetime.now().year, start_from_id = 5000000):
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.doc_source_path)
    id2nr_path = os.path.join(out_folder, 'ID2NR')
    prac_name = list(filter(lambda f: f.upper().startswith('THINPRAC') ,os.listdir(raw_path)))
    if len(prac_name) != 1:
        raise NameError('coudn''t find THINPrac')
    dict_path = os.path.join(out_folder, 'dicts')
    if not(os.path.exists(dict_path)):
        os.makedirs(dict_path)
    prac_name = prac_name[0]
    lines = getLines(raw_path, prac_name)
    all_pracs = list(sorted(set(map(lambda l: l[0:5] ,lines))))
    wr_lines= list(map(lambda i: 'DEF\t%d\tPRAC_%s\n'%(i, all_pracs[i]) ,range(len(all_pracs))))
    fw = open(os.path.join(dict_path, 'dict.prac'), 'w' )
    fw.writelines(wr_lines)
    fw.close()
    wr_lines= list(map(lambda pr: 'SET\tPRAC\tPRAC_%s\n'%(pr) ,all_pracs))
    prac_data = set(map(lambda n: n[-5:], os.listdir(fixOS(cfg.raw_source_path))))
    
    fw = open(os.path.join(dict_path, 'distinct_prac_set'), 'w' )
    fw.writelines(wr_lines)
    fw.close()
    if not(os.path.exists(id2nr_path)):
        new_id2nr = {}
        old_id2nr = {}
        seen_old, seen_new = 0, 0
        skipped_invalid_patflag = defaultdict(int)
        processed = defaultdict(int)
        fp = open(cfg.patient_demo, 'r')
        lines = fp.readlines() 
        lines = lines[1:] # skip header
        fw_id2nr = open(id2nr_path, 'w')
        if previous_id2nr is not None:
            fp_old = open(previous_id2nr, 'r')
            lines_old = fp_old.readlines()
            fp_old.close()
            fw_id2nr.writelines(lines_old)
            start_from_id = int(lines_old[-1].split('\t')[1])
            for l in lines_old:
                combid, id = l.split('\t')
                old_id2nr[combid] = int(id)
        eprint('writing new ID2NR. year=%d, starting_from=%d'%(year, start_from_id))

        prac_file = open_for_write("thin_prac")
        main_demo_file = open_for_write("thin_demographic")
        small_demo_file = open_for_write("Demographics")
        byears_file = open_for_write("byears")
        censor_file = open_for_write("censor")
        stats_file = open_for_write("thin_demo_stats")

        skip_p = set()
        for l in lines:
            combid,pracid,patid,patflag,active,age,dob,sex,regstat,startdate,enddate,regdate,compdate,\
            visdate,amrdate,collectiondate,xferdate,deathdte,smoking,smokedate,alcohol,alcoholunits,\
            alcoholdate,height,heightdate,weight,bmi,weightdate = l.split(',')
            if pracid not in prac_data:
                if pracid not in skip_p:
                    print('SKIP PRAC %s - not in data prac list'%pracid)
                    skip_p.add(pracid)
                continue
            if patflag not in set(['A', 'C', 'D']):
                skipped_invalid_patflag[pracid] += 1
                continue
            if combid in new_id2nr:
                eprint("error! combid", combid, "seen twice!")
                exit()
            if combid in old_id2nr:
                new_id2nr[combid] = old_id2nr[combid]
            else:
                seen_new += 1
                if seen_new % 1000000 == 0:
                    eprint(seen_new,)
                new_id2nr[combid] = start_from_id+seen_new
            processed[pracid] += 1
            prac_file.write("\t".join(map(str,[new_id2nr[combid], "PRAC", "PRAC_" + pracid])) + '\n')
            main_demo_file.write("\t".join(map(str,[new_id2nr[combid] , "BYEAR", dob[-4:]])) + '\n')
            main_demo_file.write("\t".join(map(str,[new_id2nr[combid] , "BDATE", dob[-4:]+dob[3:5]+dob[0:2]])) + '\n')
            main_demo_file.write("\t".join(map(str,[new_id2nr[combid] , "STARTDATE", startdate[-4:]+startdate[3:5]+startdate[0:2]])) + '\n')
            main_demo_file.write("\t".join(map(str,[new_id2nr[combid] , "ENDDATE", enddate[-4:]+enddate[3:5]+enddate[0:2]])) + '\n')          
            main_demo_file.write("\t".join(map(str,[new_id2nr[combid] , "GENDER", 1 if sex == 'M' else 2])) + '\n')
            if len(deathdte)>0:
                #print("\t".join(map(str,[new_id2nr[combid] , "DEATHYEAR", deathdte[-4:]])),file=main_demo_file)
                main_demo_file.write("\t".join(map(str,[new_id2nr[combid] , "DEATHDATE", deathdte[-4:]+deathdte[3:5]+deathdte[0:2]])) + '\n')
                    
            fw_id2nr.write("\t".join(map(str,[combid, new_id2nr[combid]])) + '\n')
            
            if int(enddate[-4:]) >= year: # we cant rely on the active flag, sometimes its Y and the patient left (e.g. a9937025J)
                stat = "1001" # regular
                censor_file.write("\t".join(map(str,[new_id2nr[combid], 'Censor' ,startdate[-4:]+startdate[3:5]+startdate[0:2], stat])) + '\n')
            else:
                if len(deathdte) > 0:
                    stat = "2008" # dead
                elif len(xferdate) > 0:
                    stat = "2002" # transferred
                else:
                    stat = "2009" # unknown
                censor_file.write("\t".join(map(str,[new_id2nr[combid], 'Censor', enddate[-4:]+enddate[3:5]+enddate[0:2] , stat])) + '\n')                
            byears_file.write(" ".join(map(str,[new_id2nr[combid], dob[-4:]])) + '\n')
            small_demo_file.write(" ".join(map(str,[new_id2nr[combid], dob[-4:], sex])) + '\n')    
        fp.close()     
        for k, v in processed.iteritems():
            stats_file.write("processed %s %d\n"%(k, v))
        for k, v in skipped_invalid_patflag.iteritems():
            stats_file.write("skipped_invalid_patflag %s %d\n"%(k, v))
        fw_id2nr.close()

def createResolveFld(specifyAhd = None):
    cfg = Configuration()
    raw_path = fixOS(cfg.doc_source_path)
    data_path = fixOS(cfg.raw_source_path)
    out_folder = fixOS(cfg.work_path)
    resolvName = 'Resolved'
    nonNumName = 'NonNumeric'
    StatsName = 'Stats'
    if not(os.path.exists(raw_path)):
        raise NameError('config error - doc_path don''t exists')
    if not(os.path.exists(data_path)):
        raise NameError('config error - raw_path don''t exists')
    if not(os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')

    ahd_code_name = list(filter(lambda f: f.startswith('AHDCodes') ,os.listdir(raw_path)))
    if len(ahd_code_name) != 1:
        raise NameError('coudn''t find AHDCodes')
    ahd_code_name = ahd_code_name[0]
    ahd_lookup_name = list(filter(lambda f: f.startswith('AHDlookup') ,os.listdir(raw_path)))
    if len(ahd_lookup_name) != 1:
        raise NameError('coudn''t find AHDlookup')
    ahd_lookup_name = ahd_lookup_name[0]
    readcodes_name = list(filter(lambda f: f.startswith('Readcodes') ,os.listdir(raw_path)))
    if len(readcodes_name) != 1:
        raise NameError('coudn''t find readcodes_name')
    readcodes_name = readcodes_name[0]
    lines = getLines(raw_path, ahd_code_name)
    ahd_codes = read_ahd_codes(lines)
    lines = getLines(raw_path, readcodes_name)
    ahd_read_codes = read_ahd_read_codes(lines)

    lines = getLines(raw_path, ahd_lookup_name)
    ahd_lookups = {'':'NA', '<None>':'<None>'}
    for l in lines:
        dataname, datadesc, lookup, lookupdesc = \
        map(clean_and_strip, [l[0:8],l[8:38],l[38:44],l[44:144]])
        #print("\t".join([dataname, datadesc, lookup, lookupdesc]))
        ahd_lookups[lookup]=lookupdesc
    eprint("found", len(ahd_lookups), "AHD lookups")

    out_prefix = 'all'
    
    create_id2nr()
    lines = getLines(out_folder, 'ID2NR')
    id2nr = read_id2nr(lines)

    if not(os.path.exists(os.path.join(out_folder, nonNumName))):
        os.makedirs(os.path.join(out_folder, nonNumName))
    if not(os.path.exists(os.path.join(out_folder, resolvName))):
        os.makedirs(os.path.join(out_folder, resolvName))
    if not(os.path.exists(os.path.join(out_folder, StatsName))):
        os.makedirs(os.path.join(out_folder, StatsName))
    out_raw_ahd_file_name = os.path.join(out_folder, nonNumName , out_prefix + "_AHDCODE")
    out_raw_ahd_file = file(out_raw_ahd_file_name, 'w')
    out_raw_lines = []

    filterRe = re.compile('ahd\..*')
    if specifyAhd is not None:
        filterRe = re.compile(specifyAhd)
    in_file_names = os.listdir(data_path)
    in_file_names = list(filter( lambda x: filterRe.match(x) is not None,  in_file_names))
    in_file_names = list(map(lambda p : os.path.join(data_path ,p) ,in_file_names))
    eprint("about to process", len(in_file_names), "files")
    for in_file_name in in_file_names:
        pracid = in_file_name[-5:]
        out_file_name = os.path.join( out_folder, resolvName , 'ahd.resolved.' + pracid)
        err_file_name = os.path.join( out_folder, StatsName  , 'ahd.resolve_err.' + pracid)
        eprint("reading from", in_file_name, "and writing to", out_file_name, err_file_name, out_raw_ahd_file_name)
        
        out_file = file(out_file_name, 'w')
        err_file = file(err_file_name, 'w')
        
        stats = {"unknown_id": 0,\
            "unknown_unit": defaultdict(int), "empty_num_result": defaultdict(int), 
            "invalid_num_result": defaultdict(int),
            "processed": defaultdict(int),
            "unknown_medcode": defaultdict(int), "bad_ahdflag": 0, "read": 0, "wrote_numeric": 0, "wrote_non_numeric": 0}
        out_data = []
        writeLines = []
        for l in file(in_file_name):
            stats["read"] += 1
            patid, eventdate, ahdcode, ahdflag, data1, data2, data3, data4, data5, data6, medcode = parse_ahd_line(l)
            combid = pracid + patid
            if combid not in id2nr:
                #eprint("unknown combid [%s]" % combid)
                stats["unknown_id"] += 1
                continue
            if ahdflag != 'Y':
                stats["bad_ahdflag"] += 1
                continue 
            if medcode not in ahd_read_codes:
                stats["unknown_medcode"][medcode] += 1
                continue
            def get_full_ahd_name(medcode, ahdcode):
                full_ahd_name = ahd_read_codes[medcode] + '-' + medcode + '_' + ahd_codes[ahdcode]["desc"] + '-' + ahdcode
                full_ahd_name = full_ahd_name.replace('/', '_Over_').replace(':', '-').replace(' ', '_').replace('>', 'GreaterThan').replace('<', 'LessThan')
                return full_ahd_name
            if ahdcode in ahd_codes and ahd_codes[ahdcode]["data2"] == "NUM_RESULT" and ahd_codes[ahdcode]["datafile"] == "TEST" :
                full_ahd_name = get_full_ahd_name(medcode, ahdcode)
                if data2 is None or data2 == '':
                    stats["empty_num_result"][full_ahd_name] += 1
                    continue
                if not is_number(data2) :
                    stats["invalid_num_result"][full_ahd_name] += 1
                    continue
                if data3 not in ahd_lookups:
                    stats["unknown_unit"][(full_ahd_name, data3)] += 1
                    continue
                stats["processed"][full_ahd_name] += 1        
                units = ahd_lookups[data3]
                stats["wrote_numeric"] += 1
                l = [id2nr[combid], full_ahd_name, eventdate, data2, units]
                writeLines.append("\t".join(map(str,l)) + '\n')
                #print("\t".join(map(str,l)), file=out_file)
            elif ahdcode in ['1001400217', '1001400156'] : #RBC red blood cell size and Immunoglobulin are specified as START_RNGE, END_RNGE
                full_ahd_name = get_full_ahd_name(medcode, ahdcode)
                if not is_number(data5) or not is_number(data6):
                    stats["invalid_num_result"][full_ahd_name] += 1
                    continue            
                stats["processed"][full_ahd_name] += 1
                stats["wrote_numeric"] += 2
                l = [id2nr[combid], "start_"+full_ahd_name, eventdate, data5, "NA"]
                writeLines.append("\t".join(map(str,l)) + '\n')
                #print("\t".join(map(str,l)), file=out_file)
                l = [id2nr[combid], "end_"+full_ahd_name, eventdate, data6, "NA"]
                writeLines.append("\t".join(map(str,l)) + '\n')
                #print("\t".join(map(str,l)), file=out_file)
            else:
                stats["wrote_non_numeric"] += 1
                out_data.append([id2nr[combid], "MEDCODE", eventdate, medcode])
        out_file.writelines(writeLines)
        out_file.close()
        out_data.sort()
        for l in out_data:
            out_raw_lines.append("\t".join(map(str,l)) + '\n')
            #print("\t".join(map(str,l)), file=out_raw_ahd_file) 
        out_raw_ahd_file.writelines(out_raw_lines)
        err_file = file(err_file_name, 'w')
        write_stats(stats, pracid, err_file)
    out_raw_ahd_file.close()


def createCommonValsFromSum(filterCnt = 0):
    cfg = Configuration()
    work_path = fixOS(cfg.work_path)
    counts = dict()
    counts_non_zero = dict()
    stats = 0
    
    allFiles = os.listdir(work_path)
    rValStats = re.compile('^ValueStats_.', re.IGNORECASE)

    lines = []
    for f in allFiles:
        if rValStats.match(f) is not None:
            fp = open(os.path.join(work_path, f), 'r')
            ln = fp.readlines()
            fp.close()
            for l in ln:
                lines.append(l)
            
    for l in lines:
        ahdcode, count, count_non_zero = map(lambda x : x.strip(), l.split('\t'))
    
        if ahdcode is None or count is None or count_non_zero is None:
            raise NameError('parse error')
        stats += 1
        if counts.get(ahdcode) is None:
            counts[ahdcode] = 0
        if counts_non_zero.get(ahdcode) is None:
            counts_non_zero[ahdcode] = 0
        counts[ahdcode] = counts[ahdcode] + int(count)
        counts_non_zero[ahdcode] =counts_non_zero[ahdcode] + int(count_non_zero)

    lines = []
    for k, v in counts.items():
        if filterCnt > 0 and counts_non_zero[k] < filterCnt:
            continue
        line ="\t".join([k, str(v), str(counts_non_zero[k])]) + '\n'
        lines.append(line)
    fw = open(os.path.join(work_path, 'CommonValues'), 'w')
    fw.writelines(lines)
    fw.close()
        
    eprint("processed", str(stats), "records")

def fixAhdName(ahdCode):
    return ahdCode.replace('?','_Q_').replace('/','_over_').replace('*','_ast_').replace('"', '')

#instead of running  up command that uses summery:
def createCommonVals(filterCnt = 0, createCommonDir = True):
    cfg = Configuration()
    work_path = fixOS(cfg.work_path)
    counts = dict()
    counts_non_zero = dict()
    stats = 0

    commonDir = os.path.join(work_path, 'Common')
    if not(os.path.exists(commonDir)):
        os.makedirs(commonDir)
        
    ResolvedFld = os.path.join(work_path, 'Resolved')
    rPrac = re.compile('ahd\.resolved\..*', re.IGNORECASE)
    ahd_files = os.listdir(ResolvedFld)
    fileCnt = len(list(filter( lambda x: rPrac.match(x) is not None ,ahd_files)))
    eprint('About to proccess %d ahd files'%fileCnt)
    for in_filename in ahd_files:
        pracid = in_filename[-5:]
        if rPrac.match(in_filename) is not None:
            stats += 1
            if stats % 10 == 0:
                eprint('Done Proccess %d files (out of %d)'%(stats, fileCnt))
            fp = open( os.path.join( ResolvedFld, in_filename), 'r')
            l = fp.readline()
            linePerFile = dict()
            while (l is not None and len(l) > 0):
                patid, ahdcode, eventdate, the_value, unit = map(lambda x : x.strip(), l.split('\t'))
                ahdcode = fixAhdName(ahdcode)
                the_value = float(the_value)
                if counts.get(ahdcode) is None:
                    counts[ahdcode] = 0
                if counts_non_zero.get(ahdcode) is None:
                    counts_non_zero[ahdcode] = 0
                counts[ahdcode]+= 1
                if the_value != 0.0:
                    counts_non_zero[ahdcode]+= 1

                if createCommonDir:
                    line = "\t".join([patid, eventdate, str(the_value), unit]) + '\n'
                    if linePerFile.get(ahdcode) is None:
                        linePerFile[ahdcode] = list()
                    linePerFile[ahdcode].append(line)
                l = fp.readline()
            if createCommonDir:
                for ahdcode, allLines in linePerFile.items():
                    ahdcode_to_file = open(os.path.join(commonDir, ahdcode), 'a')
                    ahdcode_to_file.writelines(allLines)
                    ahdcode_to_file.close()
            fp.close()
                
    lines = []
    for k, v in counts.items():
        if filterCnt > 0 and counts_non_zero[k] < filterCnt:
            continue
        line ="\t".join([k, str(v), str(counts_non_zero[k])]) + '\n'
        lines.append(line)
    fw = open(os.path.join(work_path, 'CommonValues'), 'w')
    fw.writelines(lines)
    fw.close()
        
    eprint("processed", str(stats), "records")

def saveUnitsForAllSignals():
    allsignals = listAllTargets()
    allsignals = list(filter(lambda sig: sig!= 'NULL' and sig != 'TBD' ,allsignals))
    for signalName in allsignals:
        saveUnitsForSignal(signalName)

#regex is ahdcode or readcode to search for in ahd.*
def loadSpecificSignal(signalRegex= '.', col = 2):
    col = col - 1
    cfg = Configuration()
    raw_path = fixOS(cfg.doc_source_path)
    data_path = fixOS(cfg.raw_source_path)
    out_folder = fixOS(cfg.work_path)
    resolvName = 'Resolved'
    if not(os.path.exists(raw_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not(os.path.exists(data_path)):
        raise NameError('config error - raw_path don''t exists')
    if not(os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')

    StatsName= 'Stats'
    resolvName= 'Resolved'
    nonNumericName = 'NonNumeric'
    commonFld = 'Common'
    if not(os.path.exists(os.path.join(out_folder, nonNumericName))):
        os.makedirs(os.path.join(out_folder, nonNumericName))
    if not(os.path.exists(os.path.join(out_folder, StatsName))):
        os.makedirs(os.path.join(out_folder, StatsName))
    if not(os.path.exists(os.path.join(out_folder, resolvName))):
        os.makedirs(os.path.join(out_folder, resolvName))
    if not(os.path.exists(os.path.join(out_folder, commonFld))):
        os.makedirs(os.path.join(out_folder, commonFld))

    counts = dict()
    counts_non_zero = dict()
    ahd_code_name = list(filter(lambda f: f.startswith('AHDCodes') ,os.listdir(raw_path)))
    if len(ahd_code_name) != 1:
        raise NameError('coudn''t find AHDlookup')
    ahd_code_name = ahd_code_name[0]
    readcodes_name = list(filter(lambda f: f.startswith('Readcodes') ,os.listdir(raw_path)))
    if len(readcodes_name) != 1:
        raise NameError('coudn''t find readcodes_name')
    readcodes_name = readcodes_name[0]
    lines = getLines(raw_path, ahd_code_name)
    ahd_codes = read_ahd_codes(lines)
    lines = getLines(raw_path, readcodes_name)
    ahd_read_codes = read_ahd_read_codes(lines)

    sigRe = re.compile(signalRegex)
    filterRe = re.compile('ahd\..*')
    in_file_names = os.listdir(data_path)
    in_file_names = list(filter( lambda x: filterRe.match(x) is not None,  in_file_names))
    in_file_names = list(map(lambda p : os.path.join(data_path ,p) ,in_file_names))

    
    nonNum_dir = os.path.join(out_folder, nonNumericName)
    err_file_name = os.path.join(out_folder, StatsName)
    stats_file = open(os.path.join(err_file_name, 'all.stats'), 'w')
    sum_file_path = os.path.join(nonNum_dir, 'AHDCODE')
    sum_file = open(sum_file_path,'w')
    #out_raw_lines = []
    #error_file = open(err_raw_ahd_file_name, 'w')

    create_id2nr()
    lines = getLines(out_folder, 'ID2NR')
    id2nr = read_id2nr(lines)
    
    eprint("about to process", len(in_file_names), "files")
    first_procc = dict()
    for in_file_name in in_file_names:
        pracid = in_file_name[-5:]
        #out_file_name = os.path.join( out_folder, resolvName , 'ahd.resolved.' + pracid)
        #err_file_name = os.path.join( out_folder, StatsName  , 'ahd.resolve_err.' + pracid)
        eprint("reading from", in_file_name)
        
        stats = {"empty_num_result": 0, "invalid_num_result": 0, "bad_ahdflag": 0, "processed": 0, "read": 0, "wrote_numeric": 0, "wrote_non_numeric": 0, 'unknown_id': 0}
        out_data = dict()
        writeLines = []
        writeLineCommon = dict()
        for l in open(in_file_name):
            stats["read"] += 1
            patid, eventdate, ahdcode, ahdflag, data1, data2, data3, data4, data5, data6, medcode = parse_ahd_line(l)
            data = [data1, data2, data3, data4, data5, data6]
            combid = pracid + patid
            if ahdflag != 'Y':
                stats["bad_ahdflag"] += 1
                continue
            if id2nr.get(combid) is None:
                stats["unknown_id"] += 1
                continue
            if sigRe.match(medcode) is None and sigRe.match(ahdcode) is None:
                continue
            def get_full_ahd_name(medcode, ahdcode):
                m1 = ahd_read_codes.get(medcode)
                if m1 is None:
                    m1 = ''
                m2 = ahd_codes.get(ahdcode)
                if m2 is None:
                    m2 = ''
                else:
                    m2 = m2['desc']
                full_ahd_name = m1 + '-' + medcode + '_' + m2 + '-' + ahdcode
                full_ahd_name = full_ahd_name.replace('/', '_Over_').replace(':', '-').replace(' ', '_').replace('>', 'GreaterThan').replace('<', 'LessThan').replace('"', '')
                return full_ahd_name
            if ahd_codes.get(ahdcode) is not None and (ahd_codes[ahdcode]["data%d"%(col+1)] == "NUM_RESULT" or is_number(data[col]) ):
                full_ahd_name = get_full_ahd_name(medcode, ahdcode)
                if data[col] is None or data[col] == '':
                    stats["empty_num_result"] += 1
                    continue
                if not is_number(data[col]) :
                    stats["invalid_num_result"] += 1
                    continue
                stats["processed"] += 1
                stats["wrote_numeric"] += 1
                l = [id2nr[combid], full_ahd_name, eventdate, data[col], data3]
                l2 = [id2nr[combid], eventdate, data[col], data3, full_ahd_name]
                writeLines.append("\t".join(map(str,l)) + '\n')
                if writeLineCommon.get(full_ahd_name) is None:
                    writeLineCommon[full_ahd_name] = []
                    if first_procc.get(full_ahd_name) is None:
                        commonPath = os.path.join(out_folder,commonFld,full_ahd_name) #open first time- reset file
                        out_united = open(commonPath, 'w')
                        out_united.close()
                        first_procc[full_ahd_name] = True
                    
                writeLineCommon[full_ahd_name].append("\t".join(map(str,l2)) + '\n')
                #print("\t".join(map(str,l)), file=out_file)
                if counts.get(full_ahd_name) is None:
                    counts[full_ahd_name] = 0
                if counts_non_zero.get(full_ahd_name) is None:
                    counts_non_zero[full_ahd_name] = 0
                counts[full_ahd_name]+= 1
                if is_number(data[col]) and float(data[col]) != 0.0:
                    counts_non_zero[full_ahd_name]+= 1
            else:
                if (len(data1) ==0 and len(data2)==0 and len(data3)==0 and len(data4)==0 and len(data5)==0 and len(data6)==0) and len(medcode) == 0:
                    stats["empty_num_result"] += 1
                    continue
                stats["wrote_non_numeric"] += 1
                full_ahd_name = get_full_ahd_name(medcode, ahdcode)
                if out_data.get(full_ahd_name) is None:
                    out_data[full_ahd_name] = []
                out_data[full_ahd_name].append([id2nr[combid], ahdcode, eventdate, medcode, data1, data2, data3, data4, data5, data6])
        #out_file = open(out_file_name, 'w')
        #out_file.writelines(writeLines)
        for full_ahd_name, writeLns in writeLineCommon.items():
            commonPath = os.path.join(out_folder,commonFld,full_ahd_name)
            out_united = open(commonPath, 'a')
            out_united.writelines(writeLns)
            out_united.close()
        #out_file.close()
        #out_data.sort()
        
        for full_ahd_name, objList in out_data.items():
            nonNumPath = os.path.join(nonNum_dir,full_ahd_name)
            out_united = open(nonNumPath, 'a')
            writeLns = list(map(lambda row: "\t".join(map(str,row)) + '\n', objList))
            out_united.writelines(writeLns)
            out_united.close()
            sum_file.writelines(list(map(lambda ln: reform_line(ln) ,writeLns)))
            
            #out_raw_lines.append("\t".join(map(str,l)) + '\n')
            #print("\t".join(map(str,l)), file=out_raw_ahd_file)
        #error_file.writelines(out_raw_lines)
        #stats_file = open(os.path.join( err_file_name, '%s.stats'%pracid), 'w')
        write_stats(stats, pracid, stats_file)
        
    #error_file.close()
    #out_united.close()
    stats_file.close()
    sum_file.close()
    lines = []
    filterCnt = 0
    if os.path.exists(os.path.join(out_folder, 'CommonValues')):
        old_lines = getLines(out_folder, 'CommonValues')
        for l in old_lines:
            if len(l.strip()) == 0:
                continue
            tokens = l.strip().split('\t')
            if len(tokens) != 3:
                raise NameError('Format Error in CommonVaules. Lines:\n%s'%l)
            if counts.get(tokens[0]) is None: #save it if not exists now. if exists will be override
                counts[tokens[0]] = int(tokens[1])
                counts_non_zero[tokens[0]] = int(tokens[2])
    for k, v in counts.items():
        if filterCnt > 0 and counts_non_zero[k] < filterCnt:
            continue
        line ="\t".join([k, str(v), str(counts_non_zero[k])]) + '\n'
        lines.append(line)
    fw = open(os.path.join(out_folder, 'CommonValues'), 'w')
    fw.writelines(lines)
    fw.close()

def reform_line(line):
    tokens = line.strip().split('\t')
    #From [id2nr[combid], ahdcode, eventdate, medcode, data1, data2, data3, data4, data5, data6]
    #To [id2nr[combid], "MEDCODE", eventdate, medcode]
    line = '\t'.join([tokens[0], 'MEDCODE', tokens[2], tokens[3]]) + '\n'
    return line

def createNonNumericAHD():
    cfg = Configuration()
    raw_path = fixOS(cfg.doc_source_path)
    data_path = fixOS(cfg.raw_source_path)
    out_folder = fixOS(cfg.work_path)
    
    if not(os.path.exists(raw_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not(os.path.exists(data_path)):
        raise NameError('config error - raw_path don''t exists')
    if not(os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')

    nonNumericName = 'NonNumeric'
    nonNum_dir = os.path.join(out_folder, nonNumericName)
    if not(os.path.exists(nonNum_dir)):
        raise NameError('most run after NonNumeric Done')

    out_file = os.path.join(nonNum_dir, 'AHDCODE')
    fw = open(out_file,'w')
    in_file_names = list(filter(lambda f: f!='AHDCODE' ,os.listdir(nonNum_dir)))
    done_cnt = 0
    for in_file_name in in_file_names:
        try:
            lines = getLines(nonNum_dir, in_file_name)
            lines = list(map(lambda line: reform_line(line) ,lines))
            fw.writelines(lines)
        except:
            eprint('Error In File %s'%in_file_name)
            traceback.print_exc()
            raise
        done_cnt += 1
        if done_cnt % 200 == 0:
            print('Done %d out of %d'%(done_cnt, len(in_file_names)))
    fw.close()

def reformat_train(line):
    tokens = line.strip().split('\t')
    return '%s\tTRAIN\t%s\n'%(tokens[0], tokens[1])

def add_train_censor(train_old_rep = None):
    #1-70, 2- 20, 3 - 10
    cl_ratio = dict()
    cl_ratio[1] = 0.7
    cl_ratio[2] = 0.2
    cl_ratio[3] = 0.1
    
    cfg = Configuration()
    pid_new_path = os.path.join(fixOS(cfg.work_path), 'demo')
    lines = getLines(pid_new_path, 'byears')
    pids_new = list(set(map(lambda ln : ln.split(' ')[0] ,lines)))
    print('done reading %d pids'%(len(pids_new)))

    pids_old = set()
    output_path = fixOS(cfg.output_path)
    if not(os.path.exists(output_path)):
        os.makedirs(output_path)
    full_temp_path = os.path.join(output_path, 'old_rep_train.pids')
    if train_old_rep is not None:
        cmd = '%s --rep %s --sig_print --output raw --bin_method "split_method=same_width;binCnt=0" --sig TRAIN --f_output %s'%(cfg.flow_app, train_old_rep, full_temp_path)
        if not(os.path.exists(full_temp_path)):
            print('Running Flow')
            subprocess.call(cmd, shell= True)
        else:
            print('skiping flow - train already exists')
        if not(os.path.exists(full_temp_path)):
            raise NameError('Flow Faild\n%s'%cmd)
        fp = open(full_temp_path,'r')
        lines = fp.readlines()
        fp.close()
        lines = lines[1:]
        pids_old = set(map(lambda ln : ln.split('\t')[0] ,lines))

    pids_to_add = list(filter(lambda pid: pid not in pids_old,pids_new))
    print('Will add %d, has %d'%(len(pids_to_add), len(pids_old)))
    random.shuffle(pids_to_add)
    final_train = []
    if len(pids_old) > 0:
        final_train = lines
        
    final_counts = dict()
    last_val = None
    tot_sum = 0
    for val, ratio in cl_ratio.items():
        last_val = val
        final_counts[val] = round(ratio * len(pids_to_add))
        tot_sum += final_counts[val]
    final_counts[last_val] = len(pids_to_add) - (tot_sum-final_counts[last_val]) #keep only what's left
    assign_val_pids = dict()
    last_pos = 0 
    for val, cnt in final_counts.items():
        end_pos = last_pos+cnt
        print('value=%d, poses=[%d, %d] size=%d'%(val, last_pos, end_pos, len(pids_to_add)))
        pid_list  = pids_to_add[int(last_pos):int(end_pos)]
        assign_val_pids[val] = pid_list
        last_pos += cnt 

    for val, pids_list in assign_val_pids.items():
        addition = list(map(lambda pid : '%s\t%d'%(pid, val) ,pids_list))
        final_train += addition

    lines = list(map(lambda ln: reformat_train(ln), final_train))
    lines.sort(key = lambda ln: int(ln.split('\t')[0]))
    fw = open(os.path.join(pid_new_path, 'TRAIN'), 'w')
    fw.writelines(lines)
    fw.close()

def add_splits(old_splits = None, n_split = 6):
    cfg = Configuration()
    pid_new_path = os.path.join(fixOS(cfg.work_path), 'demo')
    pid_to_split = dict()
    if old_splits is not None:
        fp = open(old_splits, 'r')
        lines = fp.readlines()
        fp.close()
        n_split = int(lines[0].split('\t')[1]) # take from old file
        lines = lines[1:]
        for line in lines:
            pid,split = line.split('\t')
            pid = int(pid)
            split = int(split)
            if split >= n_split:
                raise NameError('Got line %s\nwhen n_split is %d'%(line, n_split))
            pid_to_split[pid] = split

    lines = getLines(pid_new_path, 'byears')
    pids_new = list(set(map(lambda ln : int(ln.split(' ')[0]) ,lines)))
    print('done reading %d pids'%(len(pids_new)))
    pids_new = list(filter(lambda p : p not in pid_to_split ,pids_new)) #filter already splited pids:
    split_sz = round(len(pids_new) / float(n_split))
    last_split_size = len(pids_new)  - ((n_split -1) * split_sz)
    print('Will split %d pids. split_size is %d, last_split_size is %d'%(len(pids_new), split_sz, last_split_size))
    random.shuffle(pids_new)
    last_pos = 0
    for i_split in range(n_split-1):
        end_pos = last_pos+split_sz
        for p in pids_new[int(last_pos):int(end_pos)]:
            pid_to_split[p] = i_split
        last_pos += split_sz
    for p in pids_new[int(last_pos):]:
        pid_to_split[p] = n_split-1

    lines = list(map(lambda kv : '%d\t%d\n'%(kv[0], kv[1]) ,pid_to_split.items()))
    lines =  ['NSPLITS\t%d\n'%n_split] + lines
    fw = open(os.path.join(pid_new_path, 'splits%d.thin'%n_split), 'w')
    fw.writelines(lines)
    fw.close()

def get_if_exists(d, key, onlyExists = False):
    if d.get(key) is not None:
        return d[key]
    if len(key) == 0:
        return 'None'
    if onlyExists:
        return 'None'
    return key

def load_hospitalizations():
    cfg = Configuration()
    primary_convert = { 'X - Ray':'X-Ray', 'General Surgical':'General Surgery', 'Ear| Nose and Throat':'Ear Nose & Throat'}
    sec_convert = {}
    doc_path = fixOS(cfg.doc_source_path)
    work_path = fixOS(cfg.work_path)
    dict_name = list(filter(lambda f: f.startswith('NHSspeciality') ,os.listdir(doc_path)))
    if len(dict_name)!= 1:
        raise NameError('couldn''t find NHSspeciality')
    dict_name = dict_name[0]
    lines = getLines(doc_path, dict_name)
    tokens = list(map(lambda line: [line[:3], get_if_exists(primary_convert, line[3:33].strip()).replace(' ', '_'),
                                    get_if_exists(sec_convert,line[33:].strip()).replace(' ', '_')],lines))
    code2primary = dict()
    code2secondry = dict()
    stats = {"bad_code": 0, "Hospitalization": 0, "Treatment_Department": 0}
    for code, primary, secondry in tokens:
        code2primary[code] = primary
        code2secondry[code] = secondry
    lines = getLines(os.path.join( work_path, 'medical'), 'NHSSPEC')
    new_lines = list()
    seen_comb = set()
    for line in lines:
        pid, tmp, sig_date, code, status = line.split('\t') #status in ['INPATIENT', 'OUTPATIENT', 'DAY_CASE']
        sig_name = 'Hospitalization'
        if status.strip()!='INPATIENT':
            sig_name = 'Treatment_Department'
        if pid + sig_date + code not in seen_comb:
            if code in code2primary:
                seen_comb.add(pid + sig_date + code)
                new_lines.append([int(pid), sig_name, sig_date, '%s@%s'%(get_if_exists(code2primary ,code), get_if_exists(code2secondry ,code)) ])
                stats[sig_name] += 1
            else:
                stats['bad_code'] += 1
    new_lines = list(new_lines)
    new_lines.sort()
    
    lines = list(map(lambda grp: unicode('\t'.join(map(str,grp)) + '\n') ,new_lines))
    fw = io.open(os.path.join( work_path, 'medical', 'Hospitalization'), 'w', newline='')
    fw.writelines(lines)
    fw.close()
    stat_file = open(os.path.join(work_path, 'medical', 'hosp.stats'), 'w')
    write_stats(stats, 'all', stat_file)

if __name__ == "__main__":
    createResolveFld()
    createCommonVals()
    addMissingSignals()
    saveUnitsForAllSignals()
    