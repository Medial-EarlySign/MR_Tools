from common import *
from Configuration import Configuration
from signal_mapping_api import listAllTargets, searchSignal, searchSignalAndTarget, commitSignal, getTargetSources, renameSignalMap, confirmSignal, addMissingSignals
from signal_unite_api import unite_signals, unite_all_signal
from signal_config_api import *
from signal_stats_api import statsUnitedSig, statsFixedSig, getSignalUnitRes, getSignalByUnit
from signal_fix_api import fixAllSignal, fixSignal
from signal_unit_api import ignoreRareUnits, compareUnitHist, clearSupportUnits, addAllWithFactor
from signal_parse_api import parseAllSignal, getStatsForCodefile, analyzeAllAhdCodes, addAhdCodeNames
from signal_special_api import loadAllSpecialSignals, sortValues, cleanNotFoundKeys
from flow_api import createResolveFld, createCommonValsFromSum, createCommonVals, saveUnitsForAllSignals, loadSpecificSignal, load_imms, load_medical, load_therapy, load_clinical, load_registry, load_smoking, createNonNumericAHD, add_train_censor, add_splits, load_hospitalizations
from do_all_work import doAll, handleSignal, confirmAlreadyApproved, getAllSignalStatus
from signal_compare_api import compareRepositories
from create_pvi_signals import load_pvi_signals
from create_smoking_alcohol_signals import load_smoke_alcohol
import re

def renameSignal(sig_source, sig_target):
    renameSignalMap(sig_source, sig_target)
    cfg = Configuration()
    work_dir = fixOS(cfg.work_path)
    code_dir = fixOS(cfg.code_folder)
    unitedPath = os.path.join(work_dir, 'United')
    fixedPath = os.path.join(work_dir, 'Fixed')
    if not(os.path.exists(unitedPath)):
        raise NameError('config error - united dir not found')
    if not(os.path.exists(fixedPath)):
        raise NameError('config error - fied dir not found')
    if not(os.path.exists(code_dir)):
        raise NameError('config error - code dir not found')
    f1 = os.path.join(code_dir, 'Instructions.txt')
    f2 = os.path.join(code_dir, 'unitTranslator.txt')
    f3 = os.path.join(code_dir, 'confirm_signals.txt')
    f4 = os.path.join(code_dir, 'codesDependency')
    if not(os.path.exists(f1)) or not(os.path.exists(f2)) or not(os.path.exists(f3)) or not(os.path.exists(f4)):
        raise NameError('config error - config dir not found')
    
    full_unite_path = os.path.join(unitedPath, sig_source)
    if os.path.exists(full_unite_path):
        os.rename(full_unite_path, os.path.join(unitedPath, sig_target))
    full_fixed_path = os.path.join(fixedPath, sig_source)
    if os.path.exists(full_fixed_path):
        os.rename(full_fixed_path, os.path.join(fixedPath, sig_target))
    #search and replace in instructions and unitTraslator, ahd, confirm_signals
    searchAndReplaceFileTxt(f1, sig_source, sig_target)
    searchAndReplaceFileTxt(f2, sig_source, sig_target)
    searchAndReplaceFileTxt(f3, sig_source, sig_target)
    searchAndReplaceFileTxt(f4, sig_source, sig_target)
    
if __name__ == "__main__" and False:
    '''Step 0 - run 300_ahd_resolve_lookups.py and create map_file, look at resolve folder and stats folder for problems '''
    #createResolveFld() #Creates resolved and stats dir from THINDB raw data - NOT NEEDED ANYMORE use loadSpecificSignal
    #createCommonVals() #creates CommonValues file with raw signal stats for mapping - NOT NEEDED ANYMORE use loadSpecificSignal
    loadSpecificSignal('.') #Loads specific signal till Common (skips resolv)
    #fix CHADS2 - the values are in first column - TODO: fix infra to support config column for each signal. for now just run again: loadSpecificSignal('38DE[\.0]', 1). the 1 means in columns 1 and not 2 which is all other signals
    #createNonNumericAHD() # not needed anymore
    addMissingSignals() #add missing signals to mapping file thin_signals_to_united.txt if there are new signals in common
    load_pvi_signals()
    load_imms()
    load_medical()
    load_therapy()
    load_clinical()
    load_registry()
    load_smoke_alcohol()

    #if all is good, no need server to config, run:
    unite_all_signal()
    allStatuses, allMsgs = doAll()
    #run on failed signals by hand
    
    '''Step 1 - map all signal names and edit mapping file''' #Done in server.py - use the  web site
    searchSignalAndTarget('1001400138|Erythrocyte')
    #commitSignal('1001400138|Erythrocyte', 'Erythrocyte')
    
    '''Step 2 - run Unite_signals to unite all files''' #Done in server.py - use the  web site OR run unite_all after you finished the mapping on the server.py
    msgs = unite_signals('Erythrocyte')
    #unite_all_signal()
    #saveUnitsForAllSignals() #create signal_units.stats file with each united file and it's stats.
    
    '''Step 3 - check stats for united signal before fixing''' #Done in server.py - use server.py or run do_all_work for this and it will get all steps 3-6 automatically and when there is a problem it will write it down
    warningMsgs, unitStat = statsUnitedSig('Erythrocyte', '1001400138|Erythrocyte')
    
    '''Step 4 - edit instructions.txt, unitTranslator.txt and run fixSignal''' #Done in server.py - update signals with units problem, look @ do_all_work graphs and warnnings..
    #config_set_default('Erythrocyte', 'mm/h', '1', [], [], 1) #sigName, unitName, resulotion, ignore, factors, final_factor - take maccabi match or most common
    mostCommonUnit = unitStat[0][0]
    sigRes = getSignalUnitRes('Erythrocyte', mostCommonUnit)
    config_set_default('Erythrocyte', mostCommonUnit, sigRes, [], [], None) #set most common unit
    config_set_unit('Erythrocyte', 'mm/h', '1') #sigName, unitName, factorValue
    ignoreRareUnits('Erythrocyte', 200, None)
    unitStat2 = clearSupportUnits('Erythrocyte', unitStat)
    testList = unitStat2[0:4]
    testList.append(mostCommonUnit)
    unitWarn = compareUnitHist('Erythrocyte', testList, 0.0001) #smaller than 1 to 10000 remove
    if len(unitWarn) == 0:
        addAllWithFactor('Erythrocyte', testList[0:-1], '1')
    
    '''Step 5 - run fixSignal'''#Done in server.py or do_all_work
    fixSignal('Erythrocyte')
    
    '''Step 6 - check stats for fixed file''' #Done in server.py or do_all_work
    #TODO: look at stats files signalName__fix.list, signalName__fix.stats
    warningFixedMsgs = statsFixedSig('Erythrocyte')

    '''Step 7 - create statt for all special signals (categorial stuff)''' #done after analyzing stats with signal_parse_api.py - and analyzing ahdcode.final.stats file using analyzeStats.R
    #after that step I had created special_signals_config.txt file that has the special signals configuration for loading
    parseAllSignal()
    analyzeAllAhdCodes()
    addAhdCodeNames()
    #analyze stat with R - use analyzeStats.R

    '''Step 8 - load special signals '''
    loadAllSpecialSignals()
    print('cleaning not found keys...')
    cleanNotFoundKeys()
    print('sorting values in each file...')
    sortValues()
    
    '''Step 9 - run flow to create repository'''
    #use complete_signals.py (will complete missing signals in config file) and create_dictionary.py to create config files for the repository
    