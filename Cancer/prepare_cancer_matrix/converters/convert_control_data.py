import sys
import csv

demfile = open("chantu.demographics.control.txt", 'w')
cbcfile = open("chantu.cbc.control.txt", 'w')

colum_number_to_test_id     = { 5:2, 6:13, 7:17, 8:1, 9:9, 10:6, 11:5, 12:19, 13:20, 14:7, 15:8, 16:3, 17:15, 18:18, 19:14, 20:11, 21:12, 22:16, 23:4, 24:10, 25:111, 26:110 }

with open('\\\\SERVER\\Temp\\summary_stats\\input\\chantu\\original\\version2\\control_data.csv', 'rt') as f:
	reader = csv.reader(f)
	next(reader, None) # skip headers
	for row in reader:
		id = row[0]
		gender = row[1]
		age = row[2]
		
		
		# demogrpahics information 
		new_id = '3' + id
		birth_year = 2013 - int(age)
		if gender == '1':
			new_gender = 'M'
		elif gender == '2':
			new_gender = 'F'
		else:
			new_gender = 'X'
			print "Unknown gender ", gender, ".Aborts"
			sys.exit(0)
		
		demfile.write( "%d %d %s\n" % ( int(new_id), birth_year, new_gender ) )
		
		#cbc information 
		for i in range(5,27):
			
			try:
				value = float(row[i])
				# unit conversion
				if i == 11: # HCT - writtern as a fracture and not % 
					value = 100 * value
				if i == 15: # MCHC_M: (g/L) -> (g/dl)
					value = 0.1 * value
				if i == 23: # Hemoglobin: (g/L) -> (g/dl)
					value = 0.1 * value
				cbcfile.write( "%s %d %s %f\n" % ( new_id, colum_number_to_test_id[i], "20120202", value ) )
			
			except:
				pass
demfile.close()
cbcfile.close()
