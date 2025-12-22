import numpy as np
import med
import os
import xgboost as xgb
import json
import re
from io import StringIO
import pandas as pd


MDL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "AlgoMarkers",
    "AM_LGI",
    "AlgoMarker",
    "LGI-Flag-ButWhy-3.1.2-Scorer",
    "resources",
    "LGI-ColonFlag-3.1.model",
)
MDL_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "AlgoMarkers",
    "AM_LGI",
    "MHS",
    "configs",
    "crc_baseline.json",
)

SAMPLES = "/tmp/NHANES/outputs/Samples.crc/relabeled.samples"
REP = "/tmp/repository/NHANES/nhanes.repository"


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
    rep.read_all(REP, ids, signalNamesSet)  # read needed repository data

    m.apply(rep, s, 0, 4)

    shap_results = med.Features()
    predictor.calc_feature_contribs(m.features, shap_results)
    return shap_results


def add_rep_processor():
    m = med.Model()
    m.read_from_file(MDL_PATH)
    m.add_pre_processors_json_string_to_model(
        json.dumps(
            {
                "pre_processors": [
                    {
                        "action_type": "rp_set",
                        "members": [
                            {
                                "rp_type": "history_limit",
                                "signal": "ref:signals",
                                "delete_sig": "1",
                            }
                        ],
                    }
                ],
                "signals": ["Hemoglobin", "MCV", "MCH", "RBC", "Hematocrit"],
            }
        ),
        ".",
        True,
    )

    s = med.Samples()
    s.read_from_file(SAMPLES)
    ids = s.get_ids()

    rep = med.PidRepository()
    rep.init(REP)

    m.fit_for_repository(rep)
    signalNamesSet = m.get_required_signal_names()
    rep.read_all(REP, ids, signalNamesSet)

    m.apply(rep, s, 0, 2)
    return m.features.to_df()


def read_signals_after_rep_processor():
    m = med.Model()
    m.read_from_file(MDL_PATH)
    m.add_pre_processors_json_string_to_model(
        json.dumps(
            {
                "pre_processors": [
                    {
                        "action_type": "rp_set",
                        "members": [
                            {
                                "rp_type": "history_limit",
                                "signal": "ref:signals",
                                "delete_sig": "1",
                            }
                        ],
                    }
                ],
                "signals": ["Hemoglobin", "MCV", "MCH", "RBC", "Hematocrit"],
            }
        ),
        ".",
        True,
    )

    rep = med.PidRepository()
    rep.init(REP)

    m.fit_for_repository(rep)
    signalNamesSet = m.get_required_signal_names()
    rep.read_all(REP, [], signalNamesSet)

    signal_hem = m.debug_rep_processor_signal(rep, "Hemoglobin", 93705, 20250101)
    signal_wbc = m.debug_rep_processor_signal(rep, "WBC", 93705, 20250101)

    # signal_hem = rep.uget(93705, rep.sig_id("Hemoglobin"))
    print("signal hemoglobin has", len(signal_hem))
    for rec in signal_hem:
        print(rec.time(), rec.val())
    print("signal WBC has", len(signal_wbc))
    for rec in signal_wbc:
        print(rec.time(), rec.val())


def test_rep_processors():
    m = med.Model()
    with open("/tmp/1.json", "w") as fw:
        fw.write(
            json.dumps(
                {
                    "model_json_version": "2",
                    "$schema": "https://raw.githubusercontent.com/Medial-EarlySign/MR_Tools/refs/heads/main/medmodel_schema.json",
                    "serialize_learning_set": "0",
                    "model_actions": [
                        {
                            "action_type": "rp_set",
                            "members": [
                                {
                                    "rp_type": "basic_cln",
                                    "type": "iterative",
                                    "doRemove": "1",
                                    "range_min": "0",
                                    "trim_range_min":"0",
                                    "trim_range_max":"10",
                                    "range_max": "25",
                                    "print_summary": "0",
                                    "signal": ["Hemoglobin"],
                                    "unconditional":"1"
                                },
                                {
                                    "rp_type": "calculator",
                                    "calculator": "calc_log",
                                    "names": "Hemoglobin_log",
                                    "signals": "Hemoglobin",
                                    "signals_time_unit": "Days",
                                    "unconditional":"1"
                                },
                            ],
                        }
                    ],
                }
            )
        )
    m.init_from_json_file("/tmp/1.json")

    rep = med.PidRepository()
    rep.init(REP)

    m.fit_for_repository(rep)
    # learn rep processors - this model is from json and not prepared to inference yet:
    samples = med.Samples()
    s = med.Sample()
    s.id = 93705
    s.time = 20250101
    s.outcome =0 
    s.outcomeTime = s.time
    s.split = -1
    v=med.SampleVectorAdaptor()
    v.append(s)
    samples.import_from_sample_vec(v)
    signalNamesSet = m.get_required_signal_names()
    print(signalNamesSet)
    rep.read_all(REP, [s.id], signalNamesSet)

    
    m.quick_learn_rep_processors(rep, samples)

    signal_hem = m.debug_rep_processor_signal(rep, "Hemoglobin", s.id, s.time)
    print("signal hemoglobin has", len(signal_hem))
    for rec in signal_hem:
        print(rec.time(), rec.val())

    signal_hem_log = m.debug_rep_processor_signal(rep, "Hemoglobin_log", s.id, s.time)
    print("signal hemoglobin_log has", len(signal_hem_log))
    for rec in signal_hem_log:
        print(rec.time(), rec.val())

def test_train_model():
    m = med.Model()
    m.init_from_json_file(MDL_JSON)
    samples = med.Samples()
    samples.read_from_file(SAMPLES)
    df=samples.to_df()
    df["outcome"] = np.random.randint(0,2, len(df))
    samples.from_df(df)
    ids = samples.get_ids()

    rep = med.PidRepository()
    rep.init(REP)

    m.fit_for_repository(rep)
    signalNamesSet = m.get_required_signal_names()
    rep.read_all(REP, ids, signalNamesSet)

    m.learn(rep, samples)
    m.write_to_file("/tmp/baseline.model")

    samples = med.Samples()
    samples.read_from_file(SAMPLES)
    m.apply(rep, samples)

    df1 = samples.to_df()
    m2 = med.Model()
    m2.read_from_file("/tmp/baseline.model")
    m2.apply(rep, samples)
    df2 = samples.to_df()
    
    pd.testing.assert_frame_equal(
        df1,
        df2,
        atol=1e-4,
    )

    return df1, df2

def test_apply_model():
    m = med.Model()
    m.read_from_file(MDL_PATH)

    m.apply_model_change(json.dumps({
                "changes": [
                    {
                        "change_name": "delete explainer",
                        "object_type_name": "TreeExplainer",
                        "change_command": "DELETE",
                        "verbose_level": 2,
                    }
                ]
            }))

    samples = med.Samples()
    samples.read_from_file(SAMPLES)
    ids = samples.get_ids()

    rep = med.PidRepository()
    rep.init(REP)

    m.fit_for_repository(rep)
    signalNamesSet = m.get_required_signal_names()
    rep.read_all(REP, ids, signalNamesSet)

    m.apply(rep, samples)
    return samples.to_df()