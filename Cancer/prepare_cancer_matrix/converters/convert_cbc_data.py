import sys
import csv

colum_number_to_test_id = { 29:1, 33:2, 19:3, 8:4, 7:5, 16:6, 14:7, 15:8, 30:9, 28:10, 5:11, 23:12, 18:13, 6:14, 4:15, 22:16, 17:17, 3:18, 13:19, 12:20, 31:101, 32:102, 9:103, 10:104, 11:105, 20:106, 21:107, 24:108, 25:109, 26:110, 27:111 }

with open('\\\\SERVER\\Temp\\summary_stats\\input\\chantu\\original\\version2\\cbc_data.csv', 'rt') as f:
	reader = csv.reader(f)
	next(reader, None) # skip headers
	for row in reader:
		patient_id = row[0]
		date = row[1]
		test_id = row[3]
		
		if patient_id[0] == 'A':
			new_patient_id = '1' + patient_id[1:]
		elif patient_id[0] == 'B':
			new_patient_id = '2' + patient_id[1:]
		else:
			print( "Undefined patient id prefix %s. Aborts!" % patient_id )
			sys.exit()
		day_month_year = date.split("/")
		new_date = int(day_month_year[0]) + int(day_month_year[1]) * 100 + int(day_month_year[2]) * 10000
		for i in range(3,34):
			if( row[i] != "none" and row[i] != "" and row[i] != "MENT U"):
				value = float(row[i])
				# unit conversion
				if i == 7: # HCT - writtern as a fracture and not % 
					value = 100 * value
				if i == 8: # Hemoglobin: (g/L) -> (g/dl)
					value = 0.1 * value
				if i == 15: # MCHC_M: (g/L) -> (g/dl)
					value = 0.1 * value
				print new_patient_id, colum_number_to_test_id[i], new_date, value