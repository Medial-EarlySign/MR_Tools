"""
Should create:
    am_regions
    sample_per_pid
    default_region - optional
    additional_info - optional
    optional_signals - optional
    model_path - optional
    repository_path - optional
    orderdinal - optional order
"""

from models import *

lung_cohorts = []
lung_cohorts.append(CohortInfo(cohort_name='Ever Smokers Age 50-80', bt_filter=lambda df: (df['age']>=50) & (df['age']<=80) ))
lung_cohorts.append(CohortInfo(cohort_name='Ever Smokers Age 45-80', bt_filter=lambda df: (df['age']>=45) & (df['age']<=80) ))
lung_cohorts.append(CohortInfo(cohort_name='Ever Smokers Age 40-90', bt_filter=lambda df: (df['age']>=40) & (df['age']<=90) ))

lung_cohorts.append(CohortInfo(cohort_name='Ever Smokers Age 55-74', bt_filter=lambda df: (df['age']>=55) & (df['age']<=74) ))
#Add USPSTF to us
us_lung_cohorts = []
us_lung_cohorts.append(CohortInfo(cohort_name='Ever Smokers Age 50-80', bt_filter=lambda df: (df['age']>=50) & (df['age']<=80) ))
us_lung_cohorts.append(CohortInfo(cohort_name='Ever Smokers Age 55-74', bt_filter=lambda df: (df['age']>=55) & (df['age']<=74) ))
us_lung_cohorts.append(CohortInfo(cohort_name='Ever Smokers Age 45-90', bt_filter=lambda df: (df['age']>=45) & (df['age']<=90) ))

us_lung_cohorts.append(CohortInfo(cohort_name='USPSTF Age 50-80 (20 pack years, less then 15 years quit)', bt_filter=lambda df: (df['age']>=50) & (df['age']<=80) &
                                   (df['smoking.smok_pack_years']>=20) & (df['smoking.smok_days_since_quitting']<=15*365) ))

am_regions = dict()

am_regions['US-KP'] = ReferenceInfo(matrix_path='/nas1/Work/Users/eitan/Lung/outputs/models2023/EX3/model_63/reference_matrices/reference_features_kp.final.matrix', control_weight=20, cohort_options=us_lung_cohorts, default_cohort='USPSTF Age 50-80 (20 pack years, less then 15 years quit)', repository_path='/nas1/Work/CancerData/Repositories/KP/kp.repository', model_cv_path='/nas1/Work/Users/eitan/Lung/outputs/models2023/EX3/model_63/results', model_cv_format='CV_MODEL_%d.medmdl')
am_regions['UK-THIN'] = ReferenceInfo(matrix_path='/nas1/Work/Users/eitan/Lung/outputs/models2023/EX3/model_63/reference_matrices/reference_features_thin.final.matrix', cohort_options=lung_cohorts, default_cohort='Ever Smokers Age 55-74', repository_path='/nas1/Work/CancerData/Repositories/THIN/thin_2021.lung/thin.repository')

sample_per_pid = 0
default_region = 'UK-THIN'
additional_info = 'Time Window 90-365'
optional_signals = []
optional_signals.append(InputSignalsExistence(signal_name='Smoking', list_raw_signals=['Smoking_Duration', 'Smoking_Intensity',
                                                                                        'Pack_Years', 'Smoking_Quit_Date'], tooltip_str='If true will include Smoking_Duration, Smoking_Intensity, Pack_Years, Smoking_Quit_Date  in the inputs and not only status'))
optional_signals.append(InputSignalsExistence(signal_name='Labs', list_raw_signals=["Albumin","ALKP","ALT","Cholesterol",
                                                                                                    "Triglycerides","LDL","HDL","Creatinine",
                                                                                                    "Glucose","Urea","Eosinophils%","Hematocrit",
                                                                                                    "Hemoglobin","MCHC-M","MCH","Neutrophils#",
                                                                                                    "Neutrophils%","Platelets","RBC","WBC", "RDW",
                                                                                                    "Protein_Total", "Lymphocytes%", "Basophils%",
                                                                                                    "Monocytes%", "Lymphocytes#", "Basophils#",
                                                                                                    "Monocytes#","Eosinophils#","MCV"]))
optional_signals.append(InputSignalsExistence(signal_name='BMI', list_raw_signals=['BMI', 'Weight', 'Height']))
optional_signals.append(InputSignalsExistence(signal_name='Spirometry', list_raw_signals=['Fev1']))
model_path = '/earlysign/AlgoMarkers/LungFlag/lungflag.model'
orderdinal = 1