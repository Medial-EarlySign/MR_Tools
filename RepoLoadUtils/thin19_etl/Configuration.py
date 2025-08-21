import os


class Configuration:
    def __init__(self):
        self.repo = '/server/Work/CancerData/Repositories/THIN/thin_2019/thin.repository'
        
        if os.name =='nt':
            self.flow_app = r'\\nas1\UsersData\alon\MR\Tools\Flow\x64\Release\Flow.exe'
        else:
            self.flow_app = '/server/UsersData/alon/MR/Tools/Flow/Linux/Release/Flow'

        self.data_folder = 'T:\\THIN1901\\'
        self.doc_source_path = self.data_folder + 'THINAncil1901\\text'
        self.patient_source_path = self.data_folder + 'THINAncil1901\\Patient_Demography1901'
        self.raw_source_path = self.data_folder + 'THINDB1901'
        #self.raw_source_path = 'D:\\THINDB1801'
        self.patient_demo = self.data_folder + 'THINAncil1901\\Patient_Demography1901\\patient_demography.csv'
        self.work_path = 'W:\\Users\\Tamar\\thin19_load\\'
        self.code_folder = 'H:\\MR\\Tools\\RepoLoadUtils\\thin19_etl'

        self.output_path = os.path.join(self.work_path, 'outputs') # path to output graphs and information abput signals. in linux it's mapped automaticaly "C:\\Users\\Alon" is replaced by "~\"
        self.curr_repo = 'W:\\CancerData\\Repositories\THIN\\thin_2019\\'
        self.prev_repo = 'W:\\CancerData\\Repositories\THIN\\thin_2018_2\\'
        self.prev_id2ind = self.prev_repo + 'ID2NR'
