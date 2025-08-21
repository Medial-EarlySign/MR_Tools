import os
#change to read, configure from config file. put in workdir, rep.signals for local override
FULL_SIGNALS_TYPES=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rep_signals', 'general.signals')
#FULL_SIGNALS_TYPES='/nas1/Work/CancerData/Repositories/general/general.signals'
BASE_DICT_PATH=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dicts')
FORCED_SIGNALS=['BDATE', 'GENDER']