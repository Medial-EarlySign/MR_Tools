import os
import sys
import pandas as pd
sys.path.append('/mnt/project/python_lib/')
import med
from Configuration import Configuration


if __name__ == '__main__':
    cfg = Configuration()
    rep = med.PidRepository()
    rep.read_all(cfg.repo, [], ['GENDER'])
    print(med.cerr())
    drug_df = rep.get_sig('Drug')
    print(drug_df.shape)