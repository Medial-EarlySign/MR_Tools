import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from ETL_Infra.unit_conversions import find_best_unit_suggestion

def Test(df: pd.DataFrame, si, codedir: str, workdir: str):   
    if len(df)==0:
        return True
    MIN_GRP_SIZE = 500
    fail=False
    sig_name=df['signal'].iloc[0]
    # Test best unit conversion
    res = find_best_unit_suggestion(df, False, 0.5, 3, MIN_GRP_SIZE)
    for grp_tuple, grp_res in res.items():
        if grp_res is None:
            continue
        if len(grp_res) == 0:
            print(f'WARNING: no matching conversion unit to match expected median value for {grp_tuple}')
            continue
        if grp_res[0].group_size < MIN_GRP_SIZE:
            continue
        if len(grp_res) > 1:
            txt_res = '\n'.join(map(lambda x:str(x), grp_res))
            print(f'WARNING: Multiple matches for {grp_tuple}, please inspect:\n{txt_res}')
        else:
            grp_res = grp_res[0]
            # check it's 0, 1:
            if grp_res.bias != 0 or grp_res.factor != 1:
                print(f'WARNING: Critical!, found better matching for unit for {grp_tuple}. please consider: \n{grp_res}')
    
    print(f'Done testing units values for {sig_name}')
    return not(fail)


