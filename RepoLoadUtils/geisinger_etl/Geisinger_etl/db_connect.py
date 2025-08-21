import pyodbc


class DB:
    def __init__(self):
        self.host = ''
        self.port=1433
        self.user = ''
        self.password= ''
        self.dbname = ''
        self.default_batch_size=5000000


    def get_connect(self):
        cnxn = pyodbc.connect(driver='{FreeTDS}',
                              host=self.host, 
                              port=self.port, 
                              database=self.dbname,
                              password=self.password,
                              user=self.user)
        return cnxn
