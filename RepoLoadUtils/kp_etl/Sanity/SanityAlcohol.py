# -*- coding: utf-8 -*-
"""
Created on Thu May  3 11:18:18 2018

@author: Ron
"""

import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime
import matplotlib.pyplot as plt
import copyFig


def isNaN(num):
    return num != num

sourceDir = r'D:\Databases\kpsc\03-05-2018'
fileCaseDemo = r'\cases_demo.txt'
fileCaseTumor = r'\cases_tumor.txt'
fileControlDx1 = r'\controls_dx1.txt'
fileControlDemo = r'\controls_demo.txt'
fileControlCbc =  r'\controls_cbc.txt'
fileCaseSmoking = r'\'cases_smoking.txt'
fileControlSmoking = r'\'controls_smoking.txt'
fileCaseAlcohol = r'\cases_alcohol.txt'
fileControlAlcohol = r'\controls_alcohol.txt'


dfCaseAlcohol = pd.read_csv(sourceDir + fileCaseAlcohol, delimiter = '\t')
dfControlAlcohol = pd.read_csv(sourceDir + fileControlAlcohol, delimiter = '\t')

len(dfCaseAlcohol.id.unique())
