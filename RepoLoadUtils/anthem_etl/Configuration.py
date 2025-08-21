import os


class Configuration:
    def __init__(self):
        self.repo_folder = '/home/LinuxDswUser/Repositories/may20_v1/'
        self.repo = os.path.join(self.repo_folder, 'anthem.repository')

        self.work_path = '/home/LinuxDswUser/work/anthem_load'
        self.code_folder = '/mnt/project/Tools/RepoLoadUtils/anthem_etl/'

        self.output_path = os.path.join(self.work_path, 'outputs') # path to output graphs and information abput signals. in linux it's mapped automaticaly "C:\\Users\\Alon" is replaced by "~\"
        self.ontology_folder = '/mnt/project/Tools/DictUtils/Ontologies'