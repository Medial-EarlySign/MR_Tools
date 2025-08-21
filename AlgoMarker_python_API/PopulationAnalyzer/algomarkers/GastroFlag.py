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
    match_important_features - optional list
"""


from models import *


lgi_cohorts = []
lgi_cohorts.append(CohortInfo(cohort_name='Age Range: 40-90, Time-window: 365', bt_filter=lambda df: (df['age']>=40) & (df['age']<=90) ))
lgi_cohorts.append(CohortInfo(cohort_name='Age Range: 45-75, Time-window: 365', bt_filter= lambda df: (df['age']>=45) & (df['age']<=75) ))
lgi_cohorts.append(CohortInfo(cohort_name='Age Range: 50-75, Time-window: 365', bt_filter=lambda df: (df['age']>=50) & (df['age']<=75) ))
lgi_cohorts.append(CohortInfo(cohort_name='Age Range: 40-90, Time-window: 180', bt_filter=lambda df: (df['age']>=40) & (df['age']<=90) & (df['Time-Window']<=180) ))
lgi_cohorts.append(CohortInfo(cohort_name='Age Range: 45-75, Time-window: 180', bt_filter= lambda df: (df['age']>=45) & (df['age']<=75) & (df['Time-Window']<=180) ))
lgi_cohorts.append(CohortInfo(cohort_name='Age Range: 50-75, Time-window: 180', bt_filter=lambda df: (df['age']>=50) & (df['age']<=75) & (df['Time-Window']<=180) ))


    
am_regions = dict()
am_regions['UK-THIN'] = ReferenceInfo(matrix_path='/nas1/Work/Users/Alon/LGI/outputs.MHS/models/optimized_for_gastric.2025_01_09/reference_matrix/features.for_simulator.csv', cohort_options=lgi_cohorts, 
                                     default_cohort='Age Range: 40-90, Time-window: 365', repository_path='/nas1/Work/CancerData/Repositories/THIN/thin_jun2017/thin.repository')

sample_per_pid = 1
default_region = 'UK-THIN'
additional_info = 'Time Window 0-365'
optional_signals = []
optional_signals.append(InputSignalsTime(signal_name='CBC', list_raw_signals=['Hemoglobin', 'Hematocrit', 'RBC', 'WBC', 'RDW', 'Platelets',
                                                                              'MCH', 'MCHC-M', 'MCV', 'MPV', 'Eosinophils#', 'Eosinophils%',
                                                                              'Monocytes#', 'Monocytes%', 'Basophils#', 'Basophils%', 
                                                                              'Lymphocytes#', 'Lymphocytes%', 'Neutrophils#', 'Neutrophils%'], 
                                         include_only_last=True, max_length_in_years=[3]))
optional_signals.append(InputSignalsExistence(signal_name='BMP(Glucose,Creatinine,K+,Na,Urea)', list_raw_signals=['Creatinine','Glucose','K+','Na','Urea'],
                                              tooltip_str='Includes: Creatinine, Glucose, K+, Na, Urea'))
optional_signals.append(InputSignalsExistence(signal_name='CMP(Albumin,ALKP,ALT,AST,Bilirubin,Protein)', list_raw_signals=['Albumin','ALKP','ALT','AST','Bilirubin','Protein_Total'], tooltip_str='Includes: Albumin, ALKP, AST, Bilirubin, Protein_Total'))
optional_signals.append(InputSignalsExistence(signal_name='Iron_Ferritin', list_raw_signals=['Ferritin', 'Iron_Fe'], tooltip_str='Includes: Ferritin, Iron'))
model_path = '/server/Work/Users/Alon/LGI/outputs.MHS/models/optimized_for_gastric.2025_01_09/config_params/exported_full_model.with_explainabiliy.final.medmdl'

orderdinal = 3
match_important_features = ["Age", "Gender", "MCH.min.win_0_180", "Hemoglobin.min.win_0_180"]
