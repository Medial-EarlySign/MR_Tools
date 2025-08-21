#!/bin/python
import sys, os, random
sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils', 'thin_etl'))
from Configuration import Configuration
from common import *
from flow_api import getLines, add_train_censor

def fixTrain():
    cfg = Configuration()
    cl_ratio = dict()
    cl_ratio[1] = 0.7
    cl_ratio[2] = 0.2
    cl_ratio[3] = 0.1
    
    pid_new_path = os.path.join(fixOS(cfg.work_path), 'demo')
    lines = getLines(pid_new_path, 'byears')
    pids_new = set(map(lambda ln : int(ln.split(' ')[0]) ,lines))
    print('done reading %d pids'%(len(pids_new)))
    lines = getLines(os.path.join(fixOS(cfg.work_path), 'missing_pids_from_2016' ,'demo'), 'byears')
    pids_add = list(set(map(lambda ln : int(ln.split(' ')[0]) ,lines)))
    for pid in pids_add:
        pids_new.add(pid)
    pids_new = list(pids_new)
    
    old_id2nr_p = fixOS('/server/Temp/Ido/ahd/ID2NR')
    new_id2nr_p = os.path.join(fixOS(cfg.work_path), 'ID2NR')
    if not(os.path.exists(old_id2nr_p)) or not(os.path.exists(new_id2nr_p)):
        raise NameError('Missing ID2NR file\n%s\n%s'%(old_id2nr_p, new_id2nr_p))
    old_train = os.path.join(fixOS(cfg.work_path), 'outputs', 'old_rep_train.pids') #created by flow, or the scripts which creates train signal
    fp = open(new_id2nr_p, 'r')
    lines = fp.readlines()
    fp.close()
    id2nr = read_id2nr(lines)
    fp = open(os.path.join(fixOS(cfg.work_path), 'missing_pids_from_2016', 'ID2NR'), 'r')
    lines = fp.readlines()
    fp.close()
    id2nr_add = read_id2nr(lines)
    for key,val in id2nr_add.items():
        id2nr[key] = val

    fp = open(old_id2nr_p, 'r')
    lines = fp.readlines()
    fp.close()
    nr2id_old = dict()
    for line in lines:
        id, nr = line.split('\t')
        nr = int(nr)
        nr2id_old[nr] = id
    
    fp = open(old_train, 'r')
    lines = fp.readlines()
    fp.close()
    lines = lines[1:]
    id2train = dict() #from pid id in new rep to train value - first take all train signal from old rep:
    miss_cnt = dict()
    for line in lines:
        id, t_class = line.split('\t')
        t_class = int(t_class)
        id = int(id) #in old rep
        combid = nr2id_old[id]
        if combid not in id2nr:
            if miss_cnt.get(t_class) is None:
                miss_cnt[t_class] = 0
            miss_cnt[t_class] += 1
            #print('MISSING combid in new rep %s'%combid)
            continue
        id = id2nr[combid]
        
        id2train[id] = t_class
    tot_mis = sum(miss_cnt.values())
    print('Miss_cnt = %s\ntotal_mis=%d'%(miss_cnt, tot_mis))
    min_val = min(miss_cnt.values())
    for k,v in miss_cnt.items():
        miss_cnt[k] = v - min_val
    tot_mis = sum(miss_cnt.values())
    
    #complete missing ids:
    pids_to_add = list(filter(lambda pid: pid not in id2train, pids_new))
    print('Will add %d'%(len(pids_to_add)))
    random.shuffle(pids_to_add)
    #complete unbalance first:
    tot_add_cnt = len(pids_to_add)
    last_pos = 0 
    for train_val,to_add_cnt in miss_cnt.items():
        end_pos = last_pos+to_add_cnt
        print('value=%d for missings, poses=[%d, %d] size=%d'%(val, last_pos, end_pos, tot_add_cnt))
        pid_list = pids_to_add[int(last_pos):int(end_pos)]
        for pid in pid_list:
            id2train[pid] = val
        last_pos += to_add_cnt

    tot_add_cnt -= tot_mis
    if tot_add_cnt < 0 :
        raise NameError('too many misses, resolve before continue')
    final_counts = dict()
    last_val = None
    tot_sum = 0
    for val, ratio in cl_ratio.items():
        last_val = val
        final_counts[val] = round(ratio * tot_add_cnt)
        tot_sum += final_counts[val]
    final_counts[last_val] = tot_add_cnt - (tot_sum-final_counts[last_val]) #keep only what's left
    
    for val, cnt in final_counts.items():
        end_pos = last_pos+cnt
        print('value=%d, poses=[%d, %d] size=%d'%(val, last_pos, end_pos, len(pids_to_add)))
        pid_list = pids_to_add[int(last_pos):int(end_pos)]
        for pid in pid_list:
            id2train[pid] = val
        last_pos += cnt

    lines = list(map(lambda kv : '%d\tTRAIN\t%d\n'%(kv[0], kv[1]),id2train.items()))
    lines.sort(key = lambda ln: int(ln.split('\t')[0]))
    fw = open(os.path.join(pid_new_path, 'TRAIN'), 'w')
    fw.writelines(lines)
    fw.close()
        
if __name__ == "__main__":
    add_train_censor('/home/Repositories/THIN/thin_jun2017/thin.repository')
    #fixTrain()