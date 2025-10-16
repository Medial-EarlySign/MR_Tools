import sys
#NAME:low,high
def reformat_token(s):
    res = s.split(':')
    if len(res)!= 2:
        raise Exception(f'Error got "{s}" - search ":"')
    param_name, par_rng = res
    res = par_rng.split(',')        
    if len(res)!= 2:
        raise Exception(f'Error got "{s}" "{par_rng}" - search ","')
    low, high = res
    
    return param_name + ':' + '%2.3f'%(float(low)) + ',' + '%2.3f'%(float(high)) 

def transform_from_bt_filter_to_cohrt(s):
    s=';'.join(list(map(lambda x: reformat_token(x) , s.split(';'))))
    s=s.replace(',', '-').replace(';', ',')
    
    return s

if __name__ == '__main__':
    if len(sys.argv)<2:
        raise NameError('Please provide 1 input string')
    print( transform_from_bt_filter_to_cohrt(sys.argv[1]))