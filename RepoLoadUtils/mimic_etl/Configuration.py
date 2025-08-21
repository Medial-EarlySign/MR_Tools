import os


class Configuration:
    def __init__(self):
        self.repo_folder = '/nas1/Work/CancerData/Repositories/MIMIC/mimic_314/'
        self.repo = os.path.join(self.repo_folder, 'mimic.repository')
        self.prev_repo = '/server/Work/CancerData/Repositories/MIMIC/Mimic3/mimic.repository'
        self.fix_mean_threshold = 0.1
        
        if os.name =='nt':
            self.flow_app = r'\\nas1\UsersData\alon\MR\Tools\Flow\x64\Release\Flow.exe'
        else:
            self.flow_app = '/server/UsersData/alon/MR/Tools/Flow/Linux/Release/Flow'

        self.data_folder = 'T:\\ICU\\\Mimic-3-1.4\\'
        self.work_path = 'W:\\Users\\Tamar\\mimic_load\\'
        self.code_folder = 'H:\\MR\\Tools\\RepoLoadUtils\\mimic_etl'

        self.output_path = self.work_path + 'outputs' # path to output graphs and information abput signals. in linux it's mapped automaticaly "C:\\Users\\Alon" is replaced by "~\"
        self.prev_id2ind = self.prev_repo + 'ID2NR'
        self.ontology_folder = 'H:\\MR\\Tools\\DictUtils\\Ontologies'
