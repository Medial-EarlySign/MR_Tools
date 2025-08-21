#!/usr/bin/python

from __future__ import print_function
import argparse
import string
import pandas as pd, numpy as np, os, glob
from datetime import datetime
from  medial_tools.medial_tools import eprint, read_file, write_for_sure

parser = argparse.ArgumentParser()
parser.add_argument('--work_folder', default='/server/Work/Users/Ido/rambam_load/')
parser.add_argument('--raw_data_folder', default='/server/Data/RAMBAM/da_medial_patients/')
args = parser.parse_args()

ids = sorted([int(os.path.basename(f)[:-4]) for f in glob.glob(args.raw_data_folder + '/*.xml')])
outme = pd.DataFrame({'id':ids, 'nr': range(101000000, 101000000 + len(ids))})
write_for_sure(outme, args.work_folder + '/id2nr', index = False, sep='\t', header = False, columns = ['nr', 'id'])