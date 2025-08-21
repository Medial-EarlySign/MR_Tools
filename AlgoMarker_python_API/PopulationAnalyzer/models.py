from typing import Dict, List, Callable, Optional
import pandas as pd
from pydantic import BaseModel


class CohortInfo(BaseModel):
    cohort_name: str
    bt_filter: Callable[[pd.DataFrame], pd.Series]


class ReferenceInfo(BaseModel):
    matrix_path: str
    control_weight: Optional[float] = None
    cohort_options: List[CohortInfo]
    default_cohort: Optional[str] = None
    repository_path: Optional[str] = None
    model_cv_path: Optional[str] = None
    model_cv_format: Optional[str] = None


class InputSignals(BaseModel):
    signal_name: str
    list_raw_signals: List[str]


class InputSignalsExistence(InputSignals):
    existence: bool = True
    tooltip_str: str | None = None


class InputSignalsTime(InputSignals):
    include_only_last: bool
    max_length_in_years: List[int]


class ModelInfo(BaseModel):
    model_name: str
    model_references: Dict[str, ReferenceInfo]
    sample_per_pid: int
    default_region: Optional[str] = None
    additional_info: Optional[str] = None
    signals_info: Optional[List[InputSignals]] = None
    model_path: Optional[str] = None
    orderinal: Optional[int] = None
    match_important_features: List[str] | None = None
