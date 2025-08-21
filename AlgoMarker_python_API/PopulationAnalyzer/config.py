from models import *
import os


def fix_name(cfg_name: str) -> str:
    return cfg_name.replace("_SLASH_", "/")

def unfix_name(cfg_name: str) -> str:
    return cfg_name.replace("/", "_SLASH_")

def retrieve_config() -> Dict[str, ModelInfo]:
    """
    Will load dynamically al configs from relative algomarkers directory
    """
    base_path = os.path.dirname(__file__)
    algomarkers = os.path.join(base_path, "algomarkers")
    model_to_info = {}
    for ii, config_name in enumerate(sorted(os.listdir(algomarkers))):
        full_config = os.path.join(algomarkers, config_name)
        env_vars = {}
        with open(full_config, "r") as fr:
            full_code = fr.read()
            exec(full_code, globals(), env_vars)
            default_reg = None
            additional_inf = None
            _optional_signals = []
            _model_path = None
            _ordinal = ii
            _match_important_features = None
            if "sample_per_pid" not in env_vars:
                raise Exception(
                    f'Error in config {full_config} - please define "sample_per_pid"'
                )
            if "am_regions" not in env_vars:
                raise Exception(
                    f'Error in config {full_config} - please define "am_regions"'
                )
            if "default_region" in env_vars:
                default_reg = env_vars["default_region"]
            if "additional_info" in env_vars:
                additional_inf = env_vars["additional_info"]
            if "optional_signals" in env_vars:
                _optional_signals = env_vars["optional_signals"]
            if "model_path" in env_vars:
                _model_path = env_vars["model_path"]
            if "orderdinal" in env_vars:
                _ordinal = env_vars["orderdinal"]
            if "match_important_features" in env_vars:
                _match_important_features = env_vars["match_important_features"]

            am_name = ".".join(fix_name(config_name).split(".")[:-1])
            model_to_info[am_name] = ModelInfo(
                model_references=env_vars["am_regions"],
                sample_per_pid=env_vars["sample_per_pid"],
                default_region=default_reg,
                additional_info=additional_inf,
                signals_info=_optional_signals,
                model_path=_model_path,
                orderinal=_ordinal,
                model_name=am_name,
                match_important_features=_match_important_features,
            )
            print(f"Loaded {am_name} configuration")
    return model_to_info
