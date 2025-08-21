from wtforms import Form, StringField, SelectField, IntegerField, FieldList, FormField, FloatField, TextField
import pandas as pd
import os

source = 'mayo'


def save_map_file(df, mode='w'):
    cols = ['signal', 'source', 'code', 'description', 'type']
    map_file = os.path.join('data', source+'_signal_map.csv')
    print(map_file)
    header = True
    if mode == 'a':
        header = False
    df[cols].to_csv(map_file, sep='\t', index=False, header=header, mode=mode)


def append_to_map_file(df):
    save_map_file(df, mode='a')


def get_mapped():
    map_file = os.path.join('data', source + '_signal_map.csv')
    if os.path.exists(map_file):
        return pd.read_csv(map_file, sep='\t')
    else:
        return pd.DataFrame(columns=['code', 'signal'])


def get_units_transforms(signal=None):
    units_trans_file = os.path.join('data', source + '_unitTranslator.txt')
    if os.path.exists(units_trans_file):
        all_map = pd.read_csv(units_trans_file, sep='\t')
        all_map['unit'] = all_map['unit'].fillna('NaN')
        if signal:
            return all_map[all_map['signal'] == signal]
        return all_map
    else:
        return pd.DataFrame(columns=['signal', 'unit', 'muliplier',	'addition',	'round', 'final_round'])


def save_unit_tranform(df):
    units_trans_file = os.path.join('data', source + '_unitTranslator.txt')
    df[['signal', 'unit', 'muliplier',	'addition',	'round', 'final_round']].to_csv(units_trans_file, sep='\t', index=False)


def read_medial_signal():
    medial_labs_path = os.path.join('../', 'common_knowledge', 'medial_signals.txt')
    md_labs = pd.read_csv(medial_labs_path, sep='\t')
    return md_labs


def get_signal_unit(sig):
    sigs = read_medial_signal()
    return sigs[sigs['Name'] == sig].iloc[0]['FinalUnit']


def parse_request_dict(request_dict, key_prefix):
    req_dict = {}
    cur_dict = {k: v for k, v in request_dict.items() if k.startswith(key_prefix)}
    for k, v in cur_dict.items():
        key_split = k.split('-')
        if len(key_split) < 2:
            continue
        if key_split[1] in req_dict.keys():
            req_dict[key_split[1]][key_split[2]] = v
        else:
            req_dict[key_split[1]] = {key_split[2]: v}
    map_df = pd.DataFrame.from_dict(req_dict, orient='index')
    return map_df


def map_signal_post(request_dict):
    mapped = get_mapped()
    map_df = parse_request_dict(request_dict, 'labs_members')
    print(map_df)
    if request_dict['signal'] != 'Select':
        signal = request_dict['signal']
        map_df['signal'] = signal
        map_df['source'] = stage_def.TABLE
        map_df['type'] = 'numeric'
        map_df.rename(columns={'desc': 'description'}, inplace=True)
        mapped = mapped.append(map_df, sort=False)
        mapped.drop_duplicates(subset=['code', 'description', 'signal', 'source', 'type'], inplace=True)
        save_map_file(mapped)
    return signal


def map_units_post(request_dict):
    unit_tran = get_units_transforms()
    map_df = parse_request_dict(request_dict, 'units_members')
    print(map_df)
    map_df['signal'] = request_dict['signal']
    unit_tran = unit_tran.append(map_df, sort=False)
    unit_tran.drop_duplicates(subset=['signal', 'unit'], inplace=True, keep='last')
    save_unit_tranform(unit_tran)
    return map_df.set_index('unit')


class MemberForm(Form):
    code = StringField('code', render_kw={'readonly': True})
    desc = StringField('desc', render_kw={'readonly': True})
    count = IntegerField('count', render_kw={'readonly': True})


class TeamForm(Form):
    title = StringField('Labs')
    sigs = read_medial_signal()
    sig_choice = [(s, s) for s in sigs['Name'].values]
    sig_choice = [('Select', 'Select')] + sig_choice
    signal = SelectField('Select Signal', choices=sig_choice, default='Select')
    unit = StringField('unit')
    labs_members = FieldList(FormField(MemberForm))


class UnitsForm(Form):
    signal = StringField('signal', render_kw={'readonly': True})
    unit = StringField('unit', render_kw={'readonly': True})
    count = StringField('count', render_kw={'readonly': True})
    mean = StringField('mean', render_kw={'readonly': True})
    median = StringField('median', render_kw={'readonly': True})
    std = StringField('std', render_kw={'readonly': True})
    min = StringField('min', render_kw={'readonly': True})
    max = StringField('max', render_kw={'readonly': True})
    muliplier = FloatField('muliplier')
    addition = FloatField('addition')
    round = FloatField('round')
    final_round = FloatField('final_round')


class UnitsTeamForm(Form):
    title = StringField('Units')
    units_members = FieldList(FormField(UnitsForm))


class SourceForm(Form):
    sorce_choices = [('mayo', 'mayo'), ('kpnw', 'kpnw')]
    source = SelectField('Select Signal', choices=sorce_choices, default='mayo')

