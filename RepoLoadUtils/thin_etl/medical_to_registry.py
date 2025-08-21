from __future__ import print_function
import glob, io
import argparse
from common import * 
import re

def date2num(d):
    return	int(d[0:4]) * 372 + int(d[4:6]) * 31 +  int(d[6:8]);

def read_icdo_file(in_file):
    codes = defaultdict(lambda: "")
    eprint('reading icdo file')
    for i, l in enumerate(in_file):
        code, status_type_organ = l.strip()[:4], l.strip()[4:]
        codes[code] = status_type_organ
    eprint("found", len(codes), "ICD-O codes")
    return codes

def find_closest_match(code, codes_2_details):
    for i in range(len(code), 0, -1):
        if code[:i] in codes_2_details:
            return codes_2_details[code[:i]]
    return None

def compare_dicts(d1, d2):
    return d1["status"] == d2["status"] and d1["type"] == d2["type"] and d1["organ"] == d2["organ"]
    
def read_medcode_file(in_file, ahd_read_codes):
    codes = {}
    eprint('reading medcode file')
    cnt, redundant = 0, 0
    for l in in_file:
        cnt+= 1
        try:
            code, nrec, npat, desc, comment, status, type_field, organ = l.strip('\n').strip('\r').split('\t')
        except:
            eprint("ERROR: can not parse: ", l, " in line", cnt)
            raise
            
        d = {"desc": desc, "status": status, "type": type_field, "organ": organ, "eff_readcode": code}
        exist_match = find_closest_match(code, codes)
        if exist_match is not None and compare_dicts(d, exist_match):
            eprint('WARNING: [%s]%s is redundant with: [%s]%s. both gets translated to [%s,%s,%s]' % (code, ahd_read_codes[code],
                   exist_match["eff_readcode"], exist_match["desc"], exist_match["status"], exist_match["type"], exist_match["organ"]), )
            redundant+= 1
        codes[code] = d
        code_as_parent = "".join([c for c in code[:5] if c != '.'])
        if code_as_parent not in codes:
            codes[code_as_parent] = d.copy()
            codes[code_as_parent]["eff_readcode"] = code_as_parent
                
    eprint("found", cnt, "THIN codes to detailed registry translations,", redundant, 
           "were redundant")
    return codes


def read_medcode_2_icdo_file(in_file):
    codes = defaultdict(lambda: "Cxxx") # for anything we don't know we return Cxxx
    eprint('reading medcode_2_icdo file')
    for i, l in enumerate(in_file):
        code, icdo = l.strip().split()
        codes[code] = icdo
    eprint("found", len(codes), "THIN codes to icdo translations")
    return codes


def read_translate_cancer_types_file(in_file):
    eprint('reading translate_cancer_types file')
    translate_cancer_types = []
    for i, l in enumerate(in_file):
        status_in	, type_in, organ_in, status_out, type_out, organ_out = l.strip().split('\t')
        translate_cancer_types.append({"in": (status_in	, type_in, organ_in), "out": (status_out, type_out, organ_out)})
    eprint("found", len(translate_cancer_types), "THIN translate_cancer_types records")
    return translate_cancer_types 


def translate_cancer_types(in_tuple, translate_cancer_types_table):
    for r in translate_cancer_types_table:
        m = [re.match(r["in"][i], in_tuple[i], re.IGNORECASE) for i in range(len(in_tuple))]
        if all(m):
            return r["out"]
    return in_tuple


    
def handle_single_pat(reg_file, combid, pat_recs, id2nr, codes_2_details, med2icd, icdo_2_desc, translate_cancer_types_table, ahd_read_codes):
    nr = id2nr[combid]
    pre_reg_recs = []
    for r in pat_recs:
        closest = find_closest_match(r["medcode"], codes_2_details)        
        if closest is not None:
            new_r = r.copy()
            new_r.update(closest)
            new_r["icdo"] = med2icd[r["medcode"]]
            new_r["icdo_desc"] = icdo_2_desc[new_r["icdo"]]
            pre_reg_recs.append(new_r)
    # determine anciliary or morphology cancer records that should be associated with more specific cancer records
    # morph would be skipped if (cancer - 2 < morph) ( morph happened approximately (+- 2 months) after the cancer )
    # also, if we decided that they're related, we can backdate cancer
    #eprint(combid, "pre_reg_recs", pre_reg_recs)            
    pre_reg_skip = set([])
    back_date = {}
    for morph in range(len(pre_reg_recs)):
        if pre_reg_recs[morph]["status"] not in ["anc", "morph"]:
            continue
        date_morph = date2num(pre_reg_recs[morph]["eventdate"])
        for cancer in range(len(pre_reg_recs)):            
            if morph == cancer or pre_reg_recs[cancer]["status"] != "cancer":
                continue
            date_cancer = date2num(pre_reg_recs[cancer]["eventdate"])
            if date_cancer - 62 <  date_morph:
                #eprint (combid, pre_reg_recs[morph]["eventdate"], ": morphology record is associated with cancer record", pre_reg_recs[cancer]["eventdate"], "and is skipped")
                pre_reg_skip.add(morph)
                if date_cancer - 62 < date_morph < date_cancer: 
                    #eprint (combid, pre_reg_recs[cancer]["eventdate"], ": cancer record is backdated to associated morphology record", pre_reg_recs[morph]["eventdate"])
                    back_date[cancer] = pre_reg_recs[morph]["eventdate"]
                break            
    #eprint("pre_reg_skip", pre_reg_skip)                
    for ind, r in enumerate(pre_reg_recs):
        if ind in pre_reg_skip:
            continue
        if r["status"] in ["ignore", "benign"]:
            continue
        if ind in back_date:
            r["eventdate"] = back_date[ind]
        in_cancer_type = (r["status"], r["type"], r["organ"])
        out_cancer_type = translate_cancer_types(in_cancer_type, translate_cancer_types_table)
        #eprint(in_cancer_type, out_cancer_type)
        s = "%d\t%s\t%s,%s,%s\t\t\t\tICDO[%s]:%s\tREADCODE[%s]:%s" % \
        (nr, r["eventdate"], out_cancer_type[0], out_cancer_type[1], out_cancer_type[2], r["icdo"], r["icdo_desc"], r["medcode"], ahd_read_codes[r["medcode"]])
        s_final_format = '%d\tREG\t%s\t%s'%(nr, r["eventdate"], ','.join(out_cancer_type[:3]))
        if r["eff_readcode"] != r["medcode"]:
            s += ", EFF_READCODE[%s]: %s" % (r["eff_readcode"], r["desc"])
        reg_file.append(s_final_format + '\n')	



if __name__ == "__main__":    # main loop
    code_folder = '/server/UsersData/ido/Medial/Projects/Utilities/ThinLoader/thin_etl/'
    parser = argparse.ArgumentParser()
    parser.add_argument('--in_AHDReadcodes_file', default='/server/Data/THIN1601/THINAncil1601/text/Readcodes1601.txt', type=argparse.FileType('r'))
    parser.add_argument('--in_medcode_file', default= code_folder + 'thin_cancer_medcodes_20161103.txt', type=argparse.FileType('r'))
    parser.add_argument('--in_medcode_2_icdo_file', default= code_folder + 'medcode_2_icdo.txt', type=argparse.FileType('r'))
    parser.add_argument('--in_icdo_description_file', default='/server/Work/Data/ICD-O/ICD-O', type=argparse.FileType('r'))
    parser.add_argument('--in_metastases_file', default= code_folder + 'translate_metastases.txt', type=argparse.FileType('r'))
    parser.add_argument('--in_translate_cancer_types', default=code_folder + 'translate_cancer_types.txt', type=argparse.FileType('r'))
    parser.add_argument('--in_ID2NR_file', required=True, type=argparse.FileType('r'))
    parser.add_argument('--in_medical_files', required=True)
    parser.add_argument('--out_registry_prefix', required=True)
    args = parser.parse_args()
    
    icdo_2_desc = read_icdo_file(args.in_icdo_description_file)
    ahd_read_codes = read_ahd_read_codes(args.in_AHDReadcodes_file)
    codes_2_details = read_medcode_file(args.in_medcode_file)
    med2icd = read_medcode_2_icdo_file(args.in_medcode_2_icdo_file)
    translate_cancer_types_table = read_translate_cancer_types_file(args.in_translate_cancer_types)
    id2nr = read_id2nr(args.in_ID2NR_file)
        
    in_file_names = glob.glob(args.in_medical_files)
    eprint("about to process", len(in_file_names), "files")

    reg_file_name = args.out_registry_prefix + "REG"
    eprint("writing to %s" % (reg_file_name))

    
    reg_lines = []
    for in_filename in in_file_names:
        pracid = in_filename[-5:]
        eprint("reading from %s, pracid = %s" % (in_filename, pracid))
        
        stats = {"unknown_id": 0, "invalid_medflag":0, "read": 0, "wrote": 0}

        prev_combid = -1
        pat_recs = []
        for l in file(in_filename):
            stats["read"] += 1
            patid, eventdate, enddate, datatype, medcode, medflag, staffid, source,\
            episode, nhsspec, locate, textid, category, priority, medinfo, inprac,\
            private, medid, consultid, sysdate, modified = parse_medical_line(l)

            if pracid + patid not in id2nr:
                stats["unknown_id"] += 1            
                continue
            combid = pracid + patid 
            if medflag not in ['R', 'S']:
                stats["invalid_medflag"] += 1
                continue
            if prev_combid != combid:
                if prev_combid != -1:
                    handle_single_pat(reg_lines, prev_combid, pat_recs, id2nr, codes_2_details, med2icd, icdo_2_desc, translate_cancer_types_table, ahd_read_codes)
                prev_combid = combid
                pat_recs = []
                
            pat_recs.append({"medcode": medcode, "eventdate": eventdate})       
     
    handle_single_pat(reg_lines, combid, pat_recs, id2nr, codes_2_details, med2icd, icdo_2_desc, translate_cancer_types_table, ahd_read_codes)
    reg_lines = sorted(reg_lines, key = lambda l : int(l.split('\t')[0]))
    reg_file = file(reg_file_name, 'w')
    reg_file.writelines(reg_lines)
    reg_file.close()


            
