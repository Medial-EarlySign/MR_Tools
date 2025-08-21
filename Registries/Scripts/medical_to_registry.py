from __future__ import print_function
from Configuration import Configuration
import io, pandas as pd, os
from common import * 
import re

def date2num(d):
	return	int(d[0:4]) * 372 + int(d[4:6]) * 31 +	int(d[6:8]);

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
	eprint('reading medcode file', in_file)
	df = pd.read_csv(in_file, sep='\t')
	eprint(df.dtypes)
	def handle_rec(x):
		#global cnt, redundant
		#code, nrec, npat, desc, comment, status, type_field, organ = l.strip('\n').strip('\r').split('\t')		
		code = x["Read code"]
		d = {"desc": x["description"], "status": x["status 2016"], "type": x["type 2016"], "organ": x["organ 2016"], 
							"eff_readcode": code}
		exist_match = find_closest_match(code, codes)
		if exist_match is not None and compare_dicts(d, exist_match):
			eprint('WARNING: [%s]%s is redundant with: [%s]%s. both gets translated to [%s,%s,%s]' % (code, ahd_read_codes[code],
				   exist_match["eff_readcode"], exist_match["desc"], exist_match["status"], exist_match["type"], exist_match["organ"]), )
		# put only the interesting part without the 2 last chars and without the "." chars, e.g. 123
		code_as_parent = "".join([c for c in code[:5] if c != '.']) 
		if code_as_parent not in codes:
			codes[code_as_parent] = d.copy()
			codes[code_as_parent]["eff_readcode"] = code_as_parent
			
		# put the specific code, e.g. 123..00. This is done only for special cases where we would like to discern 123..00 and 123..11
		codes[code] = d
	df = df[~pd.isnull(df["status 2016"])]
	df.apply(handle_rec, axis = 1)
		
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


def load_registry():
	cfg = Configuration()
	out_folder = fixOS(cfg.work_path)
	raw_path = fixOS(cfg.doc_source_path)
	data_path = fixOS(cfg.raw_source_path)
	config_lists_folder = fixOS(cfg.config_lists_folder)
	readcodes_name = list(filter(lambda f: f.startswith('Readcodes') ,os.listdir(raw_path)))
	if len(readcodes_name) != 1:
		raise NameError('coudn''t find readcodes_name')
	readcodes_name = readcodes_name[0]
	lines = getLines(raw_path, readcodes_name)
	if not(os.path.exists(os.path.join( out_folder, 'registry'))):
		os.makedirs(os.path.join( out_folder, 'registry'))
	ahd_read_codes = read_ahd_read_codes(lines)
	
	icdo_2_desc = read_icdo_file(getLines(config_lists_folder ,'ICD-O'))
	codes_2_details = read_medcode_file(os.path.join(config_lists_folder, 'thin_cancer_medcodes_20170716_full_tree_fixed_freqs.txt'), ahd_read_codes)
	med2icd = read_medcode_2_icdo_file(getLines(config_lists_folder , 'medcode_2_icdo.txt'))
	translate_cancer_types_table = read_translate_cancer_types_file(getLines(config_lists_folder,'translate_cancer_types.txt'))
	

	#create_id2nr()
	lines = getLines(out_folder, 'ID2NR')
	id2nr = read_id2nr(lines)

	in_file_names = list(filter(lambda f: f.startswith('medical.') ,os.listdir(data_path)))
	eprint("about to process", len(in_file_names), "files")

	reg_file_name = os.path.join( out_folder, 'registry',  "REG")
	eprint("writing to %s" % (reg_file_name))
	stats_file_name = os.path.join( out_folder, 'registry',	 "reg_stats")
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
		
if __name__ == "__main__":	  # main loop
	#in order to run the script - use Configuration.py file and run load_registry()
	load_registry()