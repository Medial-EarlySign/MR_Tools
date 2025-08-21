import os
import sys
import pandas as pd
import argparse
from Configuration import Configuration
import numpy as np

if __name__ == '__main__':
    #  Read command arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--id_start', type=int, default=1, help='first id')
    args, unparsed = parser.parse_known_args()

    if (unparsed):
        eprint("Left with unparsed arguments:")
        eprint(unparsed)
        exit(0)

    cfg = Configuration()

    # Read patient_cohort file
    inFile = os.path.join(cfg.data_path,'patient_cohort.csv')
    pc = pd.read_csv(inFile)
    print(f'Read {len(pc)} patients from {inFile}')

    # Add index column
    pc['pid'] = args.id_start + np.arange(len(pc))

    # Write
    outFile = os.path.join(cfg.work_path,'ID2NR')
    pc[['patient_id','pid']].to_csv(outFile,sep='\t',header=None,index=False)
