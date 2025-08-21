#!/bin/python
import sys, os, random, io
sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils', 'thin_etl'))
from Configuration import Configuration
from common import *
from flow_api import getLines

def parse_line(line):
    #pracid, patid, event_date, ahd_code, flag, medcode, value
    return line[:5], line[5:9], line[9:17], line[17:27], line[27:28], line[106:113], line[151:161].strip()

def load_rdw(rdw_path):
    read_codes_set = set()
    read_codes_set.add('42Z7.00')
    cfg = Configuration()
    work_path = fixOS(cfg.work_path)
    if not(os.path.exists(rdw_path)):
        raise NameError('couldn''t find %s'%rdw_path)
    lines = getLines('/server/Temp/Thin_2017_Loading', 'ID2NR_fixed')
    id2nr = read_id2nr(lines)
    
    fp = open(rdw_path, 'r')
    lines = fp.readlines()
    fp.close()
    lines = lines[1:]
    stats = {'bad_flag' :0, 'read' : 0, 'bad_rdw_code' : 0, 'not_numeric' : 0 , 'empty' : 0, 'wrote_number' : 0, 'unknown_id' : 0}
    stats_file = open(os.path.join(work_path, 'outputs', 'rdw_load.stats'), 'w')
    write_lines= []
    for line in lines:
        pracid, patid, event_date, ahd_code, flag, medcode, value = parse_line(line)
        combid = pracid + patid
        stats['read'] += 1
        if (flag != 'Y'):
            stats['bad_flag'] += 1
            continue
        if (medcode not in read_codes_set):
            stats['bad_rdw_code'] += 1
            continue
        if not(combid in id2nr):
            stats['unknown_id'] += 1
            continue
        if len(value) == 0:
            stats['empty'] += 1
            continue
        if not(is_number(value)):
            stats['not_numeric'] += 1
            continue
        stats['wrote_number'] +=1

        pid =  int(id2nr[combid])
        write_lines.append( [pid, 'RDW', event_date, value] )

    write_lines.sort()
    write_lines = list(map(lambda ln : unicode('\t'.join(map(str ,ln)) + '\n') ,write_lines))
    fw = io.open(os.path.join(work_path, 'Fixed', 'RDW'), 'w', newline = '')
    fw.writelines(write_lines)
    fw.close()
    write_stats(stats, 'all', stats_file)

load_rdw(fixOS('/server/Data/THIN1601/Additional_files/AHD_extract_for_ AHDcode_1001400217.txt'))