import pandas as pd
import numpy as np
import os

def comp_regs(reg1_file, reg2_file):

    cols = ['pid', 'sig', 'start_date', 'end_date', 'level']
    df1 = pd.read_csv(reg1_file, sep='\t', names=cols)
    df2 = pd.read_csv(reg2_file, sep='\t', names=cols)

    for pid, df in df1.groupby('pid'):
        comp_df = df2[df2['pid']==pid]
        if not df.equals(comp_df):
            print(pid)
            print(comp_df)
            print(df)
            print('-------------------------------------')

def test_kpnw():
    kp_reg = 'W:\\AlgoMarkers\\Pre2D\\kpnw\\diabetes.DM_Registry'
    cols = ['pid', 'sig', 'start_date', 'end_date', 'level']
    new_df = pd.read_csv(kp_reg, sep='\t', names=cols)
    print(new_df)


if __name__ == '__main__':
    #new_reg = 'W:\\AlgoMarkers\\Pre2D\\pre2d_thin18\\diabetes.DM_Registry_python'
    #prev_reg = 'W:\\AlgoMarkers\\Pre2D\\pre2d_thin18\\diabetes.DM_Registry'
    #comp_regs(prev_reg, new_reg)

    py_reg = 'W:\\AlgoMarkers\\Pre2D\\kpnw\\diabetes.DM_Registry_python'
    c_reg = 'W:\\AlgoMarkers\\Pre2D\\kpnw\\diabetes.DM_Registry'
    #comp_regs(py_reg, c_reg)
    test_kpnw()
