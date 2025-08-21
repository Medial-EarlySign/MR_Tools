import os
import getpass

class Configuration:
    def __init__(self):

        username = getpass.getuser()

        self.repo_folder = '/server/Work/CancerData/Repositories/TrinetX/LGI.all_encounters/'
        self.repo = os.path.join(self.repo_folder, 'trinetx.repository')

        self.flow_app = 'Flow'

        self.data_path = '/nas1/Work/TrinetX'
        self.work_path = '/nas1/Work/Users/yaron/TrinetX/LGI'
        self.tools_path = f'/nas1/UsersData/{username}/MR/Tools'
        self.code_path = os.path.join(self.tools_path,'RepoLoadUtils','trinetx_etl')
        self.onto_path = os.path.join(self.tools_path,'DictUtils','Ontologies')
        self.output_path = os.path.join(self.work_path,'outputs')
