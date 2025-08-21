from common import *
from Configuration import Configuration
import os, re

def unite_signals(signalNameRegex):
    msgs = []
    cfg = Configuration()
    map_file_path = os.path.join(fixOS(cfg.code_folder), 'thin_signals_to_united.txt')
    united_path = os.path.join( fixOS(cfg.work_path), 'United')
    if not(os.path.exists(united_path)):
        os.makedirs(united_path)
    original_signals_path = os.path.join(fixOS(cfg.work_path), 'Common')
    regex = re.compile(signalNameRegex)
    if not(os.path.exists(map_file_path)):
        raise NameError('map file doesn''t exists please fix configuration file')
    fo = open(map_file_path, 'r')
    lines = fo.readlines()
    fo.close()
    lines = lines[1:] # skip header
    total_nin = len(lines)
    file_list = dict()
    proccess_cnt = 0
    for line in lines:
        tokens = line.strip().split('\t')
        in_file = tokens[0].strip()
        out_signal = tokens[1].strip()
        if ( out_signal == 'TBD' or out_signal == 'NULL' or len(regex.findall(out_signal)) == 0):
            continue
        if file_list.get(out_signal) == None:
            file_list[out_signal] = []
        file_list[out_signal].append(in_file)
        proccess_cnt = proccess_cnt + 1
    msg = 'About to unite %d files (out of %d) into %d files'%(proccess_cnt, total_nin, len(file_list.keys()))
    msgs.append(msg)
    print(msg)
    found_cnt = 0
    for signal, fl_list in file_list.items():
        msg = 'Appending to United/%s ...'%signal
        msgs.append(msg)
        print(msg)
        fw = open( os.path.join(united_path, signal.replace('/', '_over_')), 'w')
        for source_name in fl_list:
            full_path = os.path.join(original_signals_path, source_name)
            lineSet = set()
            if not(os.path.exists(full_path)):
                msg = 'Cannot find %s, skipping...'%signal
                msgs.append(msg)
                eprint(msg)
                continue
            found_cnt = found_cnt + 1
            fo = open(full_path, 'r')
            line = fo.readline()
            while line is not None and len(line) != 0:
                if not(line in lineSet):
                    fw.write('%s\t%s\n'%(line.strip(), source_name))
                    lineSet.add(line)
                line = fo.readline()
            fo.close()
        fw.close()
    msg = 'Found %d files (out of %d I looked for) and wrote them into %d files'%(found_cnt, proccess_cnt, len(file_list.keys()))
    msgs.append(msg)
    print(msg)
    return msgs

def unite_all_signal():
    return unite_signals('.*')

if __name__ == "__main__":
    #unite_all_signal()
    msg  = unite_signals(sys.argv[1])
