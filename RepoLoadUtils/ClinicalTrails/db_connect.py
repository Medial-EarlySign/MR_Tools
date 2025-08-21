from sqlalchemy import engine_from_config


class DB_shula:
    def __init__(self):
        self.host = '192.168.102.41'
        self.port = 1443
        self.username = 'postgres'
        self.password = ''
        self.default_batch_size = 5000000


    #def get_connect(self):
    def get_url(self, dbname):
        uri_psql = 'postgresql+psycopg2://' + self.username + ':' + self.password + '@' + self.host + ':5432/' + dbname
        return uri_psql

    def get_engine(self, dbname):
        config = {
            "sqlalchemy.url": 'postgresql://' + self.username + ':' + self.password + '@' + self.host + ':5432/' + dbname,
            "sqlalchemy.echo": True,
            "sqlalchemy.server_side_cursors": True,
        }
        engine = engine_from_config(config)
        return engine
