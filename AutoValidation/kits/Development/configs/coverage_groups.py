eGFR=getcol(df, 'eGFR_CKD_EPI.last.win_0_360')

#hgb=getcol(df, 'Hemoglobin.last.win_0_360')

#Define Groups
cohort_f['Age:70-75, eGFR<65']= (df.Age>=70) & (df.Age<=75) & (df[eGFR]<65)
