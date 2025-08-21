from sqlalchemy import create_engine, text
import pandas as pd
import html2text, re

def fetch_html(x):
  h = html2text.HTML2Text()
  cdata=re.compile(r'<!\[CDATA\[(.*?)\]\]>', re.DOTALL)
  return h.handle(cdata.sub(r'\1',x))

class DB_Access:
  def __init__(self, connection_string):
    self.connection_string=connection_string
    self.engine=None
    self.conn=None
  def connect(self):
    if self.engine is None:
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
  def __execute_query(self, query, batch_size=None):
    if self.conn is None:
      print('Connection before execute query in first time')
      self.connect()
    #print(f'Execute {query}\nbatch_size={batch_size}')
    df = pd.read_sql_query(query, self.conn, chunksize=batch_size)
    return df

  def fetch_data(self, batch_size=None):
      sql="WITH all_pages as(SELECT * FROM confdb.dbo.CONTENT WHERE SPACEID=2359297 and CONTENTTYPE='PAGE') SELECT BC.*, AP.TITLE, AP.CONTENT_STATUS, AP.LASTMODDATE, AP.PARENTID FROM confdb.dbo.BODYCONTENT BC JOIN all_pages AP on BC.CONTENTID =AP.CONTENTID WHERE CONTENT_STATUS!='deleted'"
      res = self.__execute_query(text(sql), batch_size)
      print('Fetch text')
      res['text']=res['BODY'].apply(fetch_html).apply(lambda x: x.strip())
      res = res[(res['text']!='') & (res['text'].notna())].reset_index(drop=True)
      return res
    
if __name__=='__main__':
    CONNECTION_STRING='mssql+pyodbc://confuser:2w#E#E2w@confluence'
    db=DB_Access(CONNECTION_STRING)
    res=db.fetch_data()
    #res=res[['TITLE', 'LASTMODDATE', 'text']]