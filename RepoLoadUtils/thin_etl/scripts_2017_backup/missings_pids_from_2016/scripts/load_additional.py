#!/bin/python
import sys, os
sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils', 'thin_etl'))
from signal_full_api import *
from flow_api import create_id2nr
import signal_fix_special
from create_dictionaries import *
#Edit Configuration.py, copy all configs files from old (used cp_all_configs.sh, or can copy old config_folder) adn edit needed files #DONE

#create_id2nr(2017, 20801688)
#loadSpecificSignal('.') #DONE
#loadSpecificSignal('38DE[\.0]', 1) #DONE
#addMissingSignals() #DONE
#print('exit for now')
#sys.exit()
#load_pvi() #DONE
#load_imms() #DONE
#load_medical() #DONE
#load_therapy() #DONE
#load_clinical() #DONE
#load_registry() #DONE
#load_smoking() #DONE
#confrim Chads2 chad2_vel #DONE
#load_hospitalizations()
#confirm RDW - it's still categorial in thin. example TST003 #DONE

#unite_signals('GFR')
#fixSignal('GFR')
#fixSignal('eGFR')
#unite_signals('CHADS2')
#fixSignal('CHADS2_VASC')
#unite_all_signal() #DONE
#fixAllSignal()
#signal_fix_special.fixSignal('TEMP', signal_fix_special.fix_factors)
#fixSignal('Fibrinogen')
#fixSignal('FreeT4')
#fixSignal('MCH')
#fixSignal('MCV')
#fixSignal('T4')
#saveUnitsForAllSignals() #Not mandatory - DONE
#allStatuses, allMsgs = doAll() #DONE
#run on ['TEMP'] by hand look for errors inserver - run again on errors #DONE
#look for compare results with old thin #DONE
#sys.exit()
#create_pvi_dict()
#create_drugs_dict()
#create_drugs_nice_names()
#create_readcode_dict()
#create_hospitalization_dict()

#run catecorial load:
#loadAllSpecialSignals() #DONE
#print('cleaning not found keys...')
#cleanNotFoundKeys() #DONE
#print('sorting values in each file...')
#sortValues() #DONE

#tuples = buildAhdLookup()

#use create_dictionary.py to create config files for the repository - check for all dictionaries #DONE
#create config files (convert_config, thin.signals) #DONE
#create repository with Flow#DONE

#Complete signals
old_base_rep = '/home/Repositories/THIN/thin_mar2017/thin.repository'
new_rep = '/server/Temp/Thin_2017_Loading/repository_data_final/thin.repository'
reps = [old_base_rep, new_rep]
#compareRepositories(reps)

#loadSpecificSignal('44M[CEG]\.00')
#unite_signals('TroponinT')
#fixSignal('TroponinI')
