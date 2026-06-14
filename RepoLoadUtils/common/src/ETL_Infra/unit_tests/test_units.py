from ETL_Infra.unit_conversions import find_best_unit_suggestion, find_best_unit_suggestion_to_group
import pandas as pd

#current_dir = os.path.dirname(os.path.dirname(__file__))
#cfg=pd.read_csv(os.path.join(current_dir, 'rep_signals', 'unit_suggestions.cfg'), sep='\t', names=['signal', 'factor', 'description'])

#df = pd.read_csv('/nas1/Work/Users/Eitan/thin_2021_loading/FinalSignals/Urea.0', sep='\t', names=['pid', 'signal', 'time_0', 'value_0', 'source', 'unit', 'unit_name', 'other_1', 'other_2'])
df = pd.read_csv('/nas1/Work/Users/Eitan/thin_2021_loading/FinalSignals/Hemoglobin.0', sep='\t', names=['pid', 'signal', 'time_0', 'value_0', 'source', 'unit', 'unit_name', 'other_1', 'other_2'])
print('Finished reading df')
df['value_0'] = df['value_0'] * 10

#optional_factors = [1, 2.14, 2.8, 6, 12.84]
#optional_factors = cfg[cfg['signal']=='Urea']['factor'].values
#optional_factors = list(map(lambda x: [0, x, 'Temp'],optional_factors))
#optional_factors = None
res=find_best_unit_suggestion(df)
res_full=find_best_unit_suggestion_to_group(df, diff_threshold_percentage=1000, diff_threshold_ratio=1000)

#print(res)
for k,v in res.items():
    txt_res = '\n'.join(map(lambda x:str(x), v))
    print(f'For {k} result: \n{txt_res}')
print('All options')
print('\n'.join(map(lambda x: str(x),res_full)))