import pandas as pd
import os, gzip

def read_table_united(base_path, table_prefix_name, columns, process_function=None, write_batch=0, output_path_prefix=None, _use_cols=None, sort_by=['pid']):
    files = list(filter(lambda x : x.startswith(table_prefix_name) , os.listdir(base_path)))
    files = sorted(files, key=lambda x : int(x.split('.')[-2][10:]) )
    all_data=None
    batch_num=1
    for file in files:
        full_f=os.path.join(base_path, file)
        print('Process file %s'%(full_f), flush=True)
        if _use_cols is not None:
            data=pd.read_csv(full_f, compression='gzip', sep='|', header=None, index_col=False, names=columns, usecols=_use_cols)
        else:
            data=pd.read_csv(full_f, compression='gzip', sep='|', header=None, index_col=False, names=columns)
        if process_function is not None:
            data=process_function(data)
        if all_data is None:
            all_data=data.drop_duplicates().reset_index(drop=True)
        else:
            all_data=all_data.append(data, ignore_index=True).drop_duplicates().reset_index(drop=True)
        #check batch:
        if output_path_prefix is not None and write_batch > 0:
            if len(all_data) > write_batch:
                all_data.iloc[:write_batch].sort_values(sort_by).to_csv(output_path_prefix + '.' + str(batch_num) + '.tsv', sep ='\t', index=False, header=False)
                print('Wrote batch %d, size=%d'%(batch_num, len(all_data)), flush=True)
                all_data = all_data.iloc[write_batch:].reset_index(drop=True)
                batch_num = batch_num + 1
                while len(all_data)>write_batch:
                    print('WARN: batch size too small... writing another batch left size of %d'%(len(all_data)), flush=True)
                    all_data.iloc[:write_batch].sort_values(sort_by).to_csv(output_path_prefix + '.' + str(batch_num) + '.tsv', sep ='\t', index=False, header=False)
                    print('Wrote batch %d, size=%d'%(batch_num, len(all_data)), flush=True)
                    all_data = all_data.iloc[write_batch:].reset_index(drop=True)
                    batch_num = batch_num + 1
    #last batch:
    if output_path_prefix is not None:
        name=output_path_prefix + '.' + str(batch_num) + '.tsv'
        if write_batch == 0:
            name=output_path_prefix + '.tsv'
        all_data.drop_duplicates().reset_index(drop=True).sort_values(sort_by).to_csv(name, sep ='\t', index=False, header=False)
        print('Wrote last batch %d, size=%d'%(batch_num, len(all_data)), flush=True)
    return all_data

def read_column_united(base_path, table_prefix_name, columns, cols):
    files = list(filter(lambda x : x.startswith(table_prefix_name) , os.listdir(base_path)))
    files = sorted(files, key=lambda x : int(x.split('.')[-2][10:]) )
    all_data=None
    batch_num=1
    for file in files:
        full_f=os.path.join(base_path, file)
        print('Process file %s'%(full_f), flush=True)
        data=pd.read_csv(full_f, compression='gzip', sep='|', header=None, index_col=False, names=columns, usecols=cols)
        data['cnt']=1
        data=data.groupby(cols).count().reset_index()
        data['file']=file
        if all_data is None:
            all_data=data
        else:
            all_data=all_data.append(data, ignore_index=True)
        del data
    return all_data

