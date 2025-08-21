import pymssql
import sys

MSSQL = "mssql"
POSTGRES = "postgres"


class SQLAdapter(object):

    '''
    Handles different SQL sessions
    '''

    def __init__(self, db_type):
        '''
        Constructor
        '''
        self.fetch_size = 1
        self.db_type = db_type
        if (db_type == MSSQL):
            self.sql_package = pymssql
        elif (db_type == POSTGRES):
            self.sql_package = psycopg2
        else:
            print('Error: Not a supported sql database type')
            sys.exit(1)
        return

    def connect(self, db_name, server_name=None, username=SQLDB_USER_NAME, password=SQLDB_USER_PASSWORD, char_set="UTF-8"):
        try:
            if (server_name is not None):
                self.con = self.sql_package.connect(
                    server=server_name, database=db_name,  user=username, password=password)
#                 self.con = self.sql_package.connect(
#                     server=server_name, database=db_name,  user=username, password=password, charset=char_set)
            else:
                self.con = self.sql_package.connect(
                    database=db_name,  user=username, password=password)

        except self.sql_package.DatabaseError as e:
            print('Error %s' % e)
            sys.exit(1)
        return self

    def close(self):
        return self.con.close()

    def commit(self):
        try:
            self.con.commit()
        except self.sql_package.DatabaseError as e:
            print('Error %s' % e)
            sys.exit(1)

    def autocommit(self, is_true=True):
        try:
            self.con.autocommit(is_true)
        except self.sql_package.DatabaseError as e:
            print('Error %s' % e)
            sys.exit(1)

    def sql_query(self, sql, curtype='list'):
        if 'list' in curtype:
            cur = self.list_cursor()
        elif 'dict' in curtype:
            cur = self.real_dict_cursor()
        else:
            print('Error: cursor type is not defined %s' % curtype)
            sys.exit(1)
        cur.execute(sql)
        return cur.fetchall()

    def sql_query_execute(self, sql, curtype='list'):
        if 'list' in curtype:
            cur = self.list_cursor()
        elif 'dict' in curtype:
            cur = self.real_dict_cursor()
        else:
            print('Error: cursor type is not defined %s' % curtype)
            sys.exit(1)
        cur.execute(sql)
        return cur

    def set_fetch_size(self, size):
        self.fetch_size = size

    def sql_query_fetch(self, cur, size=0):
        if size == 0:
            size = self.fetch_size
        return cur.fetchmany(size)

    def cursor(self):
        try:
            c = self.con.cursor()
        except self.sql_package.DatabaseError as e:
            print('Error %s' % e)
            sys.exit(1)
        return c

    def list_cursor(self):
        if (self.db_type == MSSQL):
            return self.con.cursor(as_dict=False)
        elif (self.db_type == POSTGRES):
            return self.con.cursor()

    def real_dict_cursor(self):
        if (self.db_type == MSSQL):
            return self.con.cursor(as_dict=True)
        elif (self.db_type == POSTGRES):
            return self.con.cursor(cursor_factory=RealDictCursor)
