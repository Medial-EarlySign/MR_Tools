from Configuration import Configuration
import sys
sys.path.append('/opt/medial_sign/med_scripts/ETL/common')
from build_config_file import create_config_file, create_signal_file, create_additional_config_file

if __name__ == '__main__':
    cfg = Configuration()
    load_only_list=['TRAIN']    
    #create_config_file('geisinger',  cfg.work_dir, cfg.repo_folder, [])
    create_additional_config_file('geisinger', cfg.work_dir, cfg.repo_folder, load_only_list)
    #create_signal_file('ibm', cfg.work_dir, cfg.code_dir)


