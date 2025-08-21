#!/bin/python
import sys
import os
import subprocess
from Configuration import Configuration
from const_and_utils import fixOS


def run_command_file(cmd, out_p):
    print(cmd)
    #return
    if os.path.exists(out_p):
        os.remove(out_p)
    p = subprocess.call(cmd, shell=True)
    if (p != 0 or not(os.path.exists(out_p))):
        print('Error in running Command. CMD was:\n%s'%cmd)
        raise NameError('stop')


def load_hyper_reg():
    reg_creator_app = fixOS(os.path.join(os.environ['MR_ROOT'], 'Tools', 'Registries', 'CreateRegistries', 'Linux', 'Release', 'Hypertension'))
    cfg = Configuration()
    work_path =  fixOS(cfg.work_path)
    reg_path = os.path.join(work_path, 'registry')
    
    list_folder = os.path.join(os.environ['MR_ROOT'], 'Tools', 'Registries', 'Lists')
    
    readCodesFile = os.path.join(list_folder, 'hyper_tension.desc')
    CHF_ReadCodes = os.path.join(list_folder, 'heart_failure_events.desc')
    MI_ReadCodes = os.path.join(list_folder, 'mi.desc')
    AF_ReadCodes = os.path.join(list_folder, 'AtrialFibrilatioReadCodes.desc')

    rep_path = fixOS(cfg.repo)

    if not(os.path.exists(reg_path)):
        os.makedirs(reg_path)

    cmd = [reg_creator_app,  '--readCodesFile', readCodesFile,'--CHF_ReadCodes', CHF_ReadCodes,'--MI_ReadCodes',MI_ReadCodes ,'--AF_ReadCodes' , AF_ReadCodes, '--config', rep_path]
    full_cmd = ' '.join(cmd) + ' > %s 2> %s'%( os.path.join(reg_path, 'HT_Registry'), os.path.join(reg_path, 'hyperTenstionRegistry.stderr') )
    print (full_cmd)
    run_command_file(full_cmd, os.path.join(reg_path, 'HT_Registry'))
    

def load_cvd_reg(DiseaseReadCodesFileN,PastReadCodesFileN,Runtype,SignalName ):
    reg_creator_app = fixOS(os.path.join(os.environ['MR_ROOT'], 'Tools', 'Registries', 'CreateRegistries', 'Linux', 'Release', 'CVD'))
    cfg = Configuration()
    work_path = fixOS(cfg.work_path)
    reg_path = os.path.join(work_path, 'registry')
    rep_path = fixOS(cfg.repo)

    if not(os.path.exists(reg_path)):
        os.makedirs(reg_path)

    list_folder = os.path.join(os.environ['MR_ROOT'], 'Tools', 'Registries', 'Lists')
    DiseaseReadCodesFile = os.path.join(list_folder, DiseaseReadCodesFileN)
    PastReadCodesFile = os.path.join(list_folder, PastReadCodesFileN)
    AdmissionReadCodesFile = os.path.join(list_folder, 'readcode_admissions.txt')
    FileOut = os.path.join(reg_path, SignalName)

    cmd = [reg_creator_app,'--config', rep_path,   '--DiseaseReadCodesFile', DiseaseReadCodesFile,'--PastReadCodesFile', PastReadCodesFile,'--AdmissionReadCodesFile',AdmissionReadCodesFile ,'--Runtype' , Runtype , '--SignalName',SignalName , '--FileOut',FileOut  ]
    
    full_cmd = ' '.join(cmd)
    print(full_cmd)
    run_command_file(full_cmd, os.path.join(reg_path, SignalName))
   
        
def load_diabetes_reg():
    reg_creator_app = fixOS(os.path.join(os.environ['MR_ROOT'], 'Tools', 'Registries', 'createDiabetesRegistry', 'Linux', 'Release', 'Diabetes'))
    config_path = fixOS(os.path.join(os.environ['MR_ROOT'], 'Tools', 'Registries', 'Lists'))
    cfg = Configuration()

    work_path = fixOS(cfg.work_path)
    rep_path = fixOS(cfg.repo)
    
    reg_path = os.path.join(work_path, 'registry')
    if not(os.path.exists(reg_path)):
        os.makedirs(reg_path)
    
    cmd = [reg_creator_app,'--rep', rep_path, '--reg_type diabetes', '--reg_params "reg_mode=2"', '--create_registry', '--drugs',os.path.join(config_path, 'diabetes_drug_codes18.full') ,'--read_codes',  os.path.join(config_path, 'diabetes_read_codes_registry.full'), '--out_reg', os.path.join(work_path,'diabetes.reg')]
    
    full_cmd = ' '.join(cmd) + ' > %s '%( os.path.join(work_path, 'diabetes.log'))
    print(full_cmd)

    print('*****************************')
    print(work_path)
    run_command_file(full_cmd, os.path.join(work_path, 'diabetes.reg'))
    
    signal_name = 'DM_Registry'
    cmd = [reg_creator_app,	'--rep', rep_path,'--diabetes_reg', os.path.join(work_path,'diabetes.reg'), '--out_reg',os.path.join(reg_path,signal_name), '--create_registry', '--reg_type', signal_name]
    full_cmd = ' '.join(cmd) + ' > %s '%( os.path.join(work_path, 'diabetes2.log'))
    #print (full_cmd)
    run_command_file(full_cmd, os.path.join(reg_path, signal_name))
    


def load_ckd_reg():
    reg_creator_app = fixOS(os.path.join(os.environ['MR_ROOT'], 'Tools', 'Registries', 'createDiabetesRegistry', 'Linux', 'Release', 'Diabetes'))
    cfg = Configuration()
    
    work_path = fixOS(cfg.work_path)
    rep_path = fixOS(cfg.repo)
    
    reg_path = os.path.join(work_path, 'registry')
    if not os.path.exists(reg_path):
        os.makedirs(reg_path)
    
    signal_name = 'CKD_Registry'
    cmd = [reg_creator_app,	'--rep', rep_path,'--proteinuria', '--out_reg', os.path.join(reg_path,'CKD_Registry')]
    full_cmd = ' '.join(cmd) + ' > %s '%( os.path.join(reg_path, 'proteinuria.log'))
    print(full_cmd)
    run_command_file(full_cmd, os.path.join(reg_path, 'CKD_Registry'))


if __name__ == "__main__":
    print('starting')
    
    load_diabetes_reg()
    load_ckd_reg()
    load_hyper_reg()
    load_cvd_reg('MI_present.txt','MI_past.txt','event','CVD_MI' )
    load_cvd_reg('ischemicStroke_present.txt','ischemicStroke_past.txt','event','CVD_IschemicStroke' )
    load_cvd_reg('hemorhagic_present.txt','hemorhagic_past.txt','event','CVD_HemorhagicStroke' )
    load_cvd_reg('heartFailure.txt','','notevent','CVD_HeartFailure' )



