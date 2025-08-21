import os
import getpass

class Configuration:
    def __init__(self):

        username = getpass.getuser()

        self.repo_folder = '/server/Work/CancerData/Repositories/TrinetX22/Full/'
        #self.repo = os.path.join(self.repo_folder, 'trinetx.repository')

        self.flow_app = 'Flow'

        self.data_path = '/nas1/Work/TrinetX/Labs'
        self.work_path = '/nas1/Work/Users/coby/Trinetx/'
        self.work_dir = '/nas1/Work/Users/coby/Trinetx/'
        self.tools_path = f'/nas1/UsersData/{username}/MR/Tools'
        self.code_path = os.path.join(self.tools_path,'RepoLoadUtils','trinetx2022_etl')
        self.code_dir = os.path.join(self.tools_path,'RepoLoadUtils','trinetx2022_etl')
        self.onto_path = os.path.join(self.tools_path,'DictUtils','Ontologies')
        self.output_path = os.path.join(self.work_path,'outputs')
        self.dict_folder=os.path.join(self.code_dir, 'configs', 'dicts')