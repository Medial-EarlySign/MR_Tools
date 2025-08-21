#!/usr/bin/env python
import os
from ETL_Infra.etl_process import *
from denmark_parser import *
#END of imports
from datetime import datetime #Just for measuring time

#Should be in denmark_parser, but it's not needed, just demonstration
from data_fetcher.files_fetcher import big_files_fetcher
#Added to pd.read_csv: skiprows, chunksize and iterate processing with loop + yield return each batch
def labs_file_parser_lazy(filepath,batch_size, start_from_row):
    #When read with skip rows, keep in min that the header is not read again
    df_iterator = pd.read_csv(filepath, names= ['pid', 'index_date', 'lab_date', 'lab_name', 'value_0', 'lab_name_unfiltered'], \
                     skiprows = start_from_row, chunksize=batch_size)
    for df in df_iterator:
        df['signal'] = df['lab_name'] + '::' + df['lab_name_unfiltered']
        df.loc[df['signal'].isnull(), 'signal']= df['lab_name_unfiltered']
        yield df

def big_labs_data_fetcher(start_batch, batch_size):
    #files = list_files('pop2_datasetC_labresults_firstvisit_for_all')
    files = list_files('pop2_datasetB_labresults_firstvisit_for_controls_LCdate_for_cases')
    return big_files_fetcher(files, batch_size, labs_file_parser_lazy, start_batch)
#END


print(">>> list_files('Pop2_datasetA')")
print(list_files('Pop2_datasetA'))

#Let's use labs_data_fetcher to fetch labs in batches - The batch is "with" #of files.
#we can use "big_files_fetcher" to fetch  number of rows
batch_size = 10000

print(f"We will create a data_fetcher for labs, starting from batch 0, and batch size is {batch_size}")
print(">>> data_fetcher = labs_data_fetcher(0, batch_size)")
st_time = datetime.now()
data_fetcher = big_labs_data_fetcher(0, batch_size)
#data_fetcher = labs_data_fetcher(0, batch_size)
ed_time = datetime.now()
print(f'Took {(ed_time-st_time).total_seconds()} to run - very fast, "lazy evaluation"')

print("Now, we will call the first batch, we can iterate on all result with for loop")
print(">>> df = next(data_fetcher)")
st_time = datetime.now()
df = next(data_fetcher)
ed_time = datetime.now()
print(f'Took {(ed_time-st_time).total_seconds()} to get batch')
print("Now, we will call the second batch, we can iterate on all result with for loop")
print(">>> df2 = next(data_fetcher)")
st_time = datetime.now()
df2 = next(data_fetcher)
ed_time = datetime.now()
print(f'Took {(ed_time-st_time).total_seconds()} to get batch')

print("Here is df:")
print(">>> df")
print(df)
print("Here is df2:")
print(">>> df2")
print(df2)

