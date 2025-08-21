#!/bin/python
from flask import Flask
from flask import request, url_for
from Configuration import Configuration
from signal_mapping_api import listAllTargets, searchSignal, searchSignalAndTarget, commitSignal, addMissingSignals, getTargetSources, mapSourceTarget, confirmSignal
from signal_unite_api import unite_signals, unite_all_signal
from signal_stats_api import statsUnitedSig, statsFixedSig, getSignalUnitRes, getSignalByUnit
from signal_fix_api import fixAllSignal, fixSignal
from signal_config_api import *
from signal_unit_api import ignoreRareUnits, compareUnitHist, clearSupportUnits, addAllWithFactor, getUnitStatsForSignal
from datetime import datetime
from pini_stats import showAhd

import os

app = Flask(__name__)

def readMap():
    cfg = Configuration()
    fp = open( os.path.join( fixOS(cfg.code_folder), 'thin_signals_to_united.txt'), 'r')
    lines = fp.readlines()
    fp.close()
    lines = lines[1:] #without header
    res = list(map(lambda v: v.strip().split('\t') ,lines))
    res = sorted(res, key = lambda v: v[0])
    return res

@app.route('/actions/get_ahdcode')
def getAhdcode():
    ahdcode = request.args.get('code', '')
    if len(ahdcode) == 0 :
        raise NameError('please pass ahdcode')
    tups = showAhd(ahdcode, False)
    if tups is not None and len(tups) > 0:
        tblStr = """%s"""%( '\n'.join( list(map( lambda rw: '<tr> <td>%s</td><td>%s</td><td>%d</td> </tr>'%(rw[0], rw[2], rw[1])  ,tups))) )
    else:
        tblStr = ""
    return """<html>
     <head>
     <script src="/static/jquery.min.js"></script>
     <script src="/static/bootstrap.min.js"></script>
     <script>
     function openAhd() {
         var code = $('#ahdCode').val();
         window.location.href = '/actions/get_ahdcode?code=' + code;
     }
    
     </script>
     <link rel="stylesheet" href="/static/bootstrap.min.css"></link>
     <title>Ahdcode %s Details</title></head>
     <body>
     <div align="center">
     <label for="ahdCode">ahdcode:</label>
     <input type="text" name="ahdCode" id="ahdCode" value="%s"></input><br />
     <input type="button" value="Show Details" onclick="openAhd()"></input>
     </div>
     <div align="center">
     <table class="table table-stripe">
     <thead>
     <th>readcode</th> <th>Description</th> <th>Count</th>
     </thead>
     <tbody>
     %s
     </tbody>
     </table>
     <a href="/">Home</a>
     </div>
     </body>
     </html>
"""%(ahdcode, ahdcode ,tblStr)

@app.route('/actions/signal_rows')
def getNumRows():
    signalName = request.args.get('signal', '')
    if (len(signalName) ==0 ):
        raise NameError('please pass signal name')
    cfg = Configuration()
    source_dir =  os.path.join( fixOS(cfg.work_path), 'Common')
    if not(os.path.exists(source_dir)):
        raise NameError('source dir not exists. config problem?')

    res = 0
    sourceFiles = getTargetSources(signalName)
    for srcFile in sourceFiles:
        fullP = os.path.join(source_dir, srcFile)
        if os.path.exists(fullP):
            fp = open(fullP, 'r')
            num_lines = 0
            for line in fp:
                num_lines = num_lines + 1
            res = res + num_lines
            fp.close()
    return '%s %s'%(signalName, str(res))

@app.route('/actions/confirm_test')
def confirm_test():
    signalName = request.args.get('signal', '')
    if (len(signalName) ==0 ):
        raise NameError('please pass signal name')
    confirmSignal(signalName)
    return 'Success!'

def getSignalStatus(sigName):
    cfg = Configuration()
    source_dir =  os.path.join( fixOS(cfg.work_path), 'Common')
    if not(os.path.exists(source_dir)):
        raise NameError('source dir not exists. config problem?')
    sourceFiles = getTargetSources(sigName)
    allSrcExists = True
    for srcFile in sourceFiles:
        fullP = os.path.join(source_dir, srcFile)
        if not(os.path.exists(fullP)):
            allSrcExists = False
            break
    if not(allSrcExists):
        return ['Map', 'Not All Source File Exists' , None]
    
    united_dir =  os.path.join( fixOS(cfg.work_path), 'United')
    if not(os.path.exists(source_dir)):
        raise NameError('united dir not exists. config problem?')
    sigNamePath = sigName.replace('/','_over_')
    united_full = os.path.join(united_dir, sigNamePath)

    state = 'Map'
    comment = 'Waiting for Unite'
    dt=  None
    rUnited = None
    if not(os.path.exists(united_full)):
        return [state, comment, dt]
    else:
        state = 'United'
        rUnited = os.path.getmtime(united_full)
        dt = datetime.fromtimestamp(rUnited).strftime('%d-%m-%Y %H:%M:%S')
        comment = 'Waiting For Fix'
        
    fixed_dir =  os.path.join( fixOS(cfg.work_path), 'Fixed')
    if not(os.path.exists(fixed_dir)):
        raise NameError('fixed dir not exists. config problem?')
    fixed_full = os.path.join(fixed_dir, sigNamePath)
    rFixed = None
    if not(os.path.exists(fixed_full)):
        return [state, comment, dt]
    else:
        rFixed = os.path.getmtime(fixed_full)
        if rFixed < rUnited:
            comment = 'Update Fix File'
            return [state, comment, dt]
        else:
            state=  'Fixed'
            dt = datetime.fromtimestamp(rFixed).strftime('%d-%m-%Y %H:%M:%S')
            comment = 'Waiting for tests'

    code_dir = fixOS(cfg.code_folder)
    if not(os.path.exists(code_dir)):
        raise NameError('please add codeDir')
    fullPt = os.path.join(code_dir, 'confirm_signals.txt')
    if not(os.path.exists(fullPt)):
        return [state, comment, dt]
    else:
        fp = open(fullPt, 'r')
        lines = fp.readlines()
        fp.close()
        for line in lines:
            tokens = line.split('\t')
            if len(tokens) != 2:
                raise NameError('Format Error %s'%line)
            if tokens[0].strip() == sigName:
                approved = datetime.strptime(tokens[1].strip(), '%d-%m-%Y %H:%M:%S')
                approveDt = (approved - datetime(1970, 1, 1)).total_seconds()
                #approveDt = approveDt.timestamp()
                if approveDt < rFixed:
                    comment = 'already approved in the past'
                else:
                    dt = tokens[1].strip()
                    state = 'Done'
                    comment = ''
                
    return [state, comment, dt]

def getAllSourceCnt():
    cfg = Configuration()
    workDir = fixOS(cfg.work_path)
    if not(os.path.exists(workDir)):
        raise NameError('configuration error? can''t find work_dir')
    commonVals = os.path.join(workDir,'CommonValues')
    if not(os.path.exists(commonVals)):
        raise NameError('cant''t finc commonVal file')
    fp = open(commonVals, 'r')
    lines = fp.readlines()
    fp.close()
    srcCnt = dict()
    for line in lines:
        if len(line.strip()) == 0:
            continue
        tokens= line.split('\t')
        if len(tokens) != 3:
            raise NameError('Format Error in commonVals')
        sigKey = tokens[0].strip()
        cnt = int(tokens[1].strip())
        if srcCnt.get(sigKey) is None:
            srcCnt[sigKey] = 0
        srcCnt[sigKey] += cnt
        
    return srcCnt

def getAllSignalCounts():
    cfg = Configuration()
    workDir = fixOS(cfg.work_path)
    if not(os.path.exists(workDir)):
        raise NameError('configuration error? can''t find work_dir')
    commonVals = os.path.join(workDir,'CommonValues')
    if not(os.path.exists(commonVals)):
        raise NameError('cant''t finc commonVal file')
    fp = open(commonVals, 'r')
    lines = fp.readlines()
    fp.close()
    sigCnt = dict()
    srcToTargt = mapSourceTarget()
    for line in lines:
        if len(line.strip()) == 0:
            continue
        tokens= line.split('\t')
        if len(tokens) != 3:
            raise NameError('Format Error in commonVals')
        sigKey = tokens[0].strip()
        cnt = int(tokens[1].strip())
        if srcToTargt.get(sigKey) is None:
            #eprint ('Couldn''t find %s'%sigKey)
            #sigCnt[srcToTargt[sigKey]] = 0
            pass
        else:
            targetName = srcToTargt[sigKey].replace('/','_over_')
            if sigCnt.get(targetName) is None:
                sigCnt[targetName] = 0
            sigCnt[targetName] += cnt
    
    return sigCnt

def getAllSignalStatus():
    sigCnt = getAllSignalCounts()   
    tups = list(sorted(sigCnt.items(), key = lambda kv : kv[1], reverse = True))
    signaleOrdered = list(map(lambda kv: kv[0],tups))
    res = []
    for signal in signaleOrdered:
        numOfRows = '0'
        if sigCnt.get(signal) is not None:
            numOfRows = str(sigCnt[signal])
        status, comment, updateDate = getSignalStatus(signal)
        
        unitStats = getUnitStatsForSignal(signal, True)
        supportedPerc = 'Unknown'
        if len(unitStats) > 0:
            unitStat2 = set(clearSupportUnits(signal, unitStats))
            totCnt = sum(list(map(lambda v: v[1] ,unitStats)))
            sumNotSupported = sum(map(lambda kv: kv[1] ,filter( lambda kv: kv[0] in  unitStat2 ,unitStats)))
            supportedPerc = 100.0 * ( totCnt - sumNotSupported)  / float(totCnt)
            supportedPerc = '%2.2f'%supportedPerc
        
        if updateDate is None:
            updateDate = ''
        res.append( [signal,  numOfRows, status, comment, updateDate, supportedPerc ] )
    return res

@app.route('/')
def index():
    signals = getAllSignalStatus()
    signalsStatus = '\n'.join(map(lambda v: '<tr class="%s"> <td>%s</td> <td class="get_row" id="row_%s">%s</td> <td>%s</td> <td>%s</td> <td>%s</td> <td>%s</td> </tr>'%( 'mark-yes' if v[2] == 'Done' else '' ,v[0], v[0].replace('/','_over_') ,v[1], v[2], v[3] , v[4], v[5]) ,signals))
    return """
     <html>
     <head>
     <script src="/static/jquery.min.js"></script>
     <script src="/static/bootstrap.min.js"></script>
     <script>
       $( document ).ready(function() {
          //allSigs = $('.get_row')
          //for (i = 0; i < allSigs.length; i++) {
               //sig = $(allSigs[i]);
               //sigName = escape(sig.attr('id').substr(4).replace('_over_', '/'))
              // $.get('/actions/signal_rows?signal=' + sigName, function(data) {
               //   v = data.split(' ');
                //  var sig = v[0].replace('/','_over_')
                //  $('#row_' + sig).text(v[1]);
              // } ).fail( function() {} );
          //}
      });
     </script>
     <link rel="stylesheet" href="/static/bootstrap.min.css"></link>
     <link rel="stylesheet" href="/static/site.css"></link>
     <title>Signal Proccessing ETL Site</title></head>
     <body>
     <div class= "list-group" align="center">
     <a class="list-group-item" href="/mapping" target="_blank">Step 1 - Map Lab test files to signal</a>
     <a class="list-group-item" href="/unite" target="_blank">Step 2 - Unite Signals</a>
     <a class="list-group-item" href="/signal_stats" target="_blank">Step 3 - Test United Signal Stats</a>
     <a class="list-group-item" href="/config_units" target="_blank">Step 4 - Configure Units</a>
     <a class="list-group-item" href="/fix" target="_blank">Step 5 - Fix Signal</a>
     <a class="list-group-item" href="/signal_stats" target="_blank">Step 6 - Test Fixed Signal stats</a>
     </div>
     <div align="center">
     <h1>Signals Status</h1>
     <table class="table table-stripe">
     <thead>
     <th>Signal</th> <th>NumOfRows</th> <th>Status</th> <th>Comments</th> <th>Update Date</th> <th>Unit Support Ratio</th>
     </thead>
     <tbody>
     %s
     </tbody>
     </table>
     </div>
     </body>
     </html>
"""%(signalsStatus)



@app.route('/config_units')
def config_units():
    targets = list(map(lambda sigName : sigName.replace('/','_over_') ,listAllTargets().keys()))
    lsEle = '\n'.join(list(map(lambda x: '<option value="%s">'%x ,targets)))
    return """
<html>
     <head>
     <script src="/static/jquery.min.js"></script>
     <script src="/static/bootstrap.min.js"></script>
     <link rel="stylesheet" href="/static/site.css"></link>
     <script>
     function get_signal_info() {
         var sigName = escape($('#signalName').val());
          $('#status').text('Running On ' + sigName);
         $.get('/actions/signal_unit_info?signal=' + sigName, function(data) {
             $('#signal_units').html(data);
             $('#status').text('Success!');
         }).fail(function(exp) {
         var errorTitle = exp.responseText.match(/<title[^>]*>([^<]+)<\/title>/)[1];
         $('#status').text('Fail!' + errorTitle);
         } );
     }

       function get_only_config() {
         var sigName = escape($('#signalName').val());
          $('#status').text('Retrieving Config for ' + sigName);
         $.get('/actions/signal_unit_info?signal=' + sigName + '&fast=1', function(data) {
             $('#signal_units').html(data);
             $('#status').text('Success!');
         }).fail(function(exp) {
         var errorTitle = exp.responseText.match(/<title[^>]*>([^<]+)<\/title>/)[1];
         $('#status').text('Fail!' + errorTitle);
         } );
     }

function set_default() {
          var sigName = escape( $('#signalN').val());
          var comUnit =escape( $('#default_unit').val());
          var sigRes = $('#default_res').val();
          var ignoreList  = $('#ignore_list').val();
          if (ignoreList.startsWith(',')) {
                ignoreList = ignoreList.substr(1)
          }
          ignoreList = escape(ignoreList)
          var factorList  = $('#factors').val();
          if (factorList.startsWith(',')) {
                factorList = factorList.substr(1)
          }
          var factor  = $('#final_factor').val();
          var supposeMean = $('#supposeMean').val();
          $('#status').text('Setting Default to ' + sigName);
           $.get('/actions/set_default?signal=' + sigName + '&commonUnit=' + comUnit + '&sigRes=' + sigRes + '&ignoreList=' + ignoreList + '&factorList=' + factorList +  '&factor=' + factor + '&supposeMean=' + supposeMean, function(data) { $('#status').html(data); }).fail(function(exp) {
           var errorTitle = exp.responseText.match(/<title[^>]*>([^<]+)<\/title>/)[1];
           $('#status').text('Fail!' + errorTitle);
           } );
       }

       function set_unit() {
          var sigName = escape($('#signalN').val());
          var unit_name = escape($('#unit_name').val());
          var unit_factor = $('#unit_factor').val();
          $('#status').text('Setting Unit to ' + sigName);
           $.get('/actions/set_unit?signal=' + sigName + '&unitName=' + unit_name + '&factor=' + unit_factor, function(data) { $('#status').html(data); }).fail(function(exp) {
           var errorTitle = exp.responseText.match(/<title[^>]*>([^<]+)<\/title>/)[1];
           $('#status').text('Fail!' + errorTitle);
           } );
       }

      function ignore_units() {
          var sigName = escape($('#signalN').val());
          var unitCnt = $('#unitCnt').val();
          var unitPerc = $('#unitPerc').val();
          $('#status').text('Ignoring Units on ' + sigName);
           $.get('/actions/ignore_units?signal=' + sigName + '&unitCnt=' + unitCnt + '&unitPerc=' + unitPerc, function(data) { $('#status').html(data); }).fail(function(exp) {
           var errorTitle = exp.responseText.match(/<title[^>]*>([^<]+)<\/title>/)[1];
           $('#status').text('Fail!' + errorTitle);
           } );
       }

    function get_unit() {
          var sigName = escape($('#signalN').val());
          var unit_name = escape($('#unit_name').val());
          $.get('/actions/get_unit?signal=' + sigName + '&unitName=' + unit_name, function(data) {
          $('#unit_factor').val(data);
          }).fail(function(exp) { } );
    }

    function compare_hists() {
          var sigName = escape($('#signalN').val());
          var unit_list = escape($('#unitCompare').val());
          $('#status').text('');
          $.get('/actions/compare_units?signal=' + sigName + '&unitList=' + unit_list, function(data) {
              $('#status').text(data);
          }).fail(function(exp) {
             var errorTitle = exp.responseText.match(/<title[^>]*>([^<]+)<\/title>/)[1];
             $('#status').text('Faild!' + errorTitle);
          } );
    }

     </script>
     <link rel="stylesheet" href="/static/bootstrap.min.css"></link>
     <title>Config Units for Signal</title></head>
     <body>
     <div align="center">
     <label for="signalName">Signal Name:</label>
     <datalist id="signalList">%s</datalist>
     <input type="text" name="signalName" id="signalName" list="signalList"></input>
     <input type="button" value="Get Info" onclick="get_signal_info()"></input>
     <input type="button" value="Get only config" onclick="get_only_config()"></input>
     <pre id="status"></pre>
     </div>
     <span id="signal_units" align="left"></span>
     <div align="center">
     <a href="/">Home</a>
     </div>
     </body>
     </html>
"""%(lsEle)

@app.route('/actions/signal_unit_info')
def getSignalUnitsInfo():
    sigName = request.args.get('signal', '')
    fast = request.args.get('fast', '')
    if len(sigName) == 0:
        raise NameError('please pass arguments')
    
    defaults = config_get_default(sigName)
    wasEmpty = False
    if len(defaults) == 0:
        defaults = [sigName,  '', '', '', '', '', '']
        wasEmpty = True
    fetchFull = (len(fast) == 0)
    if fetchFull:
        unitStat = getUnitStatsForSignal(sigName)
        mostCommonUnit = unitStat[0][0]
        unitStat2 = set(clearSupportUnits(sigName, unitStat))
        listItems = '\n'.join(list(map(lambda x: '<option value="%s">'%x[0] ,unitStat)))
        totCnt = sum(list(map(lambda v: v[1] ,unitStat)))
        mapRows = map( lambda v : '<tr class="%s"><td>%s</td><td>%d</td><td>%2.3f%%</td><td>%s</td><td>%s</td></tr>'%('mark-yes' if v[0] not in unitStat2 else 'mark-no', v[0], v[1], 100.0*v[1]/float(totCnt) , 'Yes' if v[0] not in unitStat2 else 'No', config_get_unit(sigName, v[0]) ), unitStat)
        if wasEmpty:
            sigRes = getSignalUnitRes(sigName, mostCommonUnit)
            defaults = [sigName,  mostCommonUnit, sigRes, '', '', '', '']
    else:
        mapRows = []
        listItems = ''
    tdata = '\n'.join(list(mapRows))
    htmlData = """
    <datalist id="unitList">%s</datalist>
    <h3>Unit Configuration for %s</h3>
    <input id="signalN" name="signalN" type="hidden" value="%s"></input>
    <label for="default_unit">Unit</label>
    <input name="default_unit" id="default_unit" type="text" list="unitList" value="%s"></input><br />
    <label for="default_res">Resulotion</label>
    <input name="default_res" id="default_res" type="number" step="any" value="%s"></input><br />
    <label for="ignore_list">IgnoreList:</label>
    <input name="ignore_list" id="ignore_list" type="text" value="%s"></input><br />
    <label for="factors">Factors:</label>
    <input name="factors" id="factors" type="text" value="%s"></input><br />
    <label for="final_factor">Final Factor:</label>
    <input name="final_factor" id="final_factor" type="number" step="any" value="%s"></input><br />
    <label for="supposeMean">Suppose Value Mean:</label>
    <input name="supposeMean" id="supposeMean" type="number" step="any" value="%s"></input><br />
    <input type="button" value="Set Default" onclick="set_default()"></input> <br /> <br />

    <label for="unit_name">Unit</label>
    <input name="unit_name" id="unit_name" type="text" list="unitList" onkeyup="get_unit()"></input><br />
    <label for="unit_factor">Factor</label>
    <input name="unit_factor" id="unit_factor" type="number" step="any"></input><br />
    <input type="button" value="Set Unit" onclick="set_unit()"></input> <br /> <br />
    <span align="center"><table class="table" style="display: block; height: 400px; overflow-y: auto;"><thead>
    <th>Unit Name</th> <th>Count</th> <th>Percentage</th> <th>Supported</th> <th>factor</th>
    </thead><tbody>
    %s
    </tbody></table></span>
    <label for="unitCnt">Maximal Count Filter:</label>
    <input type="text" name="unitCnt" id ="unitCnt" values="100"></input>
    <label for="unitPerc">Maximal ratio Filter:</label>
    <input type="text" name="unitPerc" id ="unitPerc" values="0.0001"></input>
    <input type="button" value="Ignore Units" onclick="ignore_units()"></input><br />

    <label for="unitCompare">Unit Compare List</label>
    <input type="text" name="unitCompare" id ="unitCompare"></input><br />
    <input type="button" value="Compare Units Histograms" onclick="compare_hists()"></input>
    """%(listItems, sigName, sigName,defaults[1], defaults[2], defaults[3], defaults[4], defaults[5], defaults[6], tdata)
    return htmlData 

@app.route('/fix')
def fix():
    targets = list(map(lambda sigName : sigName.replace('/','_over_') ,listAllTargets().keys()))
    lsEle = '\n'.join(list(map(lambda x: '<option value="%s">'%x ,targets)))
    return """
<html>
     <head>
     <script src="/static/jquery.min.js"></script>
     <script src="/static/bootstrap.min.js"></script>
     <script>
     function signal_fix() {
         var sigName = escape($('#signalName').val());
          $('#status').text('Running On ' + sigName); 
         $.get('/action/fix_signal?signal=' + sigName, function(data) { $('#status').text(data); }).fail(function(exp) {
         var errorTitle = exp.responseText.match(/<title[^>]*>([^<]+)<\/title>/)[1];
         $('#status').text('Fail!' + errorTitle);
         } );
     }
     function signal_all_fix() {
         $('#status').text('Fixing All Signals..'); 
         $.get('/action/fix_all_signals', function(data) { $('#status').text(data); }).fail(function(exp) {
         var errorTitle = exp.responseText.match(/<title[^>]*>([^<]+)<\/title>/)[1];
         $('#status').text('Fail!' + errorTitle);
         } );
     }
     </script>
     <link rel="stylesheet" href="/static/bootstrap.min.css"></link>
     <title>Fix Signal</title></head>
     <body>
     <div align="center">
     <label for="signalName">Signal Name:</label>
     <datalist id="signalList">%s</datalist>
     <input type="text" name="signalName" id="signalName" list="signalList"></input><br />
     <input type="button" value="Fix Signal" onclick="signal_fix()"></input>
     <input type="button" value="Fix All Signals" onclick="signal_all_fix()"></input>
     <pre id="status"></pre>
     </div>
     <div align="center">
     <a href="/">Home</a>
     </div>
     </body>
     </html>
"""%(lsEle)

@app.route('/signal_stats')
def signal_stats():
    targets = list(map(lambda sigName : sigName.replace('/','_over_') ,listAllTargets().keys()))
    lsEle = '\n'.join(list(map(lambda x: '<option value="%s">'%x ,targets)))
    return """
<html>
     <head>
     <script src="/static/jquery.min.js"></script>
     <script src="/static/bootstrap.min.js"></script>
     <script>
     function signal_stats_united() {
         var sigName = escape($('#signalName').val());
          $('#status').text('Running On ' + sigName + ' United'); 
         $.get('/action/stats_signal_united?signal=' + sigName, function(data) { $('#status').text(data); }).fail(function(exp) {
         var errorTitle = exp.responseText.match(/<title[^>]*>([^<]+)<\/title>/)[1];
         $('#status').text('Fail!' + errorTitle);
         } );
     }
     function signal_stats_fixed() {
         var sigName = escape($('#signalName').val());
         $('#status').text('Running On ' + sigName + ' Fixed'); 
         $.get('/action/stats_signal_fixed?signal=' + sigName, function(data) { $('#status').text(data); }).fail(function(exp) {
         var errorTitle = exp.responseText.match(/<title[^>]*>([^<]+)<\/title>/)[1];
         $('#status').text('Fail!' + errorTitle);
         } );
     }

     function mark_done() {
          var sigName = escape($('#signalName').val());
          $('#status').text('Marking On ' + sigName);
          $.get('/actions/confirm_test?signal=' + sigName, function(data) {
              
              $('#status').text(data);
          }).fail(function(exp) {
           var errorTitle = exp.responseText.match(/<title[^>]*>([^<]+)<\/title>/)[1];
          $('#status').text('Fail!' + errorTitle);
          } );
     }
     
     </script>
     <link rel="stylesheet" href="/static/bootstrap.min.css"></link>
     <title>Signal Stats</title></head>
     <body>
     <div align="center">
     <label for="signalName">Signal Name:</label>
     <datalist id="signalList">%s</datalist>
     <input type="text" name="signalName" id="signalName" list="signalList"></input><br />
     <input type="button" value="United Signal Stats" onclick="signal_stats_united()"></input>
     <input type="button" value="Fixed Signal Stats" onclick="signal_stats_fixed()"></input>
     <pre id="status"></pre>
     </div>
     <div align="center">
     <input type="button" value="Mark Signal As Done" onclick="mark_done()"></input>
     </div>
     <div align="center">
     <a href="/">Home</a>
     </div>
     </body>
     </html>
"""%(lsEle)

@app.route('/unite')
def unite_page():
    targets = list(map(lambda sigName : sigName.replace('/','_over_') ,listAllTargets().keys()))
    lsEle = '\n'.join(list(map(lambda x: '<option value="%s">'%x ,targets)))
    return """
<html>
     <head>
     <script src="/static/jquery.min.js"></script>
     <script src="/static/bootstrap.min.js"></script>
     <script>
     function unite_signal() {
         var sigName = escape($('#signalName').val());
          $('#status').text('Running On ' + sigName); 
         $.get('/action/unite_signal?signal=' + sigName, function(data) { $('#status').text(data); }).fail(function(exp) {
         var errorTitle = exp.responseText.match(/<title[^>]*>([^<]+)<\/title>/)[1];
         $('#status').text('Fail!' + errorTitle);
         } );
     }
     function unite_all() {
         $.get('/action/unite_all', function(data) { $('#status').text(data); }).fail(function(exp) {
         var errorTitle = exp.responseText.match(/<title[^>]*>([^<]+)<\/title>/)[1];
         $('#status').text('Fail!' + errorTitle);
         } );
     }
     </script>
     <link rel="stylesheet" href="/static/bootstrap.min.css"></link>
     <title>Unite Signal</title></head>
     <body>
     <div align="center">
     <label for="signalName">Signal Name:</label>
     <datalist id="signalList">%s</datalist>
     <input type="text" name="signalName" id="signalName" list="signalList"></input><br />
     <input type="button" value="Unite Signal" onclick="unite_signal()"></input>
     <input type="button" value="Unite All" onclick="unite_all()"></input><br />
     <pre id="status"></pre>
     </div>
     <div align="center">
     <a href="/">Home</a>
     </div>
     </body>
     </html>
"""%(lsEle)

@app.route('/mapping')
def mapping():
    tp = readMap()
    srcCnt = getAllSourceCnt()
    tp = list(map( lambda v: [v[0], v[1], str(srcCnt[v[0]]) if  srcCnt.get(v[0]) is not None else 'Unknown', srcCnt[v[0]] if srcCnt.get(v[0]) is not None else 0 ] ,tp))
    tp = sorted(tp, key = lambda vec : vec[-1], reverse=True)
    tblLines = list(map( lambda v : '<tr>%s</tr>'%(' '.join(list(map( lambda x: '<td>%s</td>'%x  ,v[:-1]) ))) , tp)  )
    
    tblData = '\n'.join(tblLines)
    searchBar = '<div align="center"><label for="search">Search</label><input name="search" id="search" type="text" onkeyup="filterRes()"></input></div>'
    searchSc = """
 function filterRes() {
  // Declare variables 
  var input, filter, table, tr, td, i;
  input = document.getElementById("search");
  filter = input.value.toUpperCase();
  table = document.getElementById("myTable");
  tr = table.getElementsByTagName("tr");
  var re = new RegExp(filter, "i");

  // Loop through all table rows, and hide those who don't match the search query
  for (i = 0; i < tr.length; i++) {
    td = tr[i].getElementsByTagName("td")[0];
    td2 = tr[i].getElementsByTagName("td")[1];
    if (td) {
      if (re.test(td.innerHTML) || re.test(td2.innerHTML)) {
        tr[i].style.display = "";
      } else {
        tr[i].style.display = "none";
      }
    } 
  }
}

function commitTarget() {
   searchRegex = document.getElementById("search").value;
   targetStr = document.getElementById("target").value;
   $.get('/action/mapSignal?regex=' + searchRegex + '&target=' + targetStr, function() { location.reload(); } ).fail(function(exp) {
    var errorTitle = exp.responseText.match(/<title[^>]*>([^<]+)<\/title>/)[1];
   $('#status').text('Failed!' + errorTitle)
   } );
   
   
}
"""
    commitBox='<div align="center"><label for="target">Target</label><input name="target" id="target" type="text"></input><input type="button" onclick="commitTarget()" value="Send"></input> <span id="status"></span> </div>'
    tblStr = '<div class="container"><table id="myTable" class="table table-striped" style="display: block; height: 800px; overflow-y: auto;"><thead><th>LabTest FileName</th><th>Target</th><th>RowCount</th></thead><tdata>%s</tdata></table></div>'%tblData
    allHtml = """
<html>
     <head>
     <script src="/static/jquery.min.js"></script>
     <script src="/static/bootstrap.min.js"></script>
     <link rel="stylesheet" href="/static/bootstrap.min.css"></link>
     <script>%s</script>
     <title>Map Lab Tests</title></head>
     <body>%s %s %s  <div align="center">
     <a href="/">Home</a>
     </div></body>
     </html>"""%(searchSc, searchBar,tblStr, commitBox)
    return allHtml

@app.route('/action/mapSignal', methods=['GET'])
def commit_target():
    searchRegex=  request.args.get('regex', '')
    targetStr=  request.args.get('target', '')
    if len(searchRegex) == 0 and len(targetStr) == 0:
        raise NameError('please pass arguments')
    commitSignal(searchRegex , targetStr)
    return "commit %s -  %s"%(searchRegex , targetStr)

@app.route('/action/add_missing_signals', methods=['GET'])
def add_missing_signals():
    addMissingSignals()
    return "Done"

@app.route('/action/unite_signal', methods=['GET'])
def unite_signal():
    signal = request.args.get('signal', '')
    if len(signal) == 0:
        raise NameError('please pass arguments')
    msgs = unite_signals(signal)
    return "\n".join(msgs)

@app.route('/action/unite_all', methods=['GET'])
def unite_all_signal():
    msgs = unite_all_signal()
    return "\n".join(msgs)

@app.route('/action/stats_signal_united', methods=['GET'])
def stats_signal_united():
    signal = request.args.get('signal', '')
    if len(signal) == 0:
        raise NameError('please pass arguments')
    msgs, tups = statsUnitedSig(signal)
    return "\n".join(msgs)

@app.route('/action/stats_signal_fixed', methods=['GET'])
def stats_signal_fixed():
    signal = request.args.get('signal', '')
    if len(signal) == 0:
        raise NameError('please pass arguments')
    msgs = statsFixedSig(signal)
    return "\n".join(msgs)

@app.route('/action/fix_signal', methods=['GET'])
def fix_signal():
    signal = request.args.get('signal', '')
    if len(signal) == 0:
        raise NameError('please pass arguments')
    fixSignal(signal)
    return "Success!"

@app.route('/action/fix_all_signals', methods=['GET'])
def fix_all_signals():
    fixAllSignal()
    return "Success!"

@app.route('/actions/set_unit')
def set_unit():
    signal = request.args.get('signal', '')
    unitName = request.args.get('unitName', '')
    factor = request.args.get('factor', '')
    if len(signal) == 0 or len(unitName) == 0 or len(factor) == 0:
        raise NameError('please pass arguments')

    config_set_unit(signal, unitName, factor)
    return "Success!"

@app.route('/actions/set_default')
def set_default():
    signal = request.args.get('signal', '')
    comUnit = request.args.get('commonUnit', '')
    sigRes = request.args.get('sigRes', '')
    ignoreList = request.args.get('ignoreList', '')
    factorList = request.args.get('factorList', '')
    factor = request.args.get('factor', '')
    supposeMean = request.args.get('supposeMean', '')
    if len(signal) == 0 or len(comUnit) == 0 or len(sigRes) == 0:
        raise NameError('please pass arguments')

    ign = []
    if len(ignoreList) > 0:
        ign = ignoreList.split(',')
    facts = []
    if len(factorList) > 0:
        facts = factorList.split(',')
    finalFact = None
    if len(factor) > 0:
        finalFact = float(factor)
    config_set_default(signal, comUnit, sigRes, ign , facts, finalFact, supposeMean)
    return "Success!"

@app.route('/actions/ignore_units')
def ignore_units():
    signal = request.args.get('signal', '')
    unitCnt = request.args.get('unitCnt', '')
    unitPerc = request.args.get('unitPerc', '')
    if len(signal) == 0:
        raise NameError('please pass arguments')
    if len(unitCnt) > 0:
        unitCnt = float(unitCnt)
    else:
        unitCnt = None
    if len(unitPerc) > 0:
        unitPerc = float(unitPerc)
    else:
        unitPerc = None
    ignoreRareUnits(signal, unitCnt, unitPerc)
    return "Success!"

@app.route('/actions/get_unit')
def getUnitVal():
    signal = request.args.get('signal', '')
    unitName = request.args.get('unitName', '')
    if len(signal) == 0 or len(unitName) == 0:
        raise NameError('please pass arguments')
    return config_get_unit(signal, unitName)

@app.route('/actions/compare_units')
def compareUnits():
    cfg = Configuration()
    signal = request.args.get('signal', '')
    unitList = request.args.get('unitList', '')
    if len(signal) == 0 or len(unitList) == 0:
        raise NameError('please pass arguments')
    tokens = unitList.split(',')
    unit_vec = list(map( lambda v: v.strip() ,tokens))
        
    unitWarn = compareUnitHist(signal, unit_vec, 0.0001)
    #unitWarn = compareUnitHist('HCG', ['IU/L', 'null value'], 0.0001)
    if len(unitWarn) == 0:
        unitWarn= ['All Graph are similar - you can watch them in "%s"'%( os.path.join(fixOS(cfg.output_path), signal + '_units', 'compare_all_series.html') )]
    else:
        unitWarn.append( 'You can watch Graph in "%s"'%( os.path.join(fixOS(cfg.output_path), signal + '_units', 'compare_all_series.html') ))
    return "\n".join(unitWarn)
    
def run_server():
    app.run(host='0.0.0.0',debug=True, threaded=True, port=5000)
    url_for('static', filename='bootstrap.min.css')
    url_for('static', filename='bootstrap.min.js')
    url_for('static', filename='jquery.min.js')
    url_for('static', filename='site.css')

if __name__ == '__main__':
    run_server()
