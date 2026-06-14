import pandas as pd
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tests.labs.test_lab_unit_conversions import Test,calc_kld, calc_distribution_distance

#TEST_PATH='/nas1/Work/Users/Eitan/KLD_example1.txt'
#OUTPUT_PATH='/tmp'
TEST_PATH='W:/Users/Eitan/KLD_example1.txt'
OUTPUT_PATH='X:/test_etl'

df = pd.read_csv(TEST_PATH, sep='\t', names=['pid', 'signal', 'time_0', 'value_0', 'unit', 'source', 'add'])
df_minimal = df.drop(columns=['signal', 'unit', 'add']).copy() #signal, unit all same value
#print(df_minimal.source.value_counts())
#Test(df, None, None, OUTPUT_PATH)

hist_all = pd.read_csv(os.path.join(OUTPUT_PATH, 'hist_all.csv'))
current_hist = pd.read_csv(os.path.join(OUTPUT_PATH, 'current_hist.3.csv'))
bins_sz,kld_res,kld_uniform,entropy_p=calc_kld(hist_all,current_hist ,'value_0', 'p')
bins_sz2,kld_res2=calc_distribution_distance(hist_all,current_hist ,'value_0', 'p')

print(kld_res)
print(kld_res2)