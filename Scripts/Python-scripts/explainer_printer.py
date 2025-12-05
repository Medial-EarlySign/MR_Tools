#!/usr/bin/env python
import argparse, os, re, string, math

template_path = os.path.join(os.path.dirname( os.path.realpath(__file__)), 'templates', 'explainer_single.template.html')
if not(os.path.exists(template_path)):
    raise NameError('File not found %s'%template_path)
fr = open(template_path, 'r')
template_txt = fr.read()
fr.close()

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

class Sett:
    def __init__(self, pid=0, time=1, outcome=2, pred=3, explain=4, explain_details=5, delimiter='\t', has_header=True, skip_lines=['SCORES', 'PID_VIEWER_URL']):
        self.pid=pid
        self.time=time
        self.outcome=outcome
        self.pred=pred
        self.explain=explain
        self.explain_details=explain_details
        self.delimeter=delimiter
        self.has_header=has_header
        self.skip_lines=set(skip_lines)

def read_explain_pred(path, s):
    if not(os.path.exists(path)):
        raise NameError('File not found %s'%path)
    fr = open(path, 'r')
    lines = fr.readlines()
    fr.close()
    if s.has_header:
        lines=lines[1:]
    lines=list(filter(lambda x: len(x.strip()) >0 and x.strip().split(s.delimeter)[0] not in s.skip_lines ,lines))
    order_col=[s.pid, s.time, s.pred, s.explain, s.explain_details]
    header = ['pid', 'time','pred', 'explain', 'explain_details']
    if s.outcome is not None:
        order_col=[s.pid, s.time, s.outcome, s.pred, s.explain, s.explain_details]
        header = ['pid', 'time', 'outcome', 'pred', 'explain', 'explain_details']
    data = list(map(lambda line: line.split(s.delimeter),lines))
    data = list(map(lambda r: [r[i] if i < len(r) else None for i in order_col] ,data))
    return header, data

def clear_name(name):
    if name.startswith('FTR_'):
        name = name[name.find('.')+1:]
    return name

def handle_missing(num, missing_value_num, alt = -1):
    if num == missing_value_num:
        return alt
    return num

def format_explain(predictor_name, pid,time,outcome,pred, explain_list, details_list, output_path, verbose):
    if verbose:
        print('Going to print exaplin graph into %s'%(output_path))
    text = template_txt
    val_format='%2.6f'
    #//edit GRAPH_TITLE, FEATURE_NAMES, SHAP_VEC
    text = text.replace('$GRAPH_TITLE$','%s'%('%s - Explain for %d at time %d with pred %f'%(predictor_name, pid, time, pred)))
    
    tuples_vals = []
    for i in range(len(explain_list)):
        tokens=explain_list[i].split(':=')
        if len(tokens) != 2:
            raise NameError('Format Error - expected 2 tokens with \":=\". Got \"%s\"'%(explain_list[i]))
        feat_name=tokens[0]
        feat_contrib=tokens[1] #read till (
        if feat_contrib.find('(') >= 0:
            feat_contrib=feat_contrib[:feat_contrib.find('(')]
        feat_val=None
        if feat_name.find('(') >= 0:
            feat_val=float(feat_name[feat_name.find('(')+1:-1])
            feat_name=feat_name[:feat_name.find('(')]
        feature_nm_name = feat_name
        feature_nm_value = feat_val
        feature_contrib = None
        if details_list[i] is not None:
            tokens=details_list[i].split(':=')
            if len(tokens) != 2:
                raise NameError('Format Error - expected 2 tokens in details with \":=\". Got \"%s\"'%(details_list[i]))
            feature_nm=tokens[0]
            feature_contrib=tokens[1]
            if feature_contrib.find('(') >= 0:
                feature_contrib=feature_contrib[:feature_contrib.find('(')]
            if feature_nm.find('(') >= 0:
                feature_nm_name=feature_nm[:feature_nm.find('(')]
                feature_nm_value=float(feature_nm[feature_nm.find('(')+1:-1])
            else:
                feature_nm_name=feature_nm
        if feature_nm_value is None:
            feature_nm_value = ''
        if feature_nm_name=='Gender':
            feature_nm_value= 'Male' if feat_val==1 else 'Female'
        else:
            feature_nm_value='%f'%(feature_nm_value)
        tuples_vals.append( [clear_name(feat_name), float(feat_contrib),  '%s=%s'%(feature_nm_name,feature_nm_value) ] )
    #sort by contrib in abs:
    #tuples_vals = sorted(tuples_vals, key = lambda kv: abs(kv[1]), reverse = True)
    txt_vals = []
    txt_features = []
    txt_labels= []
    tuples_vals = sorted(tuples_vals, key = lambda kv: abs(kv[1]), reverse = False)
    for feature_name,contrib,feat_val in tuples_vals:
        txt_features.append("'" + feature_name + "'")
        txt_vals.append(val_format%(contrib))
        if feat_val is None:
            txt_labels.append("''")
        else:
            txt_labels.append("'"+str(feat_val)+ "'")
    text = text.replace('$FEATURE_NAMES$','%s'%(', '.join(txt_features)))
    text = text.replace('$SHAP_VEC$','%s'%(', '.join(txt_vals)))
    text = text.replace('$TEXT_LABELS$','%s'%(', '.join(txt_labels)))

    fw = open(output_path, 'w')
    fw.write(text)
    fw.close()
    if verbose:
        print('Done print report for pid %d in %s'%(pid, predictor_name))

def create_key(pid, time):
    return '%d_%d'%(pid,time)

def reverse_key(key):
    t=key.split('_')
    return int(t[0]),int(t[1])
#output - Global feature importance or feature influence graphs
def print_multiple(header, data, max_count, output_path, filter_pid, predictor_name):
    pid_time_records = dict()
    pid_time_outcome = dict()
    pid_time_pred = dict()
    pid_time_details = dict()
   
    for i in range(len(data)):
        pid=int(data[i][0])
        if filter_pid is not None and pid != filter_pid:
            continue
        time=int(data[i][1])
        k=create_key(pid,time)
        if k not in pid_time_records:
            pid_time_records[k] = []
            pid_time_details[k] = []
            if len(header) > 4:
                pid_time_outcome[k] = int(data[i][2])
                pid_time_pred[k] = float(data[i][3])
            else:
                pid_time_pred[k] = float(data[i][2])
        pid_time_records[k].append(data[i][-2])
        pid_time_details[k].append(data[i][-1])
    #use pid_time_records,pid_time_outcome,pid_time_pred and create graphs:
    if not(os.path.exists(output_path)):
        os.mkdir(output_path)
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    prt = 0
    for key, explain_list in pid_time_records.items():
        prety_name = 'explain_' + ''.join(c for c in key if c in valid_chars) + '.html'
        pid,time=reverse_key(key)
        pred=pid_time_pred[key]
        details_list = pid_time_details[key]
        outcome=None
        if key in pid_time_outcome:
            outcome=pid_time_outcome[key]
        format_explain(predictor_name, pid,time,outcome,pred, explain_list, details_list, os.path.join(output_path, prety_name), prt==0)
        prt = prt + 1
        if max_count > 0 and prt >= max_count:
            break
    
def get_columns(s):
    res = list(map(lambda x: int(x),s.split(',')))
    if len(res)==5:
        res = res[:2] + [None] + res[2:]
    if len(res)!=6:
        raise NameError('Should have at least 5-6 columns as input, seperated by \",\".')
    return res

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Print nice report of explain report")
    parser.add_argument("--report_path",help="the input report path to analyze for nice print",required=True)
    parser.add_argument("--output_path",help="the output file path",required=True)
    parser.add_argument("--has_header",help="if report file has header", type=str2bool,default=True)
    parser.add_argument("--deli",help="Delimeter",default='\t')
    parser.add_argument("--skip_lines",help="first token in line to skip with \";\" to seperate",default='SCORES;PID_VIEWER_URL')
    parser.add_argument("--columns",help="columns order for: pid,time,outcome(optional),pred,explain",default='0,1,2,3,4,5')
    parser.add_argument("--max_count",help="the maximal count to print reports", type=int,default=10)
    parser.add_argument("--filter_pid",help="If given will only create graphs for pid", type=int,default=-1)
    parser.add_argument("--predictor_name",help="predictor name to show in title",default='prediction')

    args = parser.parse_args() 
    #if given feature_name - will do : format_feature_inf. otherwise: format_global_importance
    col_nums=get_columns(args.columns)
    s=Sett(col_nums[0], col_nums[1], col_nums[2], col_nums[3], col_nums[4], col_nums[5], args.deli, args.has_header, args.skip_lines.split(';'))
    
    header, data=read_explain_pred(args.report_path, s)
    print('Read %s'%(args.report_path))
    print_multiple(header, data, args.max_count, args.output_path, None if args.filter_pid < 0 else args.filter_pid, args.predictor_name)
    