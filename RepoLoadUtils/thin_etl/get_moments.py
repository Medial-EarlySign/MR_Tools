MAX_SIG = 5
import numpy as np

def get_moments(orig_data):
    d = sorted(orig_data)
    n_orig = len(orig_data)
    noisy = True
    while noisy:
        if len(d) == 0:
            return {"n_orig": n_orig, "n_clean": 0}
        meani, stdi = np.mean(d), np.std(d)
        new_data = [x for x in d if x >= meani - MAX_SIG*stdi and x <= meani + MAX_SIG*stdi]
        if len(new_data) < len(d):
            d = new_data
        else:
            noisy = False
    n_clean = len(d)
    n_above = len([x for x in orig_data if x > meani + MAX_SIG*stdi])
    n_below = len([x for x in orig_data if x < meani - MAX_SIG*stdi])
    if stdi > 0.0:
        skew = sum([((x-meani)/stdi)**3 for x in d])/len(d)
    else:
        skew = 0.0    
    if len(d) > 0:
        q = np.percentile(d, np.arange(0, 100, 25))
    else:
        q = [0.0, 0.0, 0.0, 0.0]        
    v_nz = [x for x in d if x != 0.0]
    if len(v_nz) > 0:
        q_nz = np.percentile(v_nz, np.arange(0, 100, 25))
    else:
        q_nz = [0.0, 0.0, 0.0, 0.0]
    return {"n_orig": n_orig, "n_clean": n_clean, "n_orig_above": n_above, "n_orig_below": n_below, 
    "mean_clean": meani, "std_clean": stdi, "skew_clean": skew, "quartiles_clean": q, "quartiles_clean_nz": q_nz} 

def moments_to_str(moments):
    mom_list = []
    for k,v in moments.items():
        mom_list.append(k)
        try:
            iter(v)
        except TypeError:
            mom_list.append(v)
        else:
            for v_in in v:
                mom_list.append(v_in)            
    mom_str = "\t".join(map(str,mom_list))
    return mom_str
    