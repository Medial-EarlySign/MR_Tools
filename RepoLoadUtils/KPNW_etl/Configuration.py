import os


class Configuration:
    def __init__(self):
        self.repo_folder = '/server/Work/CancerData/Repositories/KPNW/kpnw_nov20/'
        self.repo = os.path.join(self.repo_folder, 'kpnw.repository')
        
        if os.name =='nt':
            self.flow_app = r'\\nas1\UsersData\alon\MR\Tools\Flow\x64\Release\Flow.exe'
        else:
            self.flow_app = '/server/UsersData/alon/MR/Tools/Flow/Linux/Release/Flow'

        self.data_folder = 'T:\\NWP\\'
        self.delta_data_folder = 'T:\\NWP\\DeltaAPR20'
        self.delta_data_folder2 = 'T:\\NWP\\DeltaAUG20'
        self.delta_data_folder3 = 'T:\\NWP\\DeltaNOV20'
        self .data_folders = [self.data_folder, self.delta_data_folder,
                              self.delta_data_folder2, self.delta_data_folder3]
        #self.doc_source_path = self.data_folder + 'THINAncil1801\\text'
        #self.raw_source_path = self.data_folder + 'THINDB1801'
        #self.raw_source_path = 'D:\\THINDB1801'
        self.work_path = 'W:\\Users\\Tamar\\kpnw_load\\'
        self.code_folder = 'H:\\MR\\Tools\\RepoLoadUtils\\KPNW_etl'

        self.output_path = os.path.join(self.work_path, 'outputs') # path to output graphs and information abput signals. in linux it's mapped automaticaly "C:\\Users\\Alon" is replaced by "~\"
        self.ontology_folder = 'H:\\MR\\Tools\\DictUtils\\Ontologies'
