# -*- coding: utf-8 -*-
"""
Created on Mon Apr 16 13:52:54 2018

@author: Ron
"""
from os import listdir
from os.path import isfile, join

filename = 'kp1.convert_config'
directoryWin = 'D:/KP/'
directoryWin_out = 'D:/KP/out/'
directory  = 	'/server/Work/Users/Ron/KP'
directory_out = '/server/Work/Users/Ron/KP/out'

signalfiles = [f for f in listdir(directoryWin) if ((isfile(join(directoryWin, f)) and (f[-3:] == 'txt')))]
dictfiles = [f for f in listdir(directoryWin) if ((isfile(join(directoryWin, f)) and (f[0:4] == 'dict')))]

outStr = "#\n# convert config file\n#\n"
outStr += "DESCRIPTION" + "\t" + "KPSC Lung Cancer\n"
outStr += "RELATIVE\t1\n"
outStr += "SAFE_MODE\t1\n"
outStr += "SIGNAL" + "\t" + "kp.signals"+"\n"
outStr += "DIR\t"+ directory +"\n"
outStr += "OUTDIR\t" + directory_out + "\n"


for file in dictfiles:
    outStr += "DICTIONARY\t" + file + "\n"
    
outStr += "MODE\t3\n"
outStr += "PREFIX\tkp_rep\n"
outStr += "CONFIG\tkp.repository\n"
outStr += "FORCE_SIGNAL\tGENDER,BYEAR\n"

for file in signalfiles:
    outStr += "DATA\t" + file + "\n"
    
      
with open(directoryWin + filename, "wb") as text_file:
    text_file.write(str.encode(outStr))
