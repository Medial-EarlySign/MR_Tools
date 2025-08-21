import os


class Configuration:
    def __init__(self):
        self.repo_folder = '/opt/earlysign/Repositories/may22/'
        self.repo = os.path.join(self.repo_folder, 'geisinger.repository')
        self.demographic_prefix = 'demo_'
        self.data_folders=''
        
        self.work_path = '/opt/medial_sign/LOADING_PROCESS/geisinger_load_2022'
        self.code_folder = '/opt/earlysign/work/Alon/Flu/etl/configs'

        self.output_path = os.path.join(self.work_path, 'outputs') # path to output graphs and information abput signals. in linux it's mapped automaticaly "C:\\Users\\Alon" is replaced by "~\"
        self.ontology_folder = '/opt/medial_sign/med_scripts/ETL/DictUtils/Ontologies'
        self.work_dir=self.work_path
        self.dict_folder = os.path.join(self.code_folder, 'dicts')
