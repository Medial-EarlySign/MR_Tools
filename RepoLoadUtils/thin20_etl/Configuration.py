import os


class Configuration:
    def __init__(self):
        self.repo_folder = '/server/Work/CancerData/Repositories/THIN/thin_2020/'
        self.repo = os.path.join(self.repo_folder, 'thin.repository')

        if os.name == 'nt':
            self.flow_app = r'\\nas1\UsersData\tamard\MR\Tools\Flow\x64\Release\Flow.exe'
        else:
            self.flow_app = '/server/UsersData/tamard/MR/Tools/Flow/Linux/Release/Flow'

        self.data_folder = 'T:\\THIN2005\\'
        self.doc_source_path = self.data_folder + 'THINAncil2005\\text'
        self.patient_source_path = self.data_folder + 'THINAncil2005\\Patient_Demography2005'
        self.raw_source_path = self.data_folder + 'THINDB2005'
        # self.raw_source_path = 'D:\\THINDB1801'
        self.patient_demo = self.data_folder + 'THINAncil2005\\Patient_Demography2005\\patient_demography.csv'
        self.work_path = 'W:\\Users\\Tamar\\thin20_load\\'
        #self.code_folder = 'H:\\MR\\Tools\\RepoLoadUtils\\thin20_etl'
        self.code_folder = '/nas1/UsersData/tamard/MR/Tools/RepoLoadUtils/thin20_etl'
        self.output_path = os.path.join(self.work_path,
                                        'outputs')  # path to output graphs and information abput signals. in linux it's mapped automaticaly "C:\\Users\\Alon" is replaced by "~\"
        self.curr_repo = 'W:\\CancerData\\Repositories\THIN\\thin_2020\\'
        self.prev_repo = 'W:\\CancerData\\Repositories\THIN\\thin_2018_2\\'
        self.prev_id2ind = self.prev_repo + 'ID2NR'
