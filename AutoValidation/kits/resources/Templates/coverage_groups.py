pack_years=getcol(df, 'Smoking.Smok_Pack_Years')
smok_years=getcol(df, 'Smoking.Smoking_Years')
copd_feat=getcol(df, '490-496.win_0_1095')
copd_1_year=getcol(df, '490-496.win_0_365')
#hgb=getcol(df, 'Hemoglobin.last.win_0_360')

#Define Groups
#cohort_f['Age:70-75, hgb<9']= (df.Age>=70) & (df.Age<=75) & (df[hgb]<9)
cohort_f['Age:70-75, pack_years+smoking_years above 30, copd'] = (df.Age>=70) & (df.Age<=75) & ( df[pack_years] > 30) & (df[smok_years]>30) & (df[copd_feat] > 0)
cohort_f['Age:70-75, pack_years+smoking_years above 30, copd_1_y_3'] = (df.Age>=70) & (df.Age<=75) & ( df[pack_years] > 30) & (df[smok_years]>30) & (df[copd_1_year] > 2)
cohort_f['Age:70-75, pack_years+smoking_years above 40, copd'] = (df.Age>=70) & (df.Age<=75) & ( df[pack_years] > 40) & (df[smok_years]>40) & (df[copd_feat] > 0)