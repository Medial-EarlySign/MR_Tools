import sys
from datetime import datetime

class Logger(object):
    def __init__(self, filename, prefix=None):
        self.terminal = sys.__stdout__
        self.log = open(filename, 'a')
        self.log_prefix=prefix
        self.start_line=True
    def write(self, message):
        if self.terminal is None:
            raise RuntimeError('Logger has been closed, cannot write to it anymore.')
        if self.log is None:
            raise RuntimeError('Logger has been closed, cannot write to it anymore.')
        self.terminal.write(message)
        if not(self.start_line):
            self.log.write(message)
        else:
            if self.log_prefix is not None:
                self.log.write(f'{datetime.now()} :: {self.log_prefix} :: {message}')
            else:
                self.log.write(f'{datetime.now()} :: {message}')
        self.start_line=message.endswith('\n')
    def flush(self):
        if self.terminal is None:
            raise RuntimeError('Logger has been closed, cannot write to it anymore.')
        self.terminal.flush()
        if self.log is not None:
            self.log.flush()
    def __del__(self):
        if self.log is not None:
            self.log.close()
        self.log=None
        sys.stdout=sys.__stdout__
        
class Tee(object):
  def __init__(self):
    self.log = None
  def __del__(self):
    if self.log is not None:
        self.log.close()
    self.log=None
  def write(self, data):
    if self.log is None or sys.__stdout__ is None:
      raise RuntimeError('Logger has been closed, cannot write to it anymore.')
    if type(data) == bytes:
      data = data.decode('utf-8')
    self.log.write(data)
    sys.__stdout__.write(data)
  def flush(self):
    if self.log is not None:
      self.log.flush()
    if sys.__stdout__ is not None:
      sys.__stdout__.flush()
    if sys.__stderr__ is not None:
      sys.__stderr__.flush()
  def isatty(self):
      return True
  def fileno(self):
      if self.log is not None:
          return self.log.fileno()
      else:
          return 0
  def change_log_file(self, log_file, mode='w'):
      if self.log is not None:
          self.log.close()
      self.log=open(log_file, mode)    
  def close_log(self):
      if self.log is not None:
          self.log.close()
          self.log=None
  encoding='utf-8'