#!/bin/python
import sys, os
sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils', 'thin_etl'))
from signal_full_api import *
from create_dictionaries import *
#Edit Configuration.py, copy all configs files from old (used cp_all_configs.sh, or can copy old config_folder) adn edit needed files #DONE

#loadSpecificSignal('.') #DONE
#loadSpecificSignal('38DE[\.0]', 1) #DONE
#addMissingSignals() #DONE
#load_pvi_signals() #DONE
#load_smoke_alcohol()
#load_imms() #DONE
#load_medical() #DONE
#load_therapy() #DONE
#load_clinical() #DONE
#load_registry() #DONE
#confrim Chads2 chad2_vel #DONE

#confirm RDW - it's still categorial in thin. exampl TST003 #DONE

#unite_all_signal() #DONE
#saveUnitsForAllSignals() #Not mandatory - DONE
#allStatuses, allMsgs = doAll() #DONE
#run on ['TEMP'] by hand look for errors inserver - run again on errors #DONE
#look for compare results with old thin #DONE

#run catecorial load:
#loadAllSpecialSignals() #DONE
#print('cleaning not found keys...')
#cleanNotFoundKeys() #DONE
#print('sorting values in each file...')
#sortValues() #DONE

#use create_dictionary.py to create config files for the repository - check for all dictionaries #DONE
#create config files (convert_config, thin.signals) #DONE
#create repository with Flow#DONE

#create_pvi_dict()
#create_drugs_dict()
#create_drugs_nice_names()

#Complete signals
#old_base_rep = '/home/Repositories/THIN/thin_mar2017/thin.repository'
#new_rep = '/server/Temp/Thin_2017_Loading/repository_data_final/thin.repository'
#reps = [old_base_rep, new_rep]
#compareRepositories(reps) #comapre all signals
#compareRepositories(reps, ['RDW'])

parseAllSignal(aggBy = 'medcode')
analyzeAllAhdCodes(aggBy = 'medcode')
addAhdCodeNames(aggBy = 'medcode')

loadSpecificSignal('44M[CEG]\.00')
