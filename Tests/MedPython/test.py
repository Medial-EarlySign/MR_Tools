import med
import os
import xgboost as xgb
import json
import re
from io import StringIO


MDL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "AlgoMarkers",
    "AM_LGI",
    "AlgoMarker",
    "LGI-Flag-ButWhy-3.1.2-Scorer",
    "resources",
    "LGI-ColonFlag-3.1.model",
)

SAMPLES = "/tmp/NHANES/outputs/Samples.crc/relabeled.samples"
REP = '/tmp/repository/NHANES/nhanes.repository'

def test_export_model():
    m = med.Model()
    m.read_from_file(MDL_PATH)
    predictor: med.Predictor = m.predictor
    predictor.export_predictor("/tmp/test")

    xgb_model = xgb.Booster()
    xgb_model.load_model("/tmp/test")
    return xgb_model


def test_print_model() -> str:
    m = med.Model()
    m.read_from_file(MDL_PATH)
    obj_data = m.get_model_weights_json()
    # Fix to json:
    find_enums = re.compile(r'(:) *([A-Za-z][^,"}]+)')
    obj_data = find_enums.sub(rf': "\2"', obj_data)
    # json.loads(obj_data)
    return obj_data


def change_model():
    m = med.Model()
    m.read_from_file(MDL_PATH)
    m.apply_model_change(
        json.dumps(
            {
                "changes": [
                    {
                        "change_name": "just_print",
                        "object_type_name": "RepCheckReq",
                        "change_command": "PRINT",
                        "verbose_level": 2,
                    }
                ]
            }
        )
    )

def get_processors_info():
    m = med.Model()
    m.read_from_file(MDL_PATH)
    return m.get_model_processors_info()

def print_info():
    m = med.Model()
    m.read_from_file(MDL_PATH)
    print(m.print_rep_processor_by_index(1))

    print(m.print_feature_generator_by_index(1))

    print(m.print_feature_processor_by_index(1))

def feature_contrib():
    m = med.Model()
    m.read_from_file(MDL_PATH)
    predictor: med.Predictor = m.predictor

    s = med.Samples()
    s.read_from_file(SAMPLES)
    ids = s.get_ids()

    rep = med.PidRepository()
    rep.init(REP)

    m.fit_for_repository(rep)
    signalNamesSet = m.get_required_signal_names()
    rep.read_all(REP, ids, signalNamesSet) #read needed repository data

    m.apply(rep, s, 0, 4)

    shap_results = med.Features()
    predictor.calc_feature_contribs(m.features, shap_results)
    return shap_results


