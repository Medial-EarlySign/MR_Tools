import pandas as pd
import os
from math import sqrt

if __name__ == '__main__':
    in_file = 'distribution_compare.csv'
    out_file = 'distribution_compare_tscore.csv'
    if not os.path.exists(in_file):
        print('File does not exist craeting it...')
        # numeric_new_dates_compare(out_file, new_dates_start, byear_start, byear_end)
    df = pd.read_csv(in_file)
    df.drop(labels='hist', axis=1, inplace=True)
    grp = df.groupby('signal')
    for name, group in grp:
        pop_mean = group[group['population'] == 'old repository']['mean'].iloc[0]
        for i, row in group.iterrows():
            df.at[i, 't_score'] = (row['mean'] - pop_mean)/(row['std']/sqrt(row['count']))
        print(name)
        #print(group)

    df.to_csv(out_file)

