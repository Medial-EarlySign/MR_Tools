from utils import  is_nan



def hier_field_to_dict(hier):
    if is_nan(hier) or not hier or hier.lower() == 'none':
        return {}
    val_list = hier.split('~')
    val_dict = {x[0].strip(): x[1].strip() for x in [y.split(':') for y in val_list]}
    return val_dict


def get_dict_item(dict1, ky):
    if not dict1:
        return '_'
    return dict1[ky].strip().replace(' ', '_')
