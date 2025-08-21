from Configuration import Configuration
import sys
sys.path.insert(0, '/mnt/work/Infra/tools/common')
from build_config_file import create_config_file, create_signal_file, create_additional_config_file


if __name__ == '__main__':
    cfg = Configuration()
    load_only_list=['Helicobacter.Categorical','Urine_Glucose.Categorical','Urine_Bacteria.Categorical','Urine_Bilirubin.Categorical','Urine_dipstick_for_glucose.Categorical','Urine_dipstick_for_ketones.Categorical','Urine_Dipstick_for_Nitrites.Categorical','Urine_Ketone.Categorical','Urine_Leucocytes.Categorical','Urine_RBC.Categorical','Urine_Total_Protein.Categorical','UrineTotalProtein.Categorical','Heart_Rate','BP','Resp_Rate','Temperature','BMI','Weight','SaO2','Height','K+','Creatinine','Glucose','Arterial_BP_Mean','Cl','Na','Ca','CO2','Albumin','eGFR','BUN','Protein_Total','ALT','PlasmaAnionGap','AST','Bilirubin','ALKP','PO2','VAS','INR','Urea_nitrogen_Over_Creatinine','Cholesterol','Urine_Spec_Gravity','Urine_RBC','HDL','Triglycerides','Mg','Urine_PH','Urine_Bilirubin','HbA1C','Globulin','PT','Urine_Bacteria','PCO2','Art_PaO','TroponinI','UrineTotalProtein','LDL','NRBC%','Phosphate','TSH','Granulocytes','Neutrophils_Segmented%','aPTT','Urine_Total_Protein','Urine_Urobilinogen','Immature_Granulocytes#','Bicarbonate','Osmolality','NonHDLCholesterol','Myelocytes%','Metamyelocytes%','Creatinine_Kinase','Polychromasia','Bands%','Lactate','Atypical_Lymphocytes%','FreeT4','NRBC','BurrCells','Dacrocytes','Base_Excess','Target_Cells','Schistocytes','Helicobacter','Drug']
    #create_config_file('ibm',  cfg.work_dir, cfg.repo_folder, ['SMOKING_STATUS', 'ALCOHOL_STATUS'])
    create_additional_config_file('ibm', cfg.work_dir, cfg.repo_folder, load_only_list)
    #create_signal_file('ibm', cfg.work_dir, cfg.code_dir)
