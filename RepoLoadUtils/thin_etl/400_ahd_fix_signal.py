from __future__ import print_function
from collections import defaultdict
import sys
import argparse
import glob
import os
from os.path import join
from math import exp, log
from scipy.stats import norm
from get_moments import get_moments, moments_to_str

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def eprint_also_to_file(f, l):	  
	print("\t".join(map(str, l)), file=sys.stderr)
	print("\t".join(map(str, l)), file=f)

parser = argparse.ArgumentParser()
parser.add_argument('--in_unit_instructions_file', default='/server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/Instructions.txt', 
					type=argparse.FileType('r'))
parser.add_argument('--in_unit_translation_file', default='/server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/unitTranslator.txt', 
					type=argparse.FileType('r'))
parser.add_argument('--in_ahd_code_dependent_translation_file', default='/server/UsersData/ido/MR/Tools/RepoLoadUtils/thin_etl/codesDependency', 
					type=argparse.FileType('r'))
parser.add_argument('--in_signal_files', required=True)
parser.add_argument('--out_fixed_folder', required=True)
parser.add_argument('--out_stats_prefix', required=True)
args = parser.parse_args()

def clean_and_strip(x):
	return x.strip()

def read_instructions():
	'''Instructions file per signal - how to translate'''
	unit_instruction = {}
	args.in_unit_instructions_file.readline()
	for l in args.in_unit_instructions_file.readlines():
		a = map(clean_and_strip, l.split('\t'))
		b = [None] * 6 # sometimes the instructions line is shorter/longer than 6
		for i,v in enumerate(a[:6]):
			b[i] = a[i]
		signal,unit,resolution,ignore,factors,final_factor = b
		if resolution == "1":
			resolution = "{:.0f}"
		elif resolution == "0.1":
			resolution = "{:.1f}"
		elif resolution == "0.01":
			resolution = "{:.2f}"
		else:
			raise ValueError("unknown resolution: " + resolution)
		if final_factor is None or final_factor == '':
			final_factor = 1.0
		else:
			final_factor = float(final_factor)
		if ignore is not None:	  
			ignore = set(ignore.split(','))
		else:
			ignore = set([])
		if factors is not None and len(factors.strip()) > 0:
			factors = map(float, factors.strip().split(','))
		else:
			factors = []
					
		unit_instruction[signal] = {"base_unit": unit, "resolution": resolution, "ignore": ignore,
						 "factors": factors, "final_factor": final_factor, "translate": {}}
		eprint(signal, unit_instruction[signal])

	return unit_instruction
	
unit_instruction = read_instructions()
eprint("found", len(unit_instruction), "unit instructions")


def read_unit_translation(unit_instruction):
	'''Per unit translation instructions - 1-to-many with instructions file'''
	i = 0
	for l in args.in_unit_translation_file:
		signal,unit,factor = map(clean_and_strip, l.split('\t'))
		unit_instruction[signal]["translate"][unit] = factor
		i += 1
	eprint("found", i, "unit translations")
read_unit_translation(unit_instruction)

def read_code_dependent():
	'''Most translation are done in the unit level, however this file provides workarounds for specific read codes, 
	we convert them to other units as they need special treatment'''	
	ahd_code_dependent_translation = defaultdict(lambda : defaultdict(str))
	for l in args.in_ahd_code_dependent_translation_file.readlines():
		signal, in_unit, ahd_code, out_unit = map(clean_and_strip, l.split('\t'))
		ahd_code_dependent_translation[(signal, in_unit)][ahd_code] = out_unit
	return ahd_code_dependent_translation 
	
ahd_code_dependent_translation = read_code_dependent()	  
eprint("found", len(ahd_code_dependent_translation), "code dependent translations")

def translate(data, translator):
	if translator == "Formula1":
		return map(lambda x: 100.0/x if x != 0.0 else -1.0, data)
	if translator == "Formula2":
		return map(lambda x: 0.09148 * x + 2.152, data)
	return map(lambda x: float(translator) * x, data)
   

def estimate_prior(data, factors, sk, moments):
	'''First we do a rough estimates of how many values need fixing, by checking to which gaussian they belong'''
	cnt_change = 0
	for x in data:			  
		z = (x - moments["mean_clean"])/moments["std_clean"]
		d = z*z - sk*z
		for f in factors:
			nz = (x*f - moments["mean_clean"])/moments["std_clean"]
			nd = nz*nz - sk*nz
			if nd < d:
				cnt_change += 1
	return 1.0*cnt_change/len(data)


pdf_cache = {}
def cached_norm_pdf(z):
	if z not in pdf_cache:
		pdf_cache[z] = norm.pdf(z)
	return pdf_cache[z]
	
cdf_cache = {}
def cached_norm_cdf(z):
	if z not in cdf_cache:
		cdf_cache[z] = norm.cdf(z)
	return cdf_cache[z]
	
def fix_factors(data, signal, unit, factors, out_file_fixed, out_file_stats, base_unit_moments=None):
	'''For each value check if fixing it by multiplying it in a factor makes it more likely'''	  
	changed = 1
	total_changed = 0
	while changed > 0:
		changed = 0
		if base_unit_moments is None: 
			moments = get_moments(data)
		else:
			moments = base_unit_moments
		abs_skew, sign_skew = abs(moments["skew_clean"]), 1 if moments["skew_clean"] > 0 else -1
		sk = sign_skew * exp(log(abs_skew)/3) # third-sqrt
		new_data = []
		prior = estimate_prior(data, factors, sk, moments)
		eprint_also_to_file(out_file_stats, [signal, unit, str(len(data)), "prior estimation - ratio of data to be fixed", str(prior)])		   
		for x in data:
			optimal = 1.0
			if x > 0.0: # -1.0 means not valid, leave it like that
				z = (x - moments["mean_clean"])/moments["std_clean"]
				prob = 2*cached_norm_pdf(z)*cached_norm_cdf(sk*z)
				for f in factors:
					nz = (x*f - moments["mean_clean"])/moments["std_clean"]
					nprob = 2*cached_norm_pdf(nz)*cached_norm_cdf(sk*nz)*prior
					if nprob > prob:
						print("%f [%s]:: at factor: %f has better probability" % (x, unit, f) , prob,"<", nprob , "fixing!", file=out_file_fixed)
						optimal = f
			if optimal != 1.0:
				changed += 1				
			new_data.append(optimal*x)
		data = new_data
		total_changed += changed
		eprint("changed %d values out of %d" % (total_changed, len(data))) 
		if base_unit_moments is not None:
			# iterate only if this is the base unit
			return data
	return data


in_file_names = glob.glob(args.in_signal_files)
eprint("about to process", len(in_file_names), "files")
out_file_stats = open(args.out_stats_prefix + "_fix.stats", 'w')

# main loop
for in_filename in in_file_names:
	signal = os.path.basename(in_filename)
	
	
	eprint("processing %s, reading from %s", (signal, in_filename))
	if signal not in unit_instruction:
		num_lines = sum(1 for line in open(in_filename))
		eprint_also_to_file(out_file_stats, [signal, "ALL_UNITS", str(num_lines), "WARNING", "not found in the instructions, skipping"])
		continue
	my_instr = unit_instruction[signal]		   
	code_dependent_translation = defaultdict(int)	 
	ignored = defaultdict(int)	  
	data = defaultdict(list)
	metadata = defaultdict(list)
	for l in file(in_filename):		
		patid, eventdate, val, unit, source = l.strip().split('\t')
		patid = int(patid)
		val = float(val)
		if unit == "U/L": # U/L and IU/L are always the same
			unit = "IU/L" 
		if (signal, unit) in ahd_code_dependent_translation and source in ahd_code_dependent_translation[(signal, unit)]:
			code_dependent_translation[(source,unit)] += 1
			unit = ahd_code_dependent_translation[(signal, unit)][source]
		if unit == "null value" or unit in my_instr["ignore"]:
			ignored[unit] += 1
			continue
		data[unit].append(val)
		metadata[unit].append((patid, eventdate, source))
	for k,v in ignored.iteritems():
		eprint_also_to_file(out_file_stats, [signal, k, str(v), "IGNORED"])
	for k,v in code_dependent_translation.iteritems():
		eprint_also_to_file(out_file_stats, [signal, k, str(v), "CODE_DEPENDENT_TRANSLATION"])
	base_unit = my_instr["base_unit"]
	base_unit_cnt = len(data[base_unit])
	total_cnt = 0
	legit_base_unit = True
	for unit in data.keys():
		cnt = len(data[unit])
		if cnt > base_unit_cnt*10:
			eprint_also_to_file(out_file_stats, [signal, unit, cnt, "WARNING", "skipping signal as unit has more values than declared base unit", base_unit, base_unit_cnt])
			legit_base_unit = False
			break
		total_cnt += cnt
	if not legit_base_unit:
		continue
	if total_cnt == 0:
		eprint_also_to_file(out_file_stats, [signal, "ALL_UNITS", 0, "WARNING", "skipping signal as it has no records"])			   
		continue	
	eprint("signal [%s]: about to process %d records" %(signal, total_cnt))
	
	
	eprint("handling base_unit: %s" % base_unit)
	if len(my_instr["factors"]) > 0:
		out_file_fixed = open(args.out_stats_prefix + "_" + signal + "_fix.list" , 'w')
		data[base_unit] = fix_factors(data[base_unit], signal, base_unit, my_instr["factors"], out_file_fixed, out_file_stats)	  
	base_unit_moments = get_moments(data[base_unit])
	
	eprint("handling all other units")
	for unit in sorted(data.keys()):
		if unit == base_unit:
			continue
		eprint("handling %s" % unit)
		if unit not in my_instr["translate"]:
			pct_of_base = 1.0 * len(data[unit])/base_unit_cnt
			if pct_of_base < 0.05:
				eprint_also_to_file(out_file_stats, [signal, unit, str(len(data[unit])), "WARNING", "not in translation table, but its ok as it is only [%f] from [%s]" %
				(pct_of_base, base_unit)])
				continue
			else:
				eprint("ERROR : %s : Cannot translate [%s], which stands for [%f] from [%s]" % (signal, unit, pct_of_base, base_unit))
				raise Exception
		data[unit] = translate(data[unit], my_instr["translate"][unit])
		if len(my_instr["factors"]) > 0:
			data[unit] = fix_factors(data[unit], signal, unit, my_instr["factors"], out_file_fixed, out_file_stats, base_unit_moments)		  
		eprint("completed translating and fixing: %s with %d records" % (unit, len(data[unit])))

	out_filename = join(args.out_fixed_folder, signal)
	eprint("fixing resolution to", my_instr["resolution"], "and multiplying by final_factor", my_instr["final_factor"])
	eprint("about to write %s" % out_filename)
	out_data = []
	for unit in sorted(data.keys()):
		vals = []
		for i,x in enumerate(data[unit]):
			if float(x) < 0.0:
				continue
			v = float(my_instr["resolution"].format(x))*my_instr["final_factor"]
			vals.append(v)			  
			out_data.append([metadata[unit][i][0], signal, metadata[unit][i][1], "{:.6f}".format(v), metadata[unit][i][2]])
		sta = [signal, unit, len(data[unit]), "OK", moments_to_str(get_moments(vals))]
		eprint_also_to_file(out_file_stats, sta)
	out_data.sort()
	o = open(out_filename, 'w')
	for l in out_data:
		print("\t".join(map(str,l)), file=o)
	
	
	
	
	
	