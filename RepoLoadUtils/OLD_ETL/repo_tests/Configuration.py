import os
from utils import fixOS

class Configuration:
    def __init__(self):
        self.repo_short = 'thin'
        self.repo = fixOS('/nas1/Work/CancerData/Repositories/MIMIC/mimic_314/')
        self.repo_file = os.path.join(self.repo, self.repo_short+'.repository')
        self.sigs_file = os.path.join(self.repo, self.repo_short + '.signals')

        self.out_dir = '/server/Work/Users/Tamar/thin_load/output'
        #self.out_dir = '/nas1/Temp/Thin_2018_Loading/outputs'
