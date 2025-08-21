from Configuration import Configuration
from build_config_file import create_config_file
from utils import fixOS, unix_path


if __name__ == '__main__':
    cfg = Configuration()
    to_remove = ['APTT', 'CA153', 'CA199', 'Fructosamine', 'GtanNum', 'PTT', 'PlasmaVolume', 'T3', 'UrineUrate', 'VLDL', 'VitaminD2', 'Zinc']
    create_config_file('thin18',  fixOS(cfg.work_path), fixOS(cfg.repo_folder), to_remove)
