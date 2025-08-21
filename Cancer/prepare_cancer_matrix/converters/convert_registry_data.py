import sys
import csv

def cancer_type3_from_icd10 (x):
	return {
		"C18":"Colon",
		"c18":"Colon",
		"C19":"Colon",
		"C20":"Rectum",
		"C97":"Colon" #TODO
		} [x]

header = ["NUMERATOR","YEAR","IN_SITU_CODE","STAGE_CD","STAGE_MECC","date","DIAGNOSIS_CODE","ICD9_CODE","MORPHCODE","GRUROT_CODE","LYMPH_NODES_CODE","cancer.code1","cancer.code2","cancer.code3","cancer.type1_first","cancer.type2_first","cancer.type3_first","maccabi.status.date","maccabi.status"]

output_file = open("chantu.registry.csv", 'wb')
writer = csv.writer( output_file, delimiter=',', quotechar='"')
writer.writerow(header)

with open('\\\\SERVER\\Temp\\summary_stats\\input\\chantu\\original\\version2\\cancer_data.csv', 'rt') as f:
	reader = csv.reader(f)
	next(reader, None) # skip headers
	for row in reader:
		
		# raw data
		patient_id = row[0]
		age = row[1]
		icd10 = row[2]
		cancer_date = row[5]
		
		# data manipulation
		if( patient_id[0] == 'A' ):
			new_patient_id = '1' + patient_id[1:]
		elif( patient_id[0] == 'B' ):
			new_patient_id = '2' + patient_id[1:]
		else:
			print( "Undefined patient id prefix %s. Aborts!" % patient_id )
			sys.exit()
		cancer_day_month_year = cancer_date.split("/")
		print cancer_day_month_year
		cancer_day = cancer_day_month_year[0]
		cancer_month = cancer_day_month_year[1]
		cancer_year = cancer_day_month_year[2]
		new_cancer_date = cancer_month + "/" + cancer_day + "/" + cancer_year
		tnm = row[4]
		comorbidity = row[5]
		type1 = "Digestive Organs"
		type2 = "Digestive Organs"
		type3 = cancer_type3_from_icd10(icd10[0:3])
		writer.writerow( [ new_patient_id, cancer_year,"","","",new_cancer_date,"",icd10[0:3],"","","","","","",type1,type2,type3,"","" ] )
		