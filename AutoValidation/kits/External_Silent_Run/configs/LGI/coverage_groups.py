hgb = getcol(df, 'Hemoglobin.last.win_0_10000')
hgb_trend = getcol(df, 'Hemoglobin.slope.win_0_730')
plat_trend = getcol(df, 'Platelets.win_delta.win_0_180_730_10000')
mch = getcol(df, 'MCH.min.win_0_180')
mch_trend = getcol(df, 'MCH.slope.win_0_730')

#Define Groups

cohort_f['Age:60-75'] = (df.Age >=60) 
cohort_f['Age:45-60'] = (df.Age < 60)
cohort_f['hgb < 11'] = (df[hgb] > 0)  & (df[hgb] < 11)
cohort_f['hgb_trend < -2'] = (df[hgb_trend] > -65336) & (df[hgb_trend] < -2)

cohort_f['Age:60-75, hgb < 11'] = (df.Age >=60) & (df[hgb] > 0)  & (df[hgb] < 11)
cohort_f['Age:45-60, hgb < 11'] = (df.Age < 60) & (df[hgb] > 0)  & (df[hgb] < 11)

cohort_f['Age:60-75, hgb_trend < -2'] = (df.Age >=60) & (df[hgb_trend] > -65336) & (df[hgb_trend] < -2)
cohort_f['Age:45-60, hgb_trend < -2'] = (df.Age < 60) & (df[hgb_trend] > -65336) & (df[hgb_trend] < -2)

# cohort_f['Age:60-75, mch < 24'] = (df.Age>=60) & (df.Age<=75) & (df[mch] < 24)
# cohort_f['Age:00-60, mch < 24'] = (df.Age<60) & (df[mch] < 24)

# cohort_f['Age:60-75, mch_trend < -1.5'] = (df.Age>=60) & (df.Age<=75) & (df[mch_trend] < -1.5)
# cohort_f['Age:00-60, mch_trend < -1.5'] = (df.Age<60) & (df[mch_trend] < -1.5)

# cohort_f['Age:60-75, hgb < 11'] = (df.Age>=60) & (df.Age<=75) & (df[hgb] < 11)
# cohort_f['Age:00-60, hgb < 11'] = (df.Age<60) & (df[hgb] < 11)


cohort_f['Age:70-75, plat_trend > 50'] = (df.Age>=70) & (df.Age<=75) & (df[plat_trend] > 50)
