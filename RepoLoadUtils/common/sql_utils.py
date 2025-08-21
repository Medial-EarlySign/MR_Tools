from sqlalchemy import create_engine
import d6tstack
from sqlalchemy import engine_from_config

class DBFile_mock:
    def __init__(self, base_path):
        self.base_path=base_path

def get_sql_engine(SQL_SERVER, DBNAME,  username='', password=''):
    if SQL_SERVER == 'MSSQL':
        return create_mssql_engine(DBNAME, username, password)
    elif SQL_SERVER == 'POSTGRESSQL':
        return create_postgres_engine(DBNAME, username, password)
    elif SQL_SERVER == 'D6_POSTGRESSQL':
        return create_postgres_url(DBNAME, username, password)
    elif SQL_SERVER == 'D6_POSTGRESSQL_SHULA':
        return create_postgres_url(DBNAME, username, '', server='192.168.102.41')
    elif SQL_SERVER == 'FILE':
        return DBFile_mock(DBNAME)
        #return create_postgres_engine_config(DBNAME, username, '', server='192.168.102.41')
    print(SQL_SERVER + ' Unkowen source')


def create_postgres_engine(dbname, username, password, server='node-03'):
    engine = create_engine('postgresql://'+username+':'+password+'@'+server+':5432/'+dbname)
    return engine


def create_postgres_engine_config(dbname, username, password, server):
    config = {
        "sqlalchemy.url": 'postgresql://'+username+':'+password+'@'+server+':5432/'+dbname,
        "sqlalchemy.echo": False,
        "sqlalchemy.server_side_cursors": True,
    }
    engine = engine_from_config(config)
    return engine


def create_mssql_engine(dbname, username, password):
    #engine = create_engine('mssql+pymssql://MEDIAL\\tamard:!QAZ2wsx@server:4096/RawTHIN1801')
    engine = create_engine('mssql+pymssql://server/'+dbname)
    return engine


def create_postgres_url(dbname, username, password, server='node-03'):
    uri_psql = 'postgresql+psycopg2://'+username+':'+password+'@'+server+':5432/'+dbname
    return uri_psql


def pd_to_sql(SERVER_TYPE, df, db_engine, table,  if_exists='replace'):
    if SERVER_TYPE.startswith('D6_POSTGRESSQL'):
        d6tstack.utils.pd_to_psql(df, db_engine, table, if_exists=if_exists)
    else:
        df.to_sql(table, db_engine, if_exists=if_exists, index=False)


def sql_create_table(db_def):
    server = 'node-03'
    if 'SHULA' in db_def.DBTYPE:
        server = '192.168.102.41'
    create_db_engine = create_postgres_engine(db_def.DBNAME, db_def.username, db_def.password, server=server)
    #create_db_engine = get_sql_engine(db_def.DBTYPE, db_def.DBNAME, db_def.username, db_def.password)
    sql_drop = 'DROP TABLE IF EXISTS public.' + db_def.TABLE + ' CASCADE;'
    sql_create = 'CREATE TABLE public.' + db_def.TABLE + ' ('
    for col_name, col_type in zip(db_def.COLUMNS, db_def.COL_TYPES):
        sql_create = sql_create + col_name + " " + col_type + ", "
    sql_create = sql_create[:-2] + ');'
    print(sql_drop)
    create_db_engine.execute(sql_drop)
    print(sql_create)
    create_db_engine.execute(sql_create)
