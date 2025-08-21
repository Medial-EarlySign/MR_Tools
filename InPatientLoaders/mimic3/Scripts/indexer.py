#!/usr/bin/python
import csv
import numpy as np

# A class for Reading indexed files	
class mimic3_readers():
	# Read index file
	def read_index(self,dir,name):
		fileName = dir + "/" + name + ".npy" 
		self.positions[name] = np.load(fileName)
		
	# Read Lines
	def read_lines(self,dir,name,id):
		outLines = []
		if (name not in self.files.keys()):
			fileName = dir + "/" + name + ".csv" 
			self.files[name] = open(fileName,"r")
			self.readers[name] = csv.reader(self.files[name])
			header = self.readers[name].next()
			self.headers[name] = {header[i] : i for i in range(len(header))}
			if (self.identifier not in self.headers[name].keys()):
				raise ValueError("File \'%s\' does not have %s column"%(name,self.identifier))
			else:
				self.idCols[name] = self.headers[name][self.identifier]
				
			self.read_index(dir,name)
	
		if (id > self.maxId):
			raise ValueError("Cannot get id %d (Max = %d)\n"%(id,self.maxId))
			
		start = self.positions[name][id]
		if (start != -1):
			self.files[name].seek(start)
			for row in self.readers[name]:
				if (int(row[self.idCols[name]]) != id):
					break
				outLines.append(row)

		return outLines, self.headers[name]
	# Init
	def __init__(self):
		self.files = {}
		self.readers = {}
		self.positions = {}
		self.headers = {}
		self.idCols = {}
		self.maxId = 100000 ;
		self.identifier = "SUBJECT_ID"
		

