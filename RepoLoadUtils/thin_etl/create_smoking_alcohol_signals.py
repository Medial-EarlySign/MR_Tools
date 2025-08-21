import os, re, subprocess, traceback, random
from datetime import datetime
from common import *
import pandas as pd
import numpy as np
import sys
from Configuration import Configuration



def getLines(basePath, fileName):
    fileP = os.path.join(basePath, fileName)
    fp = open(fileP, 'r')
    lines = fp.readlines()
    lines = filter(lambda x: len(x.strip()) > 0 ,lines)
    fp.close()
    return lines

	
def load_smoke_alcohol():

		#===========================  configuration ===========================

		print ("ceate smoking and alcohol registry .....  ")

		cfg = Configuration()

		text_path = fixOS(cfg.doc_source_path)
		out_folder = fixOS(cfg.output_path)
		data_path = fixOS(cfg.raw_source_path)
		text_path = fixOS(cfg.doc_source_path)
		reg_list_folder = fixOS(cfg.reg_list_path)
		work_path  = fixOS(cfg.work_path)

		#data_path = "/server/Data/THIN1701/THINDB1701/"    						  #for data
		#out_folder = "/server/Work/Users/Barak/hyper/"   						  #output folder
		#text_path = "/server/Data/THIN1701/THINAncil1701/text/"					  #get medcode descriptio fron THIN database
		freq_file = "AHDReadcodeFrequencyEver1701.txt"     						  #med code file
		#reg_list_folder = "/server/UsersData/barak/MR/Tools/Registries/Lists/"    #list folder



		#H:\MR\Tools\Registries\Lists

		files = {}

		files['Alcohol_quantity'] = os.path.join(reg_list_folder,"alcohol_type_quan_list.txt") 
		files['Smoking_quantity'] = os.path.join(reg_list_folder,"smoking_type_quan_list.txt")


		#===========================  read pre files ===========================

		#read medcode desc
		print ("read medcode desc...")
		medcode_desc = {}
		for l in file(os.path.join(text_path,freq_file)):       
			medcode = l[:7]
			desc = l[7:69]
			medcode_desc[medcode] = desc
			

		#read id2nr
		print("read id2nr ....")
		lines = getLines(work_path, 'ID2NR')
		id2nr = read_id2nr(lines)
		print("read "+str(len(id2nr)) +" from id2nr .... ")

		#read def file
		print("read def file ... ")


		from collections import defaultdict
		d = defaultdict(list)
		d_sig = {}

		signals = ['Alcohol_quantity', 'Smoking_quantity']
		sh_stats = {}
		for temp_sig in signals:
			sh_stats[temp_sig]=0
			temp_file = files[temp_sig]
			list_df = pd.read_table(temp_file)

			for index , row in list_df.iterrows():
				med_code = row['read_codes']
				type = row['type']
				quantity = row['quantity']
				
				d[med_code].append(type)
				d[med_code].append(quantity)
				
				d_sig[med_code] = temp_sig

		
		#my_med= 'E23..00'		
		#print(my_med , d_sig[my_med])
		#exit()
			
			

		#==============================  run through prac and ids ==================================
		print ("run through prac and ids")
		in_file_names = list(filter(lambda f: f.startswith('ahd') ,os.listdir(data_path)))
		print("writing", os.path.join(out_folder, "alcohol_signal.txt"))
		print("writing", os.path.join(out_folder, "smoking_signal.txt"))
		out_files = {}
		out_files[signals[0]] = open(os.path.join(out_folder, "alcohol_signal.txt"), 'w')
		out_files[signals[1]] = open(os.path.join(out_folder, "smoking_signal.txt"), 'w')
		#error_file = open(os.path.join(create_reg_folder, signal_name+"_error_file.txt"), 'w')
		#log_file = open(os.path.join(create_reg_folder, signal_name+"_log_file.txt"), 'w')

		


		#in_file_names = ['ahd.c6801']
		#id_not_in_idsnr = {}
		count=0
		count_in=0
		count_out=0
		
		
		data = defaultdict(list)
		for file_name in in_file_names:
			pracid = file_name[4:]
			count+=1
			print (file_name , count , len(in_file_names))
			#if (count>3): break
			for l in file(os.path.join(data_path,file_name)):       
				
				eventdate = l[4:12]
				medcode = l[101:108]
				patid = l[0:4]
				data1 = l[23:36].strip()
				data2 = l[36:49].strip()
				if medcode not in d: continue
				
				combid = pracid + patid
				if combid not in id2nr:
					#id_not_in_idsnr[combid]=1
					#error_file.write("id not in id2nr"+"\t"+str(pracid)+"\t"+str(patid)+"\n")
					continue
				else:
					my_id = id2nr[combid]
				
				#ahdcode = l[12:22]
				#ahdflag = l[22:23]
				#data1 = l[23:36]
				#data2 = l[36:49]
				#data3 = l[49:62]
				#data4 = l[62:75]
				#data5 = l[75:88]
				#data6 = l[88:101]
				#medcode = l[101:108]
				
				#patid, eventdate, ahdcode, ahdflag, data1, data2, data3, data4, data5, data6, medcode = parse_ahd_line(l)
				
				temp_sig = d_sig[medcode]
				sh_stats[temp_sig]+=1
				#if medcode in d:

				type = d[medcode][0]
				quan = d[medcode][1]
				
				#==in type==
				# 1 - ex
				# 2 - current smoke/alcohol
				# 3 - complex
				# 4 - never smoke/alcohol
				# 5 - current not smoking/alcohol history unknown
				# 6 - screening test 
				# 7 special code
				
				#==out type ===
				# 1 ex
				# 2 current
				# 3 never
				# 4 current not ex unknown
				# 5 special group
				def get_final(type, quantity, data1, data2):
					final_quantity = -1
					final_type = -1
					if (type==1 or type==2):
						#cuurent/ex with quantity defined
						final_quantity = quan
						final_type = type
					elif (type==3):
						
						#cuurent/ex with quantity from params
						if data1=='Y':
							#current smoker
							final_type = 2
							temp_quantity = data2
							if (data2=='' or data2=='0'):
								final_quantity = -9
							else:
								final_quantity = data2
						if data1=='D':
							#ex smoker
							final_type = 1
							if (data2=='' or data2=='0'):
								final_quantity = -9
							else:
								final_quantity = data2
						if data1=='N':
							#non smoker
							final_type = 3
							final_quantity = 0
					
					elif (type==4):
						#current not history not
						final_type = 3
						final_quantity = 0
					elif (type==5):
						#current not smoking history unknown
						final_type = 4
						final_quantity = 0
					elif (type==6):
						#fast test score
						if (data1!='' and data1>=1):
							final_type = 2
							final_quantity = -9
					elif (type==7):
						#special list
						final_type = 5
						final_quantity = -9
					return final_type, final_quantity
				
				final_type, final_quantity = get_final(type, quantity, data1, data2)
				#log_file.write(str(my_id) + "\t" + pracid + "\t" + patid +  "\t" + str(eventdate) + "\t" + str(final_type) + "\t" + str(final_quantity) + "\t")
				#if medcode in medcode_desc: desc = medcode_desc[medcode] else : desc= '-1'
				#log_file.write(medcode + "\t" + desc + "\t" + data1 + "\t" + data2 +  "\n")
					
				
				#signal_file.write(str(my_id) + "\t" + temp_sig + "\t" +  str(eventdate) + "\t" + str(final_type) + "\t" + str(final_quantity) + "\n")
				#alon
				
				
				if (final_type==-1 and final_quantity==-1):
					count_out+=1
					#print(medcode , temp_sig , type , quan , final_type, final_quantity , data1 , data2,patid  )
				else:
					count_in+=1
					data[temp_sig].append((my_id, temp_sig, eventdate, final_type, final_quantity, medcode))

			
			medical_file_name = file_name.replace('ahd', 'medical')
			print (medical_file_name , count , len(in_file_names))
			for l in file(os.path.join(data_path,medical_file_name)):
				eventdate = l[4:12]
				medcode = l[22:29]
				patid = l[0:4]
				if medcode not in d: continue
				combid = pracid + patid
				if combid not in id2nr:
					continue
				else:
					my_id = id2nr[combid]
					
				temp_sig = d_sig[medcode]
				sh_stats[temp_sig]+=1
				type = d[medcode][0]
				quan = d[medcode][1]
				final_type, final_quantity = get_final(type, quantity, '', '')
				if (final_type==-1 and final_quantity==-1):
					count_out+=1
				else:
					count_in+=1
					data[temp_sig].append((my_id, temp_sig, eventdate, final_type, final_quantity, medcode))
			

					
		print("count_in : ",count_in)
		print("count_out : ",count_out)

		for k, v in data.items():
			v.sort()
			for l in v:
				out_files[k].write(unicode("\t".join(map(str, l)) + '\n'))
			out_files[k].close()

		for key in sh_stats.keys():
			print(key , sh_stats[key])
		
		#error_file.close()
		#log_file.close()




		#======================================== thin definitions =========================================================



		#==========alcohol def from thin

		#C	Current	- If the closest record prior to last date is current alcohol and there are no subsequent records of ex-alcohol or non-alcohol
		#X	Ex	- If the closest record prior to last date is non- alcohol but previous records are current alcohol or ex-alcohol, or last record is ex-alcohol
		#T	Non	- If there are no records with current alcohol or ex-alcohol at any time and a record of non- alcohol
		#U	Unknown	- If there are no records found for current alcohol, ex-alcohol or non-alcohol


		#DRI     DRINKER                       D     Alcohol status - Ex drinker                                                                         
		#DRI     DRINKER                       DRI000null value                                                                                          
		#DRI     DRINKER                       N     Alcohol status - Lifelong Teetotaller                                                               
		#DRI     DRINKER                       Y     Alcohol status - Current drinker     

		#CLINICAL1003050000Alcohol                                                                                             
			#DRINKER                       
			#UNITS(WEEK)                   
			#STARTDRINK(DATE)              
			#STOPDRINK(DATE)                                                                           


			
		#==========alcohol def from thin
			
		#CLINICAL1003040000Smoking                                                                                             
		#SMOKER                        
		#CIGARETTES(DAY)               
		#CIGARS(DAY)                   
		#TOBACCO_OUNCES(DAY)           
		#STARTSMOKE(DATE)              
		#STOPSMOKE(DATE)               	


		#SMO     SMOKER                        D     Smoking status - Ex smoker                                                                          
		#SMO     SMOKER                        N     Smoking status - Never smoked                                                                       
		#SMO     SMOKER                        SMO000null value                                                                                          
		#SMO     SMOKER                        Y     Smoking status - Current smoker    



if __name__ == "__main__":
    load_smoke_alcohol()


