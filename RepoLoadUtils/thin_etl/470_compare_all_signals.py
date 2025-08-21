from __future__ import print_function
from collections import defaultdict
import sys
import argparse
from os.path import join
import subprocess
import os

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
    
parser = argparse.ArgumentParser()
parser.add_argument('--in_signals_file', default='all.signals')
parser.add_argument('--out_folder', required=True)
args = parser.parse_args()

with open(args.in_signals_file) as f:
    signals = [s.strip() for s in f.readlines()]
    
print(signals)    

cmd = "/server/UsersData/ido/Medial/Projects/General/Flow/Linux/Release/Flow "
reps = ["/home/Repositories/MHS/build_Feb2016_Mode_3/maccabi.repository", "/server/Work/Users/Ido/THIN_ETL/final_repo/build_nov2016/thin.repository"]
for s in signals:
    for repo in reps:
        out_file_name = args.out_folder + "/" + s + "." + os.path.basename(repo)
        print("writing to: " + out_file_name)
        with open(out_file_name,'w') as f:
            try:
                c = cmd + " --rep " + repo + " --describe --age_min=20 --age_max=100 --date_min=20000101 --date_max=20170101 --sig " + s
                print(c)
                my_out = subprocess.check_output(c, shell = True)
                print(my_out, file = f)
            except KeyboardInterrupt:
                    raise            
            except:
                print("failed in signal: " + s + " repo: " + repo)
                print("failed in signal: " + s + " repo: " + repo, file = f)

    
     