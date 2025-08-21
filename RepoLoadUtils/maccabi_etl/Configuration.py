import os


class Configuration:
    def __init__(self):
        self.repo_folder = '/data/Repositories/aug20'
        self.repo = os.path.join(self.repo_folder, 'maccabi.repository')

        self.data_folder = '/medialshare'
        self.codes_folder = os.path.join(self.data_folder,'codes')
        self.work_path = '/data/maccabi_load'
        self.code_folder = '/opt/medial/tools/bin/RepoLoadUtils/maccabi_etl'
  
