#!/usr/bin/env python
import sys, os, traceback, time, socket, subprocess, re, urllib
import argparse
from datetime import datetime
from flask import Flask, request, url_for
from viewers_config import *
use_urlib2=True
try:
    import urllib2
    import thread
except:
    import urllib.request
    import urllib.parse
    import _thread as thread
    use_urlib2=False

app = Flask(__name__)
#global variables to be accessed by Flask - all will be changed by config
index_port=8000
g_server_name=None
g_server_address=None
g_javascript_dir = None
g_server_app_path = ''
all_viewers_server = []
html_index_path_g = ''

def process_exists(rep_name):
    call ='ps -ef | grep SimpleHttpServer | grep %s | grep -v grep | wc -l'%(rep_name)
    output = subprocess.check_output(call, shell=True).decode()
    output = int(output.strip())
    return output>0

def test_viewer(cfg, server_app, server_address):
    rep_exists=process_exists(cfg.rep_path)
    if not(rep_exists):
        if cfg.process is not None:
            cfg.last_error = str(cfg.process.stdout.read()[-1000:].decode('ascii'))
            fw = open(cfg.log_error_file,'w')
            fw.writelines(cfg.last_error)
            fw.close()
        if cfg.index_page is not None:
            call='%s --rep "%s" --server_dir "%s" --plotly_config "%s" --port %d --index_page %s --address %s'%(server_app, 
                cfg.rep_path, cfg.java_script_dir, cfg.config_path, cfg.port, cfg.index_page, server_address)
        else:
            call='%s --rep "%s" --server_dir "%s" --plotly_config "%s" --port %d --address %s'%(server_app, 
                cfg.rep_path, cfg.java_script_dir, cfg.config_path, cfg.port, server_address)
        print('#### Will Execute #####')
        print(call)
        print('#######################')
        cfg.process = subprocess.Popen(call, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return True
    return False

def get_req_count(v, host_name):
    if host_name is None:
        host_name = socket.gethostname()
    full_l = 'http://%s:%d/count'%(host_name, v.port)
    try:
        if use_urlib2:
            response = urllib2.urlopen(full_l)
        else:
            response = urllib.request.urlopen(full_l)
            
        html = response.read().decode('ascii')
        num_reg=re.compile('There have been ([0-9]+) requests')
        res=num_reg.findall(html)
        if len(res)==1:
            return int(res[0])
    except:
        return -1
    return -1

def get_html(all_viewers, html_index_path, host_name = None, ip_address = None, server_app_path = None):
    if host_name is None:
        host_name = socket.gethostname()
    all_rows=[]
    for v in all_viewers:
        full_l = 'http://%s:%d'%(host_name, v.port)
        uptime_txt='Down'
        rep_escape=v.rep_path
        if use_urlib2:
            rep_escape = urllib.quote(rep_escape, safe='')
        else:
            rep_escape = urllib.parse.quote(rep_escape, safe='')
        Error_link = 'http://%s:%d/error?rep=%s'%(host_name, index_port, rep_escape)
        if v.up_time is not None:
            uptime_txt='%s'%(v.up_time)
            req_cnt=get_req_count(v, ip_address)
        all_rows.append('\t\t<tr>\n\t\t\t<td>%s</td><td><a href="%s" target="_blank">%s</a></td><td>%d</td><td>%s</td><td>%s</td><td><a href="%s" target="_blank">%s</a></td>\n\t\t</tr>'%(v.rep_path, full_l, full_l,
                                                                                                            v.start_cnt-1, uptime_txt, '%d'%(req_cnt) if req_cnt >= 0 else 'Starting up...', Error_link, 'Last Error'))
    if server_app_path is not None:
        all_rows.append('\t\t<tr><th colspan="6" style="text-align: center; vertical-align: middle;">Application Run Path: %s</th></tr>'%(server_app_path))
        
    fr = open(html_index_path, 'r')
    full_html = fr.read()
    fr.close()
    full_html=full_html%('\n'.join(all_rows))
    return full_html

@app.route('/error')
def show_error():
    rep_filter = request.args.get('rep', '')
    if len(rep_filter)==0:
        return 'Please pass rep as GET parameter to filter errors'
    for v in all_viewers_server:
        if v.rep_path == rep_filter:
            if v.last_error is not None:
                return '<html><body><p>Last Error for %s:</p><textarea rows="30" cols="200">%s</textarea></body></html>'%(rep_filter, v.last_error)
            else:
                return '<html><body><p>No Errors for %s:</p></body></html>'%(rep_filter)
    return 'Not found repository %s'%(rep_filter)

@app.route('/')
def index():
    return get_html(all_viewers_server, html_index_path_g, g_server_name, g_server_address, g_server_app_path)

def flaskThread():    
    app.static_folder=g_javascript_dir
    app.static_url_path='static'
    app.run(host='0.0.0.0',debug=False, threaded=True, port=index_port)
    url_for('static', filename='bootstrap.min.css')
    url_for('static', filename='bootstrap.min.js')

def run_all(server_app, server_address, sleep_interval, all_viewers,
            html_index_path, index_port_, server_name, default_javascript):
    if server_app is None:
        if 'MR_ROOT' not in os.environ:
            raise NameError('MR_ROOT is not defined in the environment - Please define or pass server_app')
        server_app = os.path.join(os.environ['MR_ROOT'], 'Tools', 'AllTools', 'Linux', 'Release', 'SimpleHttpServer')
    global g_server_app_path
    g_server_app_path = server_app
    global index_port
    index_port = index_port_
    global g_server_name
    g_server_name = server_name
    
    global g_javascript_dir
    g_javascript_dir = default_javascript
    if g_javascript_dir is None:
        if 'MR_ROOT' not in os.environ:
            raise NameError('MR_ROOT is not defined in the environment - Please define or pass javascript_dir')
        g_javascript_dir = os.path.join(os.environ['MR_ROOT'], 'Libs', 'Internal', 'MedPlotly', 'JavaScript')
    
    if html_index_path is None:
        html_index_path = os.path.join(os.path.dirname( os.path.realpath(__file__)), 'templates', 'viewers_index.html')
    global html_index_path_g
    html_index_path_g = html_index_path
    if not(os.path.exists(html_index_path)):
        raise NameError('Can\'t find template html for index viewers at %s'%(html_index_path))
    
    global g_server_address
    if server_address is None:
        output = subprocess.check_output('ifconfig | grep -v "LOOPBACK" | egrep RUNNING -A1', shell=True).decode().strip().split('\n')
        if len(output)!=2:
            print('Please specify IP Adrerss of server - can\'t find it automatically. Options:\n%s'%output)
            raise NameError('Error - IP Address can\'t be found automatically')
        server_address=str(output[-1].strip().split()[1])
    g_server_address = server_address
    print('GETTING UP SERVER AT IP %s using app %s'%(server_address, server_app))
    
    global all_viewers_server
    all_viewers_server=all_viewers
    
    thread.start_new_thread(flaskThread, ())
    
    while True:
        for viewer_c in all_viewers:
            try:
                started = test_viewer(viewer_c, server_app, server_address)
                if started:
                    viewer_c.up_time=datetime.now()
                    viewer_c.start_cnt+=1
                    print('STARTED_VIEWER %s'%(viewer_c.rep_path))
            except:
                traceback.print_exc()
        all_viewers_server=all_viewers
        time.sleep(sleep_interval)

if __name__ == '__main__':
    cfg = FullCfg()
    run_all(cfg.server_app, cfg.server_address, cfg.sleep_interval,
            cfg.all_viewers, cfg.html_index_template, cfg.index_port,
            cfg.server_name, cfg.javascript_dir)
    
    
        
        
