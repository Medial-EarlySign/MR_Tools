# -*- coding: utf-8 -*-
"""
Created on Wed Dec  5 11:43:02 2018

@author: Ron
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Oct 24 14:19:48 2018

@author: Ron
"""
import os 
import datetime as dt
import pandas as pd

def convertDir(dirName):
    # Assumes #
    dirName = dirName.replace('\\',"/")
    if os.name == 'nt':
        #windows
        dirName = dirName.replace('/nas1/UsersData/ron/','H:/')
        dirName = dirName.replace('/nas1/Work/','W:/')
        dirName = dirName.replace('/server/UsersData/ron/','H:/')
        dirName = dirName.replace('/server/Work/','W:/')
        dirName = dirName.replace('Linux','x64')
    else:
        dirName = dirName.replace('H:/','/nas1/UsersData/ron/')
        dirName = dirName.replace('W:/','/nas1/Work/')
        dirName = dirName.replace('U:/','/nas1/UsersData/')
        dirName = dirName.replace('x64','Linux')
    
    return dirName


def convert_times(col):
    """
    Convert a time column given as minutes from 1900 to a datetime object
    Args:
        col: a pd.Series object
    Returns:
        the original col as a datetime object 
    """
    
    date_col=dt.datetime(1900,1,1)+pd.TimedeltaIndex(col,unit='m')
    return(date_col)