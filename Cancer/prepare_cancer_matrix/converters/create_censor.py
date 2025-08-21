# creates the censor file from the demographics file
# input: demographics file
# ouput: censor with every person in censor

import sys
import csv
with open('\\\\SERVER\\Temp\\summary_stats\\input\\chantu\\original\\version2\\basic_data.csv', 'rt') as f:
	reader = csv.reader(f)
	next(reader, None) # skip headers
	for row in reader:
		id = row[0]
		date = row[1]
		day_month_year = date.split("/")
		gender = row[4]
		
		if id[0] == 'A':
			new_id = '1' + id[1:]
		elif id[0] == 'B':
			new_id = '2' + id[1:]
		else:
			print( "Undefined patient id prefix %s. Aborts!" % id )
			sys.exit()
		
		if gender == '1':
			new_gender = 'M'
		elif gender == '2':
			new_gender = 'F'
		else:
			new_gender = 'X'
			print "Unknown gender ", gender, ".Aborts"
			sys.exit(0)
		print new_id, 1, 1, 19500101
with open('\\\\SERVER\\Temp\\summary_stats\\input\\chantu\\original\\version2\\control_data.csv', 'rt') as f:
	reader = csv.reader(f)
	next(reader, None) # skip headers
	for row in reader:
		id = row[0]
		new_id = '3' + id
		print new_id, 1, 1, 19500102