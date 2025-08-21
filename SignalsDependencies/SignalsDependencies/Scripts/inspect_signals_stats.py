#!/bin/python
from datetime import datetime
import sys

def dateDiff(d1, d2):
    if (d1 /100) % 100 == 0:
        d1 = d1 + 100
    if (d2 /100) % 100 == 0:
        d2 = d2 + 100
    if d1 % 100 == 0:
        d1 = d1 + 1
    if d2 % 100 == 0:
        d2 = d2 + 1
    dd1 = datetime.strptime( str(d1), '%Y%m%d')
    dd2 = datetime.strptime( str(d2), '%Y%m%d')
    secs = (dd1- dd2).total_seconds()
    return secs / 60 / 60 / 24


def age_bin(age):
    return int(5*round(age/5))

#for 1 pid - bucket is rows for same 1 pid
def handle_bucket(bucket, num_false_reg, num_only_reg, num_only_sig, num_both, from_d, to_d):
    reg_vals = []
    sig_vals = []
    for row in bucket:
        if row[1]:
            reg_vals.append(row)
        else:
            sig_vals.append(row)
    #print('%s %s\n'%(reg_vals, sig_vals))
    age_seen = dict()
    for reg in reg_vals:
        age_b = age_bin(reg[-2])
        foundVal = False
        for sig in sig_vals:
            if reg[-1] > 0:
                if dateDiff(reg[0], sig[0]) >= from_d and dateDiff(reg[0], sig[0]) <= to_d:
                    if (age_seen.get(age_b) is None):
                        num_both += 1
                        #else:
                        #    num_only_sig += 1
                    age_seen[age_b] = True
                    foundVal = True
                    break
            else:
                for age_i in range(20, age_b+1, 5):
                    if (age_seen.get(age_i) is None):
                        num_only_sig += 1
                    age_seen[age_i] = True
                    foundVal = True
                        
        if not(foundVal):
            if reg[-1] > 0:
                num_only_reg += 1
            else:
                num_false_reg += 1
            
            #if not(has_inter):
            #    if (age_seen.get(age_bin(sig[-1])) is None):
            #        num_only_sig = num_only_sig + 1
            #    age_seen[age_bin(sig[-1])] = True
            
    return num_false_reg, num_only_reg, num_only_sig, num_both

#only data for same 1 pid
def handle_bucket_age(bucket, ageStats, from_d, to_d):
    reg_vals = []
    sig_vals = []
    for row in bucket:
        if row[1]:
            reg_vals.append(row)
        else:
            sig_vals.append(row)
    #print('%s %s\n'%(reg_vals, sig_vals))
    age_seen = dict() #skip same age for pid in registry
    for reg in reg_vals:
        age_b = age_bin(reg[-2])
        for sig in sig_vals:
            if reg[-1] > 0:
                if dateDiff(reg[0], sig[0]) >= from_d and dateDiff(reg[0], sig[0]) < to_d:
                    if (age_seen.get(age_b) is None):
                        if ageStats.get(age_b) is None:
                            ageStats[age_b] = [0, 0, 0 , 0]
                        ageStats[age_b][2 + int(reg[-1]>0)] += 1
                    age_seen[age_b] = True
                    break
            else:
                if (dateDiff(reg[0], sig[0]) < to_d):
                    continue # can't be sure it's control
                age_i = age_bin(sig[-1])
                if (age_seen.get(age_i) is None):
                    if ageStats.get(age_i) is None:
                        ageStats[age_i] = [0, 0, 0 , 0]
                    ageStats[age_i][2 + int(reg[-1]>0)] += 1
                age_seen[age_i] = True
                    
        if age_seen.get(age_b) is None:
            if reg[-1] > 0:
                if (age_seen.get(age_b) is None):
                    if ageStats.get(age_b) is None:
                        ageStats[age_b] = [0, 0, 0 , 0]
                    ageStats[age_b][0 + int(reg[-1]>0)] += 1
                    age_seen[age_b] = True
            else:
                for age_i in range(20, age_b+1, 5):
                    if (age_seen.get(age_i) is None):
                        if ageStats.get(age_i) is None:
                            ageStats[age_i] = [0, 0, 0 , 0]
                        ageStats[age_i][0 + int(reg[-1]>0)] += 1
                        age_seen[age_i] = True
            
        #if not(has_inter):
            #if age_seen.get(age_bin(reg[-2])) is None:
             #   if ageStats.get(age_bin(reg[-2])) is None:
             #       ageStats[age_bin(reg[-2])] = [0, 0 , 0]
             #   ageStats[age_bin(reg[-2])][0] += 1
            #age_seen[age_bin(reg[-2])] = True
            
            #if not(has_inter):
            #    if (age_seen.get(age_bin(sig[-2])) is None):
            #        if ageStats.get(age_bin(sig[-2])) is None:
            #            ageStats[age_bin(sig[-2])] = [0, 0, 0]
            #        ageStats[age_bin(sig[-2])][1] = ageStats[age_bin(sig[-2])][1] + 1
            #    age_seen[age_bin(sig[-2])] = True
    return ageStats

def print_gender_stats(stats, name):
    print('%s:\n'%name)
    row_format ="{:>8}" * 5
    tps = []
    for k,v in stats.items():
        tps.append([k,v])
    tps = sorted(tps, key = lambda r: r[0])
    for age, stats_vec in tps:
        #prt = ', '.join( list(map(lambda v: '%8s%d'%('',v) ,stats_vec)) )
        prt = row_format.format("%d - ["%(age), *stats_vec) + "]"
        print(prt)

def get_pid_stats(signal_path, registry_path):
    fp = open(signal_path)
    lines = fp.readlines()
    fp.close()

    lines = lines[1:]
    lines = list(filter(lambda l : len(l.strip()) > 0 and not(l.startswith('#')) ,lines))
    pid_signals = dict()
    for line in lines:
        tokens = line.split('\t')
        pid = int(tokens[0])
        gender = int(tokens[1])
        #ageBin = 5*round(float(tokens[2]) / 5)
        ageBin = float(tokens[2])
        date = int(tokens[3])
        sig = int(tokens[4])
        if pid_signals.get(pid) is None:
            pid_signals[pid] = []
        pid_signals[pid].append([date, False, gender, ageBin])

    fp = open(registry_path)
    lines = fp.readlines()
    fp.close()

    lines = lines[1:]
    lines = list(filter(lambda l : len(l.strip()) > 0 and not(l.startswith('#')) ,lines))
    #pid, start, end, censor_date, age, gender, registry_value
    for line in lines:
        tokens = line.split('\t')
        pid = int(tokens[0])
        date = int(tokens[1])
        end_date = int(tokens[2]) #for now supports only end_date not bounded
        censor_date = int(tokens[3]) #for now supports only censor_date not bounded
        ageBin = float(tokens[4])
        gender = int(tokens[5])
        reg  = int(tokens[6])
        #ageBin = 5*round(float(tokens[2]) / 5)
        if (reg < 0):
            continue
        if pid_signals.get(pid) is None:
            pid_signals[pid] = []
        pid_signals[pid].append([date, True, gender, ageBin, reg])
    return pid_signals

def parse_file(signal_path, registry_path, from_day ,to_day):
    pid_signals = get_pid_stats(signal_path, registry_path)
    num_false_reg = 0
    num_only_reg = 0
    num_only_sig = 0
    num_both = 0
    maleStats = dict()
    femaleStats = dict()
    for pid, bucket in pid_signals.items():
        num_false_reg, num_only_reg, num_only_sig, num_both = handle_bucket(bucket, num_false_reg, num_only_reg, num_only_sig, num_both, from_day, to_day)
        if bucket[0][2] == 1:
            maleStats = handle_bucket_age(bucket, maleStats, from_day, to_day)
        else:
            femaleStats = handle_bucket_age(bucket, femaleStats, from_day, to_day)
        
    print("false_reg =%d, only_reg=%d, only_sig=%d, both=%d"%(num_false_reg, num_only_reg, num_only_sig, num_both))
    print_gender_stats(maleStats, 'male')
    print_gender_stats(femaleStats, 'female')

def filter_age(bucket, pid, ageBin, from_day ,to_day):
    reg_vals = []
    sig_vals = []
    res = []
    for row in bucket:
        if row[1]:
            reg_vals.append(row)
        else:
            sig_vals.append(row)

    #join both vectors by date:
    for reg in reg_vals:
        if reg[-1] > 0:
            if (age_bin(reg[-2]) != ageBin):
                continue
        else:
            if (age_bin(reg[-2]) < ageBin):
                continue
            
        age_seen = False #of ages = for specific pid
        for sig in sig_vals:
            if reg[-1] > 0:
                if dateDiff(reg[0], sig[0]) >= from_day and dateDiff(reg[0], sig[0]) < to_day:
                    age_seen = True
                    txt = 'ONLY_SIGNAL'
                    if reg[-1] > 0:
                        txt = 'BOTH'
                    res.append( [ pid,txt, reg[0], reg[-2], sig[0], sig[-1]  ] )
                    break
            else:
                if age_bin(sig[-1]) != ageBin:
                    continue
                if dateDiff(reg[0], sig[0]) > to_day: # reg is after signal - OK :)
                    age_seen = True
                    txt = 'ONLY_SIGNAL'
                    res.append( [ pid,txt, reg[0], reg[-2], sig[0], sig[-1]  ] )
                    break
                    
        if not(age_seen):
            if reg[-1] > 0:
                res.append( [ pid, 'ONLY_IN_REGISTRY_TRUE', reg[0], reg[-2], 0, 0] )
            else:
                res.append( [ pid, 'ONLY_IN_REGISTRY_FALSE', reg[0], reg[-2], 0, 0] )

    return res
        

def print_gender_bucket_stats(gender_male, ageBin, signal_path, registry_path, from_day, to_day):
    pid_signals = get_pid_stats(signal_path, registry_path)
    res = []
    for pid, bucket in pid_signals.items():
        if (bucket[0][2] == 1 and gender_male) or (not(gender_male) and not(bucket[0][2] == 1)): # sutible gender filter
            filt = filter_age(bucket, pid, ageBin, from_day, to_day)
            res = res + filt
    agg = dict()
    for row in res:
        if agg.get(row[1]) is None:
            agg[row[1]] = []
        agg[row[1]].append(row)

    for agg_name, row_list in agg.items():
        print('%s has %d records'%(agg_name, len(row_list)))

    for agg_name, row_list in agg.items():
        print('%s (%d):'%(agg_name, len(row_list)))
        ii = 1
        for row in row_list:
            print ('%03d [pid=%d, date_reg=%d, age_reg=%2.1f, date_sig=%d, age_sig=%2.1f]'%(ii, row[0], row[2], row[3], row[4], row[5]))
            ii = ii + 1

def read_config(fp):
    f = open(fp, 'r')
    lines = f.readlines()
    f.close()
    cfgs = { 'test_min_duration': None, 'test_duration': None, 'registry_path': None }
    lines = list(filter(lambda l :  len(l.strip()) >0 and not(l.strip().startswith('#')) ,lines))
    for line in lines:
        key, val = line.split('=')
        if key.strip() in cfgs:
            val = val.strip()
            if val.find('#') > 0:
                val = val[:val.find('#')]
            cfgs[key.strip()] = val
    if len(filter(lambda kv: kv[1] is None,cfgs.items())) > 0:
        fl = list(filter(lambda kv: kv[1] is None,cfgs.items()))
        raise NameError('Couldn''t find key %s'%(fl[0][0]))
    return cfgs
    

#main program:
if __name__ == "__main__":
    if len(sys.argv) != 3 and len(sys.argv) != 5:
        raise NameError('Program must get ConfigPath, and signal output path. option 2: adding male\female flag and age bucket. argument count=%d'%(len(sys.argv)))
    config_path = sys.argv[1]
    signal_path = sys.argv[2]
    cfgs = read_config(config_path)
    registry_path = cfgs['registry_path']
    print('RegsitryPath: %s'%registry_path)
    print('Signal Path: %s'%signal_path)
    from_day = int(cfgs['test_min_duration'])
    to_day = int(cfgs['test_min_duration'])+int(cfgs['test_duration'])
    if len(sys.argv) == 3:
        parse_file(signal_path, registry_path, from_day, to_day)
    else:
        gender = int(sys.argv[3]) > 0 #1-male,0-feamle
        ageBucket = int(sys.argv[4])
        print('Gender %s'%('Male' if gender else 'Female'))
        print('Age %d'%(ageBucket))
        print_gender_bucket_stats(gender > 0, ageBucket, signal_path, registry_path, from_day, to_day)
