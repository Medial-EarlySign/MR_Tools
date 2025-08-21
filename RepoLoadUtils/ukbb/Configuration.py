import os


class Configuration:
    def __init__(self):
        self.repo_folder = '/server/Work/ukbb/Repositories/'
        self.repo = os.path.join(self.repo_folder, 'ukbb.repository')

        if os.name == 'nt':
            self.flow_app = r'\\nas1\UsersData\coby-internal\MR\Tools\Flow\x64\Release\Flow.exe'
        else:
            self.flow_app = '/server/UsersData/coby-internal/MR/Tools/Flow/Linux/Release/Flow'

        self.data_folder = 'T:\\UKBB'
        self.doc_source_path = self.data_folder + '\\UKBB Ancil TEXT\\text'
        self.patient_source_path = self.data_folder + '\\UKBB Ancil TEXT\\Patient_Demography'
        self.raw_source_path = self.data_folder + '\\UKBB'
        self.patient_demo = self.data_folder + '\\UKBB Ancil TEXT\\Patient_Demography\\patient_demography.csv'
        self.work_path = 'W:\\Users\\Coby\\UKBB_load\\'
        self.code_folder = '/nas1/UsersData/coby-internal/MR/Tools/RepoLoadUtils/ukbb'
        self.output_path = os.path.join(self.work_path,
                                        'outputs')  # path to output graphs and information abput signals. in linux it's mapped automaticaly "C:\\Users\\Alon" is replaced by "~\"
        self.curr_repo = 'W:\\ukbb\\Repositories\\'
        self.prev_repo = 'W:\\ukbb\\Repositories\\'
        self.prev_id2ind = self.prev_repo + 'ID2NR'
