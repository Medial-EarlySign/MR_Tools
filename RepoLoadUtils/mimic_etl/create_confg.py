from Configuration import Configuration
from build_config_file import create_config_file
from utils import fixOS, unix_path


if __name__ == '__main__':
    cfg = Configuration()
    create_config_file('mimic',  fixOS(cfg.work_path), fixOS(cfg.repo_folder), [])
