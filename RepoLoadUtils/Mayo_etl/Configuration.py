import os


class Configuration:
    def __init__(self):
        self.repo_folder = '/server/Work/CancerData/Repositories/Mayo/Mayo_Aug19/'
        self.repo = os.path.join(self.repo_folder, 'mayo.repository')
        
        if os.name =='nt':
            self.flow_app = r'\\nas1\UsersData\alon\MR\Tools\Flow\x64\Release\Flow.exe'
        else:
            self.flow_app = '/server/UsersData/alon/MR/Tools/Flow/Linux/Release/Flow'

        self.data_folder = 'T:\\Mayo\\'
        self.work_path = 'W:\\Users\\Tamar\\mayo_load\\'
        self.code_folder = 'H:\\MR\\Tools\\RepoLoadUtils\\Mayo_etl'

        self.output_path = os.path.join(self.work_path, 'outputs') # path to output graphs and information abput signals. in linux it's mapped automaticaly "C:\\Users\\Alon" is replaced by "~\"
        self.ontology_folder = 'H:\\MR\\Tools\\DictUtils\\Ontologies'
