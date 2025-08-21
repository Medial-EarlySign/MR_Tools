#!/usr/bin/python

from __future__ import print_function
from collections import defaultdict
import sys
import glob
import os, io, traceback
from os.path import join
from math import exp, log
from scipy.stats import norm
from get_moments import get_moments, moments_to_str
from common import *
from Configuration import Configuration
from fix_factors import fixFactorsMixtureGaussian

def eprint_also_to_file(f, l):    
    print("\t".join(map(str, l)), file=sys.stderr)
    print("\t".join(map(str, l)), file=f)

def fixSignal(signal, unit_instruction = None, ahd_code_dependent_translation = None, pdf_cache = {}, cdf_cache = {}):
    cfg = Configuration()
    united_file_Path = os.path.join( fixOS(cfg.work_path), 'United')
    out_fixed_folder = os.path.join(fixOS(cfg.work_path), 'Fixed')
    out_stats_folder = os.path.join(fixOS(cfg.work_path), 'Stats')
    if not(os.path.exists(out_fixed_folder)):
        os.makedirs(out_fixed_folder)
    if unit_instruction is None:
        unit_instruction = read_instructions()
        eprint("found", len(unit_instruction), "unit instructions")
        read_unit_translation(unit_instruction)
    if ahd_code_dependent_translation is None:
        ahd_code_dependent_translation = read_code_dependent()    
        eprint("found", len(ahd_code_dependent_translation), "code dependent translations")
    sigFileName = signal.replace('/','_over_')
    in_filename = os.path.join(united_file_Path, sigFileName)
    out_file_stats = open(os.path.join(out_stats_folder, sigFileName + "__fix.stats"), 'w')
    eprint("processing %s, reading from %s"%(signal, in_filename))
    if signal not in unit_instruction:
        num_lines = sum(1 for line in open(in_filename))
        eprint_also_to_file(out_file_stats, [signal, "ALL_UNITS", str(num_lines), "WARNING", "not found in the instructions, skipping"])
        return
    ahd_lookup = get_ahd_lookup()
    my_instr = unit_instruction[signal]
    eprint("my_instr", my_instr)    
    code_dependent_translation = defaultdict(int)    
    ignored = defaultdict(int)    
    data = defaultdict(list)
    metadata = defaultdict(list)
    for l in open(in_filename):     
        tokens = l.strip().split('\t')
        patid, eventdate, val, unit, source = tokens[:5]
        if ahd_lookup.get(unit) is not None:
            unit = ahd_lookup[unit]
        patid = int(patid)
        val = float(val)
        if (signal, unit) in ahd_code_dependent_translation and source in ahd_code_dependent_translation[(signal, unit)]:
            code_dependent_translation[(source,unit)] += 1
            unit = ahd_code_dependent_translation[(signal, unit)][source]
        if unit in my_instr["ignore"]:
            ignored[unit] += 1
            continue
        data[unit].append(val)
        metadata[unit].append((patid, eventdate, source))
    for k,v in ignored.items():
        eprint_also_to_file(out_file_stats, [signal, k, str(v), "IGNORED"])
    for k,v in code_dependent_translation.items():
        eprint_also_to_file(out_file_stats, [signal, k, str(v), "CODE_DEPENDENT_TRANSLATION"])
    base_unit = my_instr["base_unit"]
    eprint("base_unit", base_unit)
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
        return
    if total_cnt == 0:
        eprint_also_to_file(out_file_stats, [signal, "ALL_UNITS", 0, "WARNING", "skipping signal as it has no records"])
        return  
    eprint("signal [%s]: about to process %d records" %(signal, total_cnt))
    
    out_fixed_path = os.path.join(out_stats_folder, sigFileName + "__fix.list")
  
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
                eprint("ERROR : %s : Cannot translate [%s], which stands for [%d/%d = %f] from [%s]" % (signal, unit, len(data[unit]), base_unit_cnt, pct_of_base, base_unit))
                raise Exception
        eprint("translating", unit, "with", my_instr["translate"][unit])
        data[unit] = translate(data[unit], my_instr["translate"][unit])

    all_data = []
    unitLens = []
    unitNames = []
    cumSum = 0
    all_pids = []
    all_dates = []
    all_sources = []
    all_units = []
    for unit in data.keys():
        all_data = all_data + list(map(float,data[unit]))
        all_pids = all_pids + list(map(lambda listTp : int(listTp[0]) ,metadata[unit]))
        all_dates = all_dates + list(map(lambda listTp : int(listTp[1]) ,metadata[unit]))
        all_sources = all_sources + list(map(lambda listTp : listTp[2] ,metadata[unit]))
        all_units = all_units + [unit] * len(data[unit])
        
    if len(my_instr["factors"]) > 0:
        eprint("finding best factor and fixing")
        out_file_fixed = open(out_fixed_path , 'w')
        all_data = fixFactorsMixtureGaussian(all_data, my_instr["factors"], my_instr["supposeMean"], True, out_file_fixed)
    eprint("completed translating and fixing: %s with %d records"%(unit, len(all_data)))

    out_filename = join(out_fixed_folder, sigFileName)
    eprint("fixing resolution to", my_instr["resolution"], "and multiplying by final_factor", my_instr["final_factor"])
    eprint("about to write %s" % out_filename)
    out_data = []

    for i in range(len(all_data)):
        v = all_data[i]
        if v < 0.0:
            continue
        if my_instr["resolution"] == "10.0":
            v = round(v, -1)
        else:
            v = float(my_instr["resolution"].format(v))
        v = v*my_instr["final_factor"]
        if my_instr["trimMax"] is not None:
            if v > my_instr["trimMax"]:
                v = my_instr["trimMax"]
        out_data.append([all_pids[i], signal, all_dates[i], "{:.6f}".format(v), all_sources[i], all_units[i]])
                    
    out_data.sort()
    #o = open(out_filename, 'w')
    o = io.open(out_filename, 'w', newline = '')
    lineExists = set()
    for l in out_data:
        ln = '\t'.join(map(str,l))
        if not(ln in lineExists): #Remove duplicate rows
            o.write(unicode(ln + '\n'))
        lineExists.add(ln)
    o.close()

def fixAllSignal():
    cfg = Configuration()
    united_file_Path = os.path.join( fixOS(cfg.work_path), 'United')
   
    in_file_names = os.listdir(united_file_Path)
    in_file_names = map(lambda f: os.path.join(united_file_Path, f), in_file_names) 
    eprint("about to process", len(in_file_names), "files")

    unit_instruction = read_instructions()
    eprint("found", len(unit_instruction), "unit instructions")
    read_unit_translation(unit_instruction) 
    ahd_code_dependent_translation = read_code_dependent()    
    eprint("found", len(ahd_code_dependent_translation), "code dependent translations")
    pdf_cache = {}  
    cdf_cache = {}

    # main loop
    failedList = dict()
    for in_filename in in_file_names:
        signal = os.path.basename(in_filename)
        try:
            fixSignal(signal, unit_instruction, ahd_code_dependent_translation, pdf_cache, cdf_cache)
        except:
            failedList[signal] = traceback.format_exc()
            traceback.print_exc()
    return failedList

if __name__ == "__main__":   
    #fixAllSignal()
    fixSignal(sys.argv[1])
