#!/bin/python
import sys, os, io
sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils', 'thin_etl'))
from flow_api import getLines
from common import *
from Configuration import Configuration

def get_id_conversion(previous_id2nr = fixOS('/server/Temp/Ido/ahd/ID2NR')):
    cfg = Configuration()
    work_path = fixOS(cfg.work_path)
    #build fix id to id dictionary
    lines = getLines(work_path, 'ID2NR')
    id2comb = dict()
    for line in lines:
        comb, id = line.split('\t')
        id2comb[int(id)] = comb
    lines = getLines(os.path.join(work_path, 'missing_pids_from_2016') ,'ID2NR')
    for line in lines:
        comb, id = line.split('\t')
        id2comb[int(id)] = comb
    print('Done reading id2comb')
    #create new additional ID2NR based on previous ID2NR
    comb2id = dict()
    fp_old = open(previous_id2nr, 'r')
    lines = fp_old.readlines()
    fp_old.close()
    last_id = None
    for line in lines:
        comb, id = line.split('\t')
        id  = int(id)
        comb2id[comb] = id
        if last_id is None or last_id < id:
            last_id = id
    #Now completes all missings with new ids:
    missing_combs = list(filter(lambda comb : comb not in comb2id,id2comb.values()))
    print('has %d missing comb ids to add'%(len(missing_combs)))
    id2id = dict() #final convertion from old_id to new fixed id"
    for comb in missing_combs:
        last_id += 1
        comb2id[comb] = last_id
        id2id[last_id] = last_id
    for id, comb in id2comb.items():
        new_id = comb2id[comb]
        id2id[id] = new_id
    #save file if not exists:
    if not(os.path.exists( os.path.join(work_path, 'ID2NR_fixed'))):
        fw = open(os.path.join(work_path, 'ID2NR_fixed'), 'w')
        fw.writelines(list(map(lambda kv : '%s\t%d\n'%(kv[0], kv[1]) ,comb2id.items())))
        fw.close()
    return id2id

def fix_signal_ids(signalPath ,id2id = None, delim = '\t'):
    cfg = Configuration()
    log_file = os.path.join(fixOS(cfg.output_path), 'done_conv.log')
    done_files = set()
    if os.path.exists(log_file):
        fp = open(log_file, 'r')
        lines = fp.readlines()
        fp.close()
        done_files = set(filter(lambda l : len(l) > 0 ,map(lambda s: s.strip(),lines)))
    if signalPath in done_files:
        print('Already Done %s - skipping'%signalPath)
        return
    if id2id is None:
        id2id = get_id_conversion()
    if not(os.path.exists(signalPath)):
        raise NameError('Couldn''t find path "%s"'%signalPath)
    print('Working on %s...'%signalPath)
    fp = open(signalPath, 'r')
    line = fp.readline()
    c_lines = []
    tmp_file = os.path.join(fixOS(cfg.output_path), 'tmp_signal_conv')
    fw = open(tmp_file, 'w')
    line_num = 0
    while (line is not None and len(line) > 0):
        tokens = line.strip().split(delim)
        id = int(tokens[0])
        rest_tokens = delim.join(tokens[1:])
        if id not in id2id:
            raise NameError('Couldn''t find %d in conversion'%id)
        new_id = id2id[id]
        c_lines.append('%d%s%s\n'%(new_id, delim, rest_tokens))
        if ((line_num+1) % 1000000) == 0:
            fw.writelines(c_lines)
            fw.close()
            fw = open(tmp_file, 'a')
            c_lines = [] # flush buffer
            line_num = -1
        line = fp.readline()
        line_num += 1
    fp.close()
    if len(c_lines) > 0:
        fw.writelines(c_lines)
    fw.close()
    #c_lines.sort(key = lambda ls: ls[0])
    #c_lines = map(lambda grp: unicode('\t'.join(map(str ,grp)) + '\n') ,c_lines)

    #sort file:
    cmd = """sort -k1 -n -S 40G %s > %s"""%(tmp_file, signalPath)
    p = subprocess.call(cmd, shell=True)

    if (p != 0):
        print ('Error in running sort command. CMD was:\n%s'%cmd)
        raise NameError('stop')
    
    #fw = io.open(signalPath, 'w', newline= '')
    #fw.writelines(c_lines)
    #fw.close()
    
    fw = open(log_file, 'a')
    fw.write('%s\n'%signalPath)
    fw.close()

def clear_comm(s):
    p = s.find('#')
    if p != -1:
        s = s[:p].strip()
    return s

def fix_all():
    try:
       input = raw_input
    except NameError:
       pass
    id2id = get_id_conversion()
    cfg = Configuration()
    work_path = fixOS(cfg.work_path)
    config_file = os.path.join(work_path, 'missing_pids_from_2016', 'rep_configs')
    lines = getLines(config_file, 'thin.fix_specific.convert_config')
    dir_path = filter(lambda l : len(l) > 0 and l.startswith('DIR') ,map(lambda line: line.strip() ,lines))
    if len(dir_path) == 1:
        dir_path = dir_path[0].split('\t')[1].strip()
        print('found dir_path: %s'%dir_path)
        base_path = dir_path
    else:
        print('haven''t foudn DIR in convert_file using dir_path: %s'%config_file)
        base_path = config_file
    lines = filter(lambda l : len(l) > 0 and l.startswith('DATA') ,map(lambda line: line.strip('#').strip() ,lines))
    task_list = list(map(lambda line: os.path.abspath(os.path.join(base_path, clear_comm(line.split('\t')[1].strip()))) ,lines))
    print('Has %d signals to convert'%(len(task_list)))
    i = 0

    #fix_signal_ids(task_list[0], id2id)
    val = input('Press Y to continue or N to cancel: ')
    if val.upper() == "N":
        print('Exit')
        return
    elif val.upper() != "Y":
        print('Unknown input - exits..')
        return
    skip_list = []
    for signal in task_list:
        if not(os.path.exists(signal)):
            skip_list.append(signal)
            print('NOT EXISTS %s'%signal)
            i+=1
            continue
        fix_signal_ids(signal, id2id)
        i+=1
        print('Done %d out of %d'%(i, len(task_list)))
    if len(skip_list) > 0:
        print('skipped %d not exits'%(len(skip_list)))
        print('Skip list:\n%s'%('\n'.join(skip_list)))
    
if __name__ == "__main__":
    cfg = Configuration()
    #fix_signal_ids(os.path.join( fixOS(cfg.work_path) ,'demo', 'byears'), None, ' ')
    #fix_signal_ids(os.path.join( fixOS(cfg.work_path), 'missing_pids_from_2016' ,'demo', 'byears'), None, ' ')
    #fix_signal_ids(os.path.join( fixOS(cfg.work_path), 'missing_pids_from_2016' ,'Fixed', 'eGFR'), None)
    #fix_signal_ids(os.path.join( fixOS(cfg.work_path) ,'Fixed', 'eGFR'), None)
    fix_all()
    
    
