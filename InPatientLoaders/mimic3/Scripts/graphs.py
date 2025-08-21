from __future__ import print_function
from collections import defaultdict
from datetime import datetime
import sys, os, math, random, socket, time
from scipy.stats.mstats import normaltest
from numpy import histogram

import sys, os
sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils', 'thin_etl'))
from bin_selections import binSelection, binarySearch, histRange

import traceback, subprocess
from scipy import stats



def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def strip_names(str):
    return str.replace('/','_over_')
	
def normVec(vec):
    totSum = sum(vec)
    return list(map( lambda x: x/float(totSum) ,vec))
	
def throwOutlyers(vec, min_th = 0.001, max_th = 0.999):
	if len(vec) == 0:
		raise NameError('vec is empty in throw outlyers')
	s_vals = sorted(vec)
	min_val = s_vals[int(len(vec)* min_th)]
	max_val = s_vals[int((len(vec)-1)* max_th)]
	#vec = list(map(lambda x: x if x >= min_val and x <= max_val else min_val if x< min_val else max_val ,vec))
	vec = list(filter(lambda x: x >= min_val and x <= max_val ,vec))
	return vec
	
def createHtmlGraph_series(x, y, seriesNum, seriesName = None):
    if len(x) != len(y):
        raise NameError('x and y vectors must be same size. x_size=%d, y_szie=%d'%(len(x), len(y)))
    if seriesName == None:
        seriesName = 'data'

    res = 'var series%d = {\n mode : \'lines+markers\',\n'%(seriesNum)
    res = res + 'x: [%s],\n'%( ', '.join( map( lambda v : '%2.4f'%v if type(v) == float else '\'%s\''%v ,x) ) )
    res = res + 'y: [%s],\n'%( ', '.join( map( lambda v : '%2.4f'%v ,y) ) )
    res = res + 'name: \'%s\' \n'%seriesName
    res = res + '};\n'
    return res

def createHtmlGraph(vec_x, vec_y, outputFile, html_data_path, xName = 'x', yName = 'y', vec_names = None):
    
	[path,name] = os.path.split(outputFile)
	
	if not(os.path.exists(fixOS(html_data_path))):
		raise NameError('please set your html_data_path in Configuration correctly')
	jsFilePath = os.path.join(fixOS(html_data_path), 'plotly-latest.min.js')
	if not(os.path.exists(jsFilePath)):
		raise NameError('please set your html_data_path in Configuration correctly - js file is missing')
	htmlPath = os.path.join(fixOS(html_data_path), 'Graph_HTML.txt')
	if not(os.path.exists(htmlPath)):
		raise NameError('please set your html_data_path in Configuration correctly - html file is missing')
	
	if (len(vec_x) != len(vec_y)):
		raise NameError('vec_x and vec_y must be same size')
	if len(vec_x) == 0:
		raise NameError('got empty series to plot')
	if type(vec_x[0]) != list:
		vec_x = [vec_x]
		vec_y = [vec_y]
		vec_names = ['data']
    
	# Copy plotly-latest.min.js if required
	if not(os.path.exists(os.path.join(path, 'plotly-latest.min.js'))):
		fp = open(jsFilePath, 'r')
		data = fp.read()
		fp.close()
		fo = open(os.path.join(path, 'plotly-latest.min.js'), 'w')
		fo.write(data)
		fo.close()

	fp = open(htmlPath, 'r')
	templateData = fp.read()
	fp.close()

	data = ''
	for i in range(len(vec_x)):
		data  = data + createHtmlGraph_series(vec_x[i], vec_y[i],  i, vec_names[i])

	data = data + 'var data = [%s];\n'%( ', '.join( map( lambda vv : 'series%d'%vv , range(len(vec_x))) ) )
	data = data + 'layout = { title:\'%s\', xaxis: { title : \'%s\' }, yaxis: { title : \'%s\' }, height : 800, width : 1200 };\n'%(name, xName, yName)
	templateData = templateData.replace('{0}', data)
	fo = open(outputFile, 'w')
	fo.write(templateData)
	fo.close()
    
def hist(vector):
    d = dict()
    for v in vector:
        if d.get(v) is None:
            d[v] = 0
        d[v] = d[v] + 1
    return d

def checkNormal(vector):
	return normaltest(vector).pvalue

def fixOS(pt):
    isUnixPath = pt.find('\\') == -1
    if ((os.name != 'nt' and isUnixPath) or (os.name == 'nt' and not(isUnixPath))):
        return pt
    elif (os.name == 'nt'):
        res = 'C:\\USERS\\' + get_user()
        if (pt.startswith('/nas1') or pt.startswith('/server')):
            res = '\\\\nas3'
            pt = pt.replace('/nas1', '').replace('/server', '')
        pt = pt.replace('/', '\\')
        res= res + pt
        return res
    else:
        res = ''
        if pt.startswith('\\\\nas1') or pt.startswith('\\\\nas3') :
            res = '/nas1'
            pt = pt.replace('\\\\nas1', '')
            pt = pt.replace('\\\\nas3', '')
        elif pt.startswith('C:\\Users\\') :
            res = os.environ['HOME']
            pt = pt.replace('C:\\Users\\', '')
            pt = pt[ pt.find('\\'):]
        elif pt.startswith('H:\\'):
            res = os.path.join('/nas1/UsersData', get_user().lower() )
            pt = pt.replace('H:', '')
        elif pt.startswith('W:\\'):
            res = '/nas1/Work'
            pt = pt.replace('W:', '')
        elif pt.startswith('T:\\'):
            res = '/nas1/Data'
            pt = pt.replace('T:', '')
        elif pt.startswith('U:\\'):
            res = '/nas1/UserData'
            pt = pt.replace('U:', '')
        elif pt.startswith('X:\\'):
            res = '/nas1/Temp'
            pt = pt.replace('X:', '')
        else:
            eprint('not support convertion "%s"'%pt)
            raise NameError('not supported')
        pt = pt.replace('\\', '/')
        res= res + pt
        return res


