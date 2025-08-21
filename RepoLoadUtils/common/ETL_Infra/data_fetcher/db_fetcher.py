import pandas as pd

from sqlalchemy import create_engine
import pandas as pd
from typing import Dict, Generator, Optional

#Helper
def postgres_connection_string(user:str, password:str, host:str, port:int, database:str):
    connection_string=f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    return connection_string

"""
A Helper class to handle database access.
"""
class DB_Access:
  def __init__(self, connection_string:str, connect_args = None):
    """
    Initialize database object with conncetion string
    
    :param connection_string: the connection string
    :param connect_args: Additional connection arguments to sqlalchemy "connect_args" in create_engine
    """
    self.connection_string=connection_string
    self.conn_args = connect_args
    self.engine=None
    self.conn=None
    
  def connect(self):
    if self.engine is None:
      if self.conn_args is not None:
        self.engine = create_engine(self.connection_string, connect_args = self.conn_args)
      else:
        self.engine = create_engine(self.connection_string)
      print('Created engine')
    if self.conn is None:
      self.conn = self.engine.connect().execution_options(stream_results=True)
      print('Created connection')
  def close(self):
    if self.conn is not None:
      self.conn.close()
      print('Closed connection')
    #if self.engine is not None:
    #  self.engine.dispose()
    #  print('Closed engine')
    self.conn=None
    #self.engine=None
  def __del__(self):
    self.close()
  def execute_query(self, query:str, batch_size:Optional[int]= None):
    if self.conn is None:
      print('Connection before execute query in first time')
      self.connect()
    #print(f'Execute {query}\nbatch_size={batch_size}')
    if batch_size == 0:
      batch_size = None
    df = pd.read_sql_query(query, self.conn, chunksize=batch_size)
    return df


def db_fetcher(db:DB_Access, sql_query:str, batch_size:int, start_batch:int, batch_mapper:Dict[int,str]) \
    -> Generator[pd.DataFrame,None,None]:
    """
    A helper function to retrieve data from DB in batches.\n
    This will add sorting of the query by "pid" to allow fetching in batches\n
    and continue from where we stoped. It will store last patient id \n
    we reached in each batch under batch_mapper
    
    :param db: The database object DB_Access
    :param sql_query: The sql query to fetch results
    :param batch_size: The size of the batch, number of rows to read from each batch
    :param start_batch: The starting point, to continue exection from the middle
    :param batch_mapper: A dictionary to map batch starting point to last patient id read in that batch
    :return: lazy data iterator to retrieve the data
    """
    #Handle query - assume have pid
    if batch_size == 0 or start_batch not in batch_mapper: #first batch or no batches:
        sql_query=f'SELECT * from ({sql_query}) tmp ORDER by pid'
    else:
        if start_batch not in batch_mapper:
           if start_batch > 0:
              raise NameError('Warning batch_mapper has no memory')
           else:
              last_pid = None
        else:
          last_pid=batch_mapper[start_batch]
        if last_pid is None:
           sql_query=f'SELECT * from ({sql_query}) tmp ORDER by pid'
        else:
          if type(last_pid) == str:
              sql_query=f'SELECT * from ({sql_query}) tmp WHERE pid >= \'{last_pid}\' ORDER by pid'
          else:
              sql_query=f'SELECT * from ({sql_query}) tmp WHERE pid >= {last_pid} ORDER by pid'
    for idx_fetch_batch, data in enumerate(_db_fetcher(db, sql_query, batch_size)):
        if 'pid' not in data.columns:
            raise NameError('DataFrame must return pid column')
        last_pid=data['pid'].max()
        batch_mapper[start_batch+1]=last_pid
        yield data



def _db_fetcher(db:DB_Access, sql_query:str, batch_size:int) -> Generator[pd.DataFrame,None,None]:
    df_iterator = db.execute_query(sql_query, batch_size)
    if type(df_iterator) == type(pd.DataFrame()):
        print('No batches - process all in one batch')
        yield df_iterator
        return
    for idx_fetch_batch, data in enumerate(df_iterator):
        print('Process batch %d'%(idx_fetch_batch+1), flush=True)
        yield data
