import asyncio
import os
import sys

BASE_PTH = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE_PTH)
from file_csv_parser import parse_file_content, parse_file_content_non_dist
from ui import get_age_from_info, get_age_from_info_avg

with open(os.path.join(BASE_PTH, 'tests', 'data', 'stratas.Frieburb_exact.csv')) as fr:
    file_content = fr.read()
strata = parse_file_content(file_content, min_obs=200)

with open(os.path.join(BASE_PTH, 'tests', 'data', 'final_data', 'Japan_full_incidence_rate.all_debug.csv')) as fr:
    file_content = fr.read()
strata_inc = parse_file_content_non_dist(file_content)
print('Start calc')
df_res = asyncio.run(get_age_from_info(strata))
print(df_res)


df = asyncio.run(get_age_from_info_avg(df_res, strata_inc))
print(df)
