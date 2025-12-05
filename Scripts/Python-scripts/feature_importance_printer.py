#!/usr/bin/env python
import argparse, os, re, string, math, traceback

feature_inf_template_path = os.path.join(os.path.dirname( os.path.realpath(__file__)), 'templates', 'feature_importance.template.html')
feature_inf_template_many_path = os.path.join(os.path.dirname( os.path.realpath(__file__)), 'templates', 'feature_importance.template.many.html')
feature_glo_template_path = os.path.join(os.path.dirname( os.path.realpath(__file__)), 'templates', 'features_global.template.html')

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def read_feat_importance(path):
    if not(os.path.exists(path)):
        raise NameError('File not found %s'%path)
    fr = open(path, 'r')
    lines = fr.readlines()
    fr.close()
    header = list(map(lambda x: x.strip(), lines[0].split('\t')))
    lines = lines[1:]
    data = list(map(lambda line: list(map(lambda x: x.strip() ,line.split('\t'))),lines))
    return header, data

def select_alias(s):
    options=s.split('|')
    options = sorted(options, key=lambda x: len(x), reverse=True)
    return options[0]

class feature_data:
    def __init__(self):
        self.contrib = None
        self.min = None
        self.max = None
        self.median = None
        self.obs_cnt = None
        self.contrib_low = None
        self.contrib_high = None
        self.outcome_mean = None
        self.outcome_ci = [None, None]
        self.outcome_ci_p = [None, None]
        self.score_mean = None
        self.score_ci = [None, None]
        self.score_ci_p = [None, None]

def clear_name(name):
    if name.startswith('FTR_'):
        name = name[name.find('.')+1:]
    return name

def handle_missing(num, missing_value_num, alt = -1):
    if num == missing_value_num:
        return alt
    return num

def format_feature_inf(header, data, feat_name, val_format, output_path, contrib_format = '%2.1f', take_median = False,
                       missing_value_num=-65336, miss_replace = None, force_many_graph = False, silence = False):
    many_use_grp = 5
    if force_many_graph:
        many_use_grp = 1
    if not(silence):
        print('Going to print report for feature %s influence to %s'%(feat_name ,output_path))
    #fetch feature: - in title: Feature - first column
    name_index=0
    if 'Representative' in header:
        name_index=header.index('Representative')
    ind = []
    for i in range(len(data)):
        if (data[i][name_index] == feat_name):
            ind = [i]
            break
        if (data[i][name_index].find( feat_name) >= 0):
            ind.append(i)
    #check if has exact:
    
    if len(ind) > 1:
        exact_ind = None
        for i in ind:
            if data[i][name_index] == feat_name or clear_name(data[i][name_index]) == feat_name:
                exact_ind = i
                break
        if exact_ind is not None:
            ind = [exact_ind]
    
    if len(ind) == 0:
        raise NameError('Error - feature %s wasn\'t found in the report'%(feat_name))
    if len(ind) > 1:
        raise NameError('Error - feature %s has been found multiple times in the report: [%s]'%(feat_name, ', '.join(map(lambda x: data[x][0] ,ind)) ))
    row = data[ind[0]]
    search_pat = re.compile(r'SHAP::[^\s]+_Mean')
    if take_median:
        search_pat = re.compile(r'SHAP::[^\s]+_Prctile50')
    rng_pat = re.compile(r'FEAT_VAL::[^\s]+_Prctile(0|100|50)')

    #search for FEAT_VAL::$GROUP_NAME$_Prctile0 and FEAT_VAL::$GROUP_NAME$_Prctile100, FEAT_VAL::$GROUP_NAME$_Prctile50
    #search for SHAP::$GROUP_NAME$_Mean or SHAP::$GROUP_NAME$_Prctile50
    grp_shap_vals = dict()
    ord_feature = []
    for i in range(len(header)):
        h = header[i]
        if len(search_pat.findall(h)) > 0:
            clean_name = clear_name(h[6:].replace('_Mean','').replace('_Prctile50','').strip())
            f = feature_data()
            if len(row[i].strip()) == 0:
                continue
            f.contrib = float(row[i])
            grp_shap_vals[clean_name] = f
            ord_feature.append(clean_name)

    #Fill SHAP Error bars if exists!
    search_pat_ci = re.compile(r'SHAP::[^\s]+_Prctile[19]0')
    for i in range(len(header)):
        h = header[i]
        if len(search_pat_ci.findall(h)) > 0:
            nm_no_shap = h[6:]
            clean_name = clear_name(nm_no_shap[:nm_no_shap.find('_Prctile')].strip())
            if len(row[i].strip()) == 0:
                continue
            if clean_name not in grp_shap_vals:
                raise NameError('can\'t find %s in names: [%s]'%(clean_name, ','.join(grp_shap_vals.keys())))
            if nm_no_shap.endswith('_Prctile10'):
                grp_shap_vals[clean_name].contrib_low = float(row[i])
            elif nm_no_shap.endswith('_Prctile90'):
                grp_shap_vals[clean_name].contrib_high = float(row[i])
            else:
                raise NameError('can\'t find %s in prctile'%(nm_no_shap))
    
    sz_groups = len(grp_shap_vals)
    f_template_path = feature_inf_template_path
    if (sz_groups > many_use_grp):
        f_template_path = feature_inf_template_many_path
        if miss_replace is None:
            miss_replace = 'NaN'
    else:
        if miss_replace is None:
            miss_replace = 'Missing_Value'
    if not(os.path.exists(f_template_path)):
        raise NameError('File not found %s'%f_template_path)
    fr = open(f_template_path, 'r')
    text = fr.read()
    fr.close()
    #Change GRAPH_TITLE, TITLES, SHAP_VEC, COLOR_VAL
    text = text.replace('$GRAPH_TITLE$','%s'%(feat_name))
    
    for i in range(len(header)):
        h = header[i]
        if len(rng_pat.findall(h)) > 0:
            clean_name = clear_name(h[10:].replace('_Prctile100','').replace('_Prctile50','').replace('_Prctile0','').strip())
            if len(row[i].strip()) == 0:
                continue
            if clean_name not in grp_shap_vals:
                raise NameError('Error - bug can\'t find %s in [%s] - %s'%(clean_name, ', '.join(ord_feature), h ))
            f = grp_shap_vals[clean_name]
            if h.endswith('Prctile100'):
                f.max = handle_missing(float(row[i]), missing_value_num, None)
            elif h.endswith('Prctile50'):
                f.median = handle_missing(float(row[i]), missing_value_num, None)
            else:
                f.min = handle_missing(float(row[i]), missing_value_num, None)

    #search for all the rest:
    obs_cnt_pat=re.compile(r'FEAT_VAL::[^\s]+_Cnt')
    outcome_pat = re.compile(r'OUTCOME::[^\s]+_Mean')
    score_pat = re.compile(r'SCORE::[^\s]+_Mean')
    #outcome_range_pat = re.compile('OUTCOME::[^\s]+_Prctile')
    outcome_range_pat = re.compile(r'OUTCOME::[^\s]+_Std')
    score_range_pat = re.compile(r'SCORE::[^\s]+_Prctile')

    tot_cnt = 0
    for i in range(len(header)):
        h = header[i]
        if len(outcome_pat.findall(h)) > 0:
            clean_name = clear_name(h[9:].replace('_Mean','').strip())
            if len(row[i].strip()) == 0:
                continue
            if clean_name not in grp_shap_vals:
                raise NameError('Error - bug can\'t find %s in [%s] - %s'%(clean_name, ', '.join(ord_feature), h ))
            f = grp_shap_vals[clean_name]
            f.outcome_mean = float(row[i])
        if len(score_pat.findall(h)) > 0:
            clean_name = clear_name(h[7:].replace('_Mean','').strip())
            if len(row[i].strip()) == 0:
                continue
            if clean_name not in grp_shap_vals:
                raise NameError('Error - bug can\'t find %s in [%s] - %s'%(clean_name, ', '.join(ord_feature), h ))
            f = grp_shap_vals[clean_name]
            f.score_mean = float(row[i])
        if len(obs_cnt_pat.findall(h)) > 0:
            clean_name = clear_name(h[10:].replace('_Cnt','').strip())
            if len(row[i].strip()) == 0:
                continue
            if clean_name not in grp_shap_vals:
                raise NameError('Error - bug can\'t find %s in [%s] - %s'%(clean_name, ', '.join(ord_feature), h ))
            f = grp_shap_vals[clean_name]
            f.obs_cnt = float(row[i])
            if f.obs_cnt is not None:
                tot_cnt += f.obs_cnt

    for i in range(len(header)):
        h = header[i]
        if len(outcome_range_pat.findall(h)) > 0:
            clean_name = h[9:]
            #prc_num = float(clean_name[clean_name.find('_Prctile')+8:])
            clean_name = clear_name(clean_name[:clean_name.find('_Std')].strip())
            if len(row[i].strip()) == 0:
                continue
            if clean_name not in grp_shap_vals:
                raise NameError('Error - bug can\'t find %s in [%s] - %s'%(clean_name, ', '.join(ord_feature), h ))
            f = grp_shap_vals[clean_name]
            std_ci=1.96
            N_size=f.obs_cnt
            if f.outcome_mean <= 1:
                std_calc=math.sqrt(f.outcome_mean*(1-f.outcome_mean)/N_size)
            else:
                std_calc = 0
            rng_std=std_calc*std_ci
            f.outcome_ci_p[0]=0.025
            f.outcome_ci_p[1]=0.975
            f.outcome_ci[0]=f.outcome_mean-rng_std
            f.outcome_ci[1]=f.outcome_mean+rng_std
            #ind = None
            #if prc_num > 50:
            #    ind = 1
            #elif prc_num < 50:
            #    ind = 0
            #if ind is not None:
            #    if f.outcome_ci_p[ind] is None or prc_num < f.outcome_ci_p[ind]:
            #        f.outcome_ci_p[ind] = prc_num
            #        f.outcome_ci[ind] = float(row[i])
        if len(score_range_pat.findall(h)) > 0:
            clean_name = h[7:]
            prc_num = float(clean_name[clean_name.find('_Prctile')+8:])
            clean_name = clear_name(clean_name[:clean_name.find('_Prctile')].strip())
            if len(row[i].strip()) == 0:
                continue
            if clean_name not in grp_shap_vals:
                raise NameError('Error - bug can\'t find %s in [%s] - %s'%(clean_name, ', '.join(ord_feature), h ))
            f = grp_shap_vals[clean_name]
            ind = None
            if prc_num > 50 and prc_num < 100:
                ind = 1
            if prc_num < 50 and prc_num > 0:
                ind = 0
            if ind is not None:
                if f.score_ci_p[ind] is None or prc_num < f.score_ci_p[ind]:
                    f.score_ci_p[ind] = prc_num
                    f.score_ci[ind] = float(row[i])

                
    #print to graph:
    txt_titles = []
    txt_vals = []
    txt_colors = []
    txt_error_y_min = []
    txt_error_y_max = []
    txt_error_x_min = []
    txt_error_x_max = []
    txt_outcomes = []
    txt_counts = []
    txt_scores = []

    txt_outcomes_min = []
    txt_outcomes_max = []
    txt_scores_min = []
    txt_scores_max = []
    contrib_err_format=contrib_format
    format_float_reg = re.compile(r'%[0-9]+\.([0-9]+)f')
    if (len(format_float_reg.findall(contrib_err_format)) > 0):
        num=int(format_float_reg.findall(contrib_err_format)[0])+1
        contrib_err_format='%2.' +str(num) + 'f'
    elif contrib_err_format=='%d':
        contrib_err_format ='%2.1f'

    num_err_format=val_format
    if (len(format_float_reg.findall(num_err_format)) > 0):
        num=int(format_float_reg.findall(num_err_format)[0])+1
        num_err_format='%2.' +str(num) + 'f'
    elif num_err_format=='%d':
        num_err_format ='%2.1f'

    not_all_nan_score = False
    not_all_nan_outcome = False
    not_all_nan_counts = False
    info_ci_outcome = [None, None]
    info_ci_score = [None, None]

    cnt_sum = 0
    for feat in ord_feature:
        f = grp_shap_vals[feat]
        if (f.max is None or f.min is None):
            frm = miss_replace
        else:
            frm = '\'%s-%s\''%( val_format%(f.min), val_format%(f.max) )
        if (sz_groups > many_use_grp):
            if (f.median is None):
                frm = miss_replace
            else:
                frm = val_format%(f.median)
            if f.contrib_low is not None and f.contrib_high is not None:
                txt_error_y_min.append(contrib_err_format%(f.contrib_low))
                txt_error_y_max.append(contrib_err_format%(f.contrib_high))
            else:
                if len(txt_error_y) > 0:
                    txt_error_y.append('0')
            if (f.max is None or f.min is None):
                txt_error_x_min.append('NaN')
                txt_error_x_max.append('NaN')
            else:
                txt_error_x_min.append(num_err_format%(f.min))
                txt_error_x_max.append(num_err_format%(f.max))
            if f.outcome_mean is not None:
                txt_outcomes.append('%2.3f'%(100 * f.outcome_mean))
                not_all_nan_outcome = True
            else:
                txt_outcomes.append('NaN')
            if f.obs_cnt is not None:
                cnt_sum += f.obs_cnt
                txt_counts.append('%2.3f'%(100*cnt_sum/tot_cnt))
                not_all_nan_counts = True
            else:
                txt_counts.append('NaN')
            if f.score_mean is not None:
                txt_scores.append('%2.3f'%(100 * f.score_mean))
                not_all_nan_score = True
            else:
                txt_scores.append('NaN')
            if f.outcome_ci[0] is not None:
                txt_outcomes_min.append(num_err_format%(100*f.outcome_ci[0]))
                if info_ci_outcome[0] is None:
                    info_ci_outcome[0] = f.outcome_ci_p[0]
            else:
                txt_outcomes_min.append('NaN')
            if f.outcome_ci[1] is not None:
                txt_outcomes_max.append(num_err_format%(100*f.outcome_ci[1]))
                if info_ci_outcome[1] is None:
                    info_ci_outcome[1] = f.outcome_ci_p[1]
            else:
                txt_outcomes_max.append('NaN')

            if f.score_ci[0] is not None:
                txt_scores_min.append(num_err_format%(100*f.score_ci[0]))
                if info_ci_score[0] is None:
                    info_ci_score[0] = f.score_ci_p[0]
            else:
                txt_scores_min.append('NaN')
            if f.score_ci[1] is not None:
                txt_scores_max.append(num_err_format%(100*f.score_ci[1]))
                if info_ci_score[1] is None:
                    info_ci_score[1] = f.score_ci_p[1]
            else:
                txt_scores_max.append('NaN')

        
        txt_titles.append(frm)
        txt_vals.append(contrib_format%(f.contrib))
        color = 'rgba(0,0,0,0)' #neutral
        if (f.contrib > 0):
            color = 'rgba(50,171,96,0.7)'
        elif (f.contrib < 0):
            color = 'rgba(222,45,38,0.8)'
        txt_colors.append("'" + color + "'")

    if not(silence):
        print('Score CI in [%d, %d]'%(info_ci_score[0] if info_ci_score[0] is not None else 0, info_ci_score[1] if info_ci_score[1] is not None else 0))
        print('Outcome CI in [%d, %d]'%(info_ci_outcome[0] if info_ci_outcome[0] is not None else 0, info_ci_outcome[1] if info_ci_outcome[1] is not None else 0))

    if not(not_all_nan_outcome):
        txt_outcomes = []
    if not(not_all_nan_score):
        txt_scores = []
    if not(not_all_nan_counts):
        txt_counts = []
    text = text.replace('$TITLES$','%s'%(', '.join(txt_titles)))
    text = text.replace('$SHAP_VEC$','%s'%(', '.join(txt_vals)))
    text = text.replace('$COLOR_VAL$','%s'%(', '.join(txt_colors)))
    text = text.replace('$CONTRIB_ERROR_BAR_MIN$','%s'%(', '.join(txt_error_y_min)))
    text = text.replace('$CONTRIB_ERROR_BAR_MAX$','%s'%(', '.join(txt_error_y_max)))
    text = text.replace('$X_ERROR_BAR_MIN$','%s'%(', '.join(txt_error_x_min)))
    text = text.replace('$X_ERROR_BAR_MAX$','%s'%(', '.join(txt_error_x_max)))
    text = text.replace('$OUTCOMES_ARRAY$','%s'%(', '.join(txt_outcomes)))
    text = text.replace('$COUNTS_ARRAY$','%s'%(', '.join(txt_counts)))
    text = text.replace('$SCORES_ARRAY$','%s'%(', '.join(txt_scores)))

    text = text.replace('$SCORES_ARRAY_MIN$','%s'%(', '.join(txt_scores_min)))
    text = text.replace('$SCORES_ARRAY_MAX$','%s'%(', '.join(txt_scores_max)))
    text = text.replace('$OUTCOMES_ARRAY_MIN$','%s'%(', '.join(txt_outcomes_min)))
    text = text.replace('$OUTCOMES_ARRAY_MAX$','%s'%(', '.join(txt_outcomes_max)))
    fw = open(output_path, 'w')
    fw.write(text)
    fw.close()
    if not(silence):
        print('Done print report for feature %s influence to %s'%(feat_name ,output_path))
    
def format_global_importance(header, data, val_format, max_count, output_path, img_width):
    """
    """
    if not(os.path.exists(feature_glo_template_path)):
        raise NameError('File not found %s'%feature_glo_template_path)
    print('Going to print report for global feature importance to %s'%(output_path))

    # Prepare values to be placed into placeholders
    # GRAPH_TITLE, FEATURE_NAMES, SHAP_VEC

    feature_contrib = dict()
    #find "Importance" title:
    ind = None
    for i in range(len(header)):
        if header[i] == "Importance":
            ind = i
            break
    if ind is None:
        raise NameError('Can\'t find "Importance" in report title')
    ind_alias=None
    for i in range(len(header)):
        if header[i] == "Category_Alias_Lookup":
            ind_alias = i
            break
    tuples_vals = []
    for i in range(len(data)):
        full_name=clear_name(data[i][0])
        if ind_alias is not None and len(data[i][ind_alias]) > 0:
            full_name = full_name + ':' + select_alias(data[i][ind_alias])
        feature_contrib[full_name] = float(data[i][ind])
        tuples_vals.append( [full_name, float(data[i][ind])] )
    #sort by contrib in abs:
    tuples_vals = sorted(tuples_vals, key = lambda kv: abs(kv[1]), reverse = True)
    tuples_vals = tuples_vals[:max_count]

    tuples_vals = sorted(tuples_vals, key = lambda kv: abs(kv[1]), reverse = False)

    vals = []
    features = []
    for feature_name, contrib in tuples_vals:
        features.append(feature_name)
        vals.append(contrib)

    txt_vals = []
    txt_features = []
    for feature_name, contrib in zip(features,vals):
        txt_features.append("'" + feature_name + "'")
        txt_vals.append(val_format%(contrib))

    GRAPH_TITLE='Global Feature Importance'
    FEATURE_NAMES=', '.join(txt_features)
    SHAP_VEC=', '.join(txt_vals)

    # Load HTML/JS template    
    fr = open(feature_glo_template_path, 'r')
    text = fr.read()
    fr.close()

    # Replace placeholders GRAPH_TITLE, FEATURE_NAMES, SHAP_VEC
    # with their current values

    text = text.replace('$GRAPH_TITLE$','%s'%(GRAPH_TITLE))
    text = text.replace('$FEATURE_NAMES$','%s'%(FEATURE_NAMES))
    text = text.replace('$SHAP_VEC$','%s'%(SHAP_VEC))

    # Export resulting HTML into an output file
    if os.path.dirname(output_path)!= '' and not(os.path.exists(os.path.dirname(output_path))):
        print('Create directory %s'%(os.path.dirname(output_path)))
        os.makedirs(os.path.dirname(output_path))
    fw = open(output_path, 'w')
    fw.write(text)
    fw.close()
    print('Done print report for global feature importance to %s'%(output_path))

    # Export plot into a PNG image
    import plotly.graph_objects as go
    output_image_path = output_path.replace('.html','.png') 

    data = {    
        'type': 'bar',
        'y': features, 
        'x': vals,
        'text': vals,
        'textposition': 'auto', 
        'name': 'Features', 
        'orientation': 'h'
    }

    # [!!!] we use HARDCODED width, because default width becomes 700 
    #       rendering the image unreadable
    #
    # ACTION:   Fix it by somehow getting image width from HTML export 
    
    layout = {
      'title': GRAPH_TITLE,
      'yaxis': { 
        'automargin':       True, 
        'showticklabels':   True, 
        'type':             'category', 
        'dtick':1 
        }, 
      'xaxis': { 
        'title':            'Contribution', 
        'automargin':       True
        },
      'autosize': True,
      'height': 800, 
      'width': img_width, 
      'font': { 
        'size': 14 
        }
    };

    # Create the figure
    fig = go.Figure(data=data, layout=layout)

    # Save the figure as a PNG file
    try:
        fig.write_image(output_image_path)
    except:
        print('Can\'t write image')
        traceback.print_exc()

    print('Done exporting global feature importance to %s'%(output_image_path))

#output - Global feature importance or feature influence graphs
def print_multiple(header, data, val_format, contrib_format, max_count, output_path, use_median, missing_value, missing_replace, force_many_graph):
    feature_contrib = dict()
    ind = None
    for i in range(len(header)):
        if header[i] == "Importance":
            ind = i
            break
    if ind is None:
        raise NameError('Can\'t find "Importance" in report title')
    name_index=0
    if 'Representative' in header:
        name_index=name_index=header.index('Representative')
    tuples_vals = []
    for i in range(len(data)):
        feature_contrib[clear_name(data[i][name_index])] = float(data[i][ind])
        tuples_vals.append( [clear_name(data[i][name_index]), float(data[i][ind]), clear_name(data[i][0])] )
    #sort by contrib in abs:
    tuples_vals = sorted(tuples_vals, key = lambda kv: abs(kv[1]), reverse = True)
    tuples_vals = tuples_vals[:max_count]
    #use tuples_vals and create graphs:
    if not(os.path.exists(output_path)):
        os.makedirs(output_path)
    first_print=True
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    for feat_name, val, cleanest_name in tuples_vals:
        prety_name = ''.join(c for c in cleanest_name if c in valid_chars) + '.html'
        #prety_name = '%s.html'%(feat_name)
        format_feature_inf(header, data, feat_name, val_format, os.path.join(output_path, prety_name), contrib_format,
                           use_median, missing_value, missing_replace, force_many_graph, not(first_print))
        first_print = False
    
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Print nice report of feautre importance")
    parser.add_argument("--report_path",help="the input report path to analyze for nice print",required=True)
    parser.add_argument("--output_path",help="the output file path",required=True)
    parser.add_argument("--num_format",help="Number format string",default='%2.1f')
    parser.add_argument("--contrib_format",help="Number format string for contrib",default='%2.1f')
    parser.add_argument("--missing_value",help="the missing_value number in matrix",default=-65336)
    parser.add_argument("--missing_replace",help="the missing_value number to show in matrix",default=None)
    parser.add_argument("--feature_name",help="feature name for specific feature anme",default='')
    parser.add_argument("--max_count",help="the maximal count to print feature importance", type=int,default=20)
    parser.add_argument("--use_median",help="use median instead on mean", type=str2bool,default=False)
    parser.add_argument("--force_many_graph",help="force to print many graph", type=str2bool,default=False)
    parser.add_argument("--print_multiple_graphs",help="will print multiple graphs. output_path is directory", type=str2bool,default=False)
    parser.add_argument("--img_width",help="set image width when exporting global feature importance as PNG", type=int, default=1904)
    args = parser.parse_args() 
    #if given feature_name - will do : format_feature_inf. otherwise: format_global_importance
    header, data = read_feat_importance(args.report_path)
    if args.print_multiple_graphs:
        print('Print multiple report')
        print_multiple(header, data, args.num_format, args.contrib_format, args.max_count, args.output_path, args.use_median, args.missing_value, args.missing_replace, args.force_many_graph)
    else:
        if len(args.feature_name) > 0:
            format_feature_inf(header, data, args.feature_name, args.num_format, args.output_path, args.contrib_format, args.use_median, args.missing_value, args.missing_replace, args.force_many_graph, False)
        else:
            format_global_importance(header, data, args.contrib_format, args.max_count, args.output_path, args.img_width)
