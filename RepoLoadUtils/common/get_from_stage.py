import pandas as pd
from sql_utils import create_engine


def get_itemid_units(db_engine, table, itemid):
    sql_query = "SELECT DISTINCT(unit) FROM " + table + " WHERE code = " + str(itemid)
    if db_engine == 'FILE':
        df = pd.read_csv(table, sep='\t')
        df=df[df['code']==itemid].reset_index(drop=True)
    else:
        df = pd.read_sql(sql_query, db_engine)
    print(df)
    return list(df['unit'].values)


def get_all_pids(db_engine, table):
    sql_query = 'SELECT orig_pid from ' + table
    if db_engine == 'FILE':
        df = pd.read_csv(table, sep='\t')
        df=df[['orig_pid']]
    else:
        df = pd.read_sql(sql_query, db_engine)
    return df['orig_pid'].unique().tolist()


def get_values_for_code(db_engine, table, codes):
    sql_query = "SELECT * FROM " + table + " WHERE code in ('" + "','".join(codes) + "')"
    print(sql_query)
    if db_engine == 'FILE':
        df = pd.read_csv(table, sep='\t')
        df=df[df['code'].isin(codes)].reset_index(drop=True)
    else:
        df = pd.read_sql(sql_query, db_engine)
    return df


def get_values_for_one_code(db_engine, table, code):
    sql_query = "SELECT * FROM " + table + " WHERE code = '" + code + "'"
    if db_engine == 'FILE':
        df = pd.read_csv(table, sep='\t')
        df=df[df['code']==code].reset_index(drop=True)
    else:
        df = pd.read_sql(sql_query, db_engine)
    return df


def get_column_vals(db_engine, table, column):
    sql_query = "SELECT orig_pid, " + column.lower() + " as value FROM " + table
    if db_engine == 'FILE':
        df = pd.read_csv(table, sep='\t')
        df = df[['orig_pid', column]].rename(columns={column: 'value'})
    else:
        df = pd.read_sql(sql_query, db_engine)
    return df


if __name__ == '__main__':
    get_all_pids()
    #get_labs_values(['Base Excess', 'Lactate'])
