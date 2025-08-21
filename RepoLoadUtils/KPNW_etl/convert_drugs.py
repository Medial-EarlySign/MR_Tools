#!/opt/medial/dist/usr/bin/python
import sys
import pyreadstat
import pandas as pd
import time


read_file = sys.argv[1]
out_file = sys.argv[2]
mode = sys.argv[3]

start = time.time()
print("Now reading file ", read_file)
df = pyreadstat.read_sas7bdat(read_file)
end = time.time()
print("Read file in ", end-start , "seconds")
print(df[0].shape)

df[0].PAT_ID_GEN = df[0].PAT_ID_GEN.astype(int)
header = ["PAT_ID_GEN","DESCRIPTION","GPI","NDC_CODE","SIG","QUANTITY","REFILLS","START_DATE","END_DATE","DISPLAY_NAME"]

print("Writing to ", out_file)
if (mode == 'a'):
	df[0].to_csv(out_file, columns=header, sep='\t', index=False, date_format='%Y%m%d', header=False, mode='a')
else:
	df[0].to_csv(out_file, columns=header, sep='\t', index=False, date_format='%Y%m%d')

print("DONE : wrote to file ", out_file)

