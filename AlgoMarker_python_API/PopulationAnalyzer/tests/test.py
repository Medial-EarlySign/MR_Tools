import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from logic import full_run, StrataStats, Strata, StrataRange, StrateCategory
import pandas as pd

stratas = []
stratas.append(StrataStats(stratas=[StrataRange(feature_name="age", min_range=0, max_range=50), StrateCategory(feature_name="gender", categoty_value="1")], prob=0.25)) 
stratas.append(StrataStats(stratas=[StrataRange(feature_name="age", min_range=0, max_range=50), StrateCategory(feature_name="gender", categoty_value="2")], prob=0.25)) 
stratas.append(StrataStats(stratas=[StrataRange(feature_name="age", min_range=50, max_range=100), StrateCategory(feature_name="gender", categoty_value="1")], prob=0.25)) 
stratas.append(StrataStats(stratas=[StrataRange(feature_name="age", min_range=50, max_range=100), StrateCategory(feature_name="gender", categoty_value="2")], prob=0.24)) 
stratas.append(StrataStats(stratas=[StrataRange(feature_name="age", min_range=120, max_range=200)], prob=0.01)) 
# Read matrix df with age stats:
#df = pd.read_csv('/nas1/Work/Users/eitan/Lung/outputs/models2023/EX3/model_63/bootstrap/reference_features.final.matrix').rename(columns={'outcome_time':'outcomeTime'})
#df=df[['id', 'time' ,'outcome', 'outcometime', 'split', 'pred_0', 'age', 'gender', 'ftr_000003.smoking.current_smoker', 'ftr_000003.smoking.ex_smoker', 'ftr_000003.smoking.never_smoker', 'ftr_000003.smoking.smoking_intensity', 'ftr_000003.smoking.smoking_years', 'ftr_000003.smoking.smok_pack_years_last', 'ftr_000003.smoking.smok_days_since_quitting', 'icd9_diagnosis.category_dep_set_icd9_code:490-496.win_0_10950', 'ftr_000077.bmi.last.win_0_1095']]
#df.to_csv('/nas1/Work/Users/eitan/Lung/outputs/models2023/EX3/model_63/bootstrap/ref_for_pr_analysis.csv', index=False)
df = pd.read_csv('/nas1/Work/Users/eitan/Lung/outputs/models2023/EX3/model_63/bootstrap/ref_for_pr_analysis.csv')
print ('Read csv')
res, prob_not_represented = full_run(df, stratas, None, None, None, 0, [500,1000])

print(f'Not represented: {100*prob_not_represented}%')
print(res)