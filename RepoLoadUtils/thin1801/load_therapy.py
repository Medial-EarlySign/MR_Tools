import os
import pandas as pd
import time
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, eprint, fixOS
from utils import to_float, is_nan
from load_patient import get_id2nr_map


def get_route(med_desc):
    if 'eye' in med_desc:
        return '_eyes'
    if 'ear' in med_desc:
        return '_ears'
    if 'cream' in med_desc or 'ointment' in med_desc or 'lotion' in med_desc or ' gel' in med_desc or 'emulsion' in med_desc or 'paint' in med_desc or 'paste' in med_desc:
        return '_skin'
    if 'bandage' in med_desc or 'patch' in med_desc or 'gauze' in med_desc or 'tape' in med_desc or 'dressing' in med_desc:
        return '_tape'
    if 'nasal' in med_desc:
        return '_nose'
    if 'enema' in med_desc or 'suppositories' in med_desc:
        return '_rectal'
    if 'pessaries' in med_desc or 'pessary' in med_desc:
        return '_vaginal'
    if 'spray' in med_desc or 'spr' in med_desc:
        return '_spray'
    if 'wash' in med_desc:
        return '_wash'
    if 'shampoo' in med_desc or 'soap' in med_desc or 'scalp' in med_desc or 'foam' in med_desc:
        return '_soap'
    return ''


unit_names_map = {'iu': 'unit', 'units': 'unit',  'mcg': 'microgram', 'micrograms': 'microgram',  'micrograms/ml': 'microgram/ml',
                  'mcg/g': 'microgram/g', 'micrograms/g': 'microgram/g', 'mcg/ml': 'microgram/ml', 'mgs': 'mg',
                  'iu/g': 'unit/g', 'units/ml': 'unit/ml', 'units/g': 'unit/g', 'iu/ml': 'unit/ml',
                  'gn/litre': 'g/litre', 'cmx': 'cm', 'u': 'unit', 'iu/': 'unit/'}
to_remove = ['/dose', '/vial', '/sachet', '/actuation', '/spray', '/application', '/chloroform', '/inhalation',
             '/infusion', '/metered', '/unit']


to_unknown = {'acetylcysteine': 'g/ml',
              'adalimumab': 'mg',
              'amphotericintotal': 'mg',
              'apraclonidine-eyes': '%',
              'benzalkonium': '%',
              'brimonidine-eyes': 'mg/ml',
              'calcipotriol-soap': 'microgram/g',
              'carbenoxolone': 'mg',
              'cetylpyridinium': 'mg',
              'citric acid': 'mg',
              'fluorouracil': 'mg',
              'amphotericin': 'mg',
              'atropine': 'microgram/ml',
              'brivaracetam': 'mg/ml',
              'budesonide-rectal': 'mg',
              'ceftriaxone': 'mg',
              'chloral hydrate': 'mg',
              'chloramphenicol': 'mg/ml',
              'cloxacillin': 'mg/ml',
              'emedastine-eyes': '%',
              'ephedrine': '%',
              'ergometrine': 'microgram/ml',
              'erythromycin-skin': '%',
              'etanercept': 'mg',
              'fenoterol': 'mg/ml',
              'follitropin alfa': 'unit/ml',
              'glucose': 'mg/ml',
              'glycerol': 'g/ml',
              'glycine': 'mg/ml',
              'guar gum': '%',
              'lactic acid-vaginal': '%',
              'lanreotide': 'mg',
              'levocabastine-nose': 'mg/ml',
              'lidocaine': '%',
              'minoxidil': 'mg/ml',
              'neomycin-skin': 'mg',
              'nicotine-nose': 'mg/ml',
              'piperazine': 'mg',
              'polymyxin b-eyes': 'unit/ml',
              'prednisolone-rectal': 'mg',
              'prilocaine': 'mg/ml',
              'rimexolone-eyes': '%',
              'sodium perborate-wash': 'g',
              'somatropin': 'unit',
              'timolol-eyes': 'mg/ml',
              'vitamins': 'ml',
              'voriconazole': 'mg/ml'

              }

to_split = ['alimemazine', 'amoxicillin', 'ampicillin', 'apomorphine', 'azatadine', 'azithromycin', 'benorilate',
            'benzylpenicillin', 'brompheniramine', 'carbocisteine', 'cefaclor', 'cefadroxil', 'cefalexin', 'cefixime',
            'cefradine', 'cefuroxime', 'cetirizine', 'chloroquine', 'chlorothiazide', 'chlorphenamine',
            'choline theophyllinate', 'cisapride', 'clarithromycin', 'clobazam', 'clomethiazole', 'codeine',
            'cyclizine', 'cyproheptadine', 'desloratadine', 'desmopressin-nose', 'diazoxide', 'dicycloverine',
            'diphenhydramine', 'droperidol', 'ephedrine', 'ergocalciferol', 'ethosuximide', 'exenatide',
            'ferrous fumarate', 'flucloxacillin', 'flupentixol', 'fluphenazine', 'glycopyrronium bromide',
            'griseofulvin',  'erythromycin', 'clemastine', 'hydrocortisone', 'hydrotalcite', 'hydroxyzine', 'ibuprofen',
            'ipratropium bromide', 'isoniazid', 'ketoconazole', 'ketorolac', 'ketotifen', 'lamivudine', 'levetiracetam',
            'levomepromazine', 'loratadine', 'mebendazole', 'memantine', 'mesalazine-rectal', 'metoclopramide',
            'nalidixic acid', 'nicotinamide', 'nystatin', 'octreotide', 'ondansetron', 'oxycodone', 'paliperidone',
            'papaverine', 'paracetamol', 'pethidine', 'phenoxymethylpenicillin', 'piracetam', 'pivampicillin',
            'potassium', 'progesterone', 'promazine', 'promethazine', 'pseudoephedrine', 'rifampicin', 'rufinamide',
            'selenium', 'sodium alginate', 'sodium picosulfate', 'somatropin', 'sucralfate', 'sumatriptan',
            'terfenadine', 'testosterone', 'tetracycline', 'thioridazine', 'trifluoperazine', 'trimethoprim',
            'zuclopenthixol']

to_split_percent = ['clindamycin', 'clotrimazole-skin', 'fusafungine-nose', 'hydrocortisone-rectal', 'minoxidil',
                    'potassium permanganate', 'sodium chloride']

def get_unit_dosage_map(raw_path):
    drugcodes = read_fwf('Drugcodes', raw_path)
    drugcodes['drugcode'] = drugcodes['drugcode'].astype(str)
    atc = read_fwf('ATCTerms', raw_path)
    freq = read_fwf('DrugcodeFrequency', raw_path)
    mrg = drugcodes.merge(atc, how='left', left_on='atc', right_on='ATC')
    mrg = mrg.merge(freq, how='left', on='drugcode')
    mrg['genericname'] = mrg['genericname'].str.lower()
    mrg['genericname'] = mrg['genericname'].str.replace(r"\(.*\)", "")  # remove parentheses with words in them
    mrg['genericname'] = mrg['genericname'].str.replace('%,', '% ', regex=False)
    mrg['genericname'] = mrg['genericname'].str.replace('%/', '% ', regex=False)
    mrg['genericname'] = mrg['genericname'].str.replace('%with', '% with', regex=False)
    mrg['genericname'] = mrg['genericname'].str.replace('%w/', '% w/', regex=False)
    mrg['genericname'] = mrg['genericname'].str.replace(',', '')
    mrg['genericname'] = mrg['genericname'].str.replace('/bendrofluazide', ' bendrofluazide')
    mrg['genericname'] = mrg['genericname'].str.replace('/papaverine', ' papaverine')
    mrg['genericname'] = mrg['genericname'].str.replace('/theophylline', ' theophylline')
    mrg['genericname'] = mrg['genericname'].str.replace('/aminophylline', ' aminophylline')
    mrg['genericname'] = mrg['genericname'].str.replace('/chlorpheniramine', ' chlorpheniramine')
    mrg['genericname'] = mrg['genericname'].str.replace('/cellulose', ' cellulose')
    mrg['genericname'] = mrg['genericname'].str.replace('/ephedrine', ' ephedrine')
    mrg['genericname'] = mrg['genericname'].str.replace('/polymixin', ' polymixin')
    mrg['genericname'] = mrg['genericname'].str.replace('mgwith', ' mg ')

    name_split = mrg['genericname'].str.split(' ', expand=True)
    name_split = mrg[['drugcode', 'genericname', 'atc', 'freq']].join(name_split)
    name_split.drop_duplicates(subset='drugcode', inplace=True)
    # all_terms = mrg[mrg['Term'].notnull()]['Term'].str.split(' ', expand=False)
    all_atc_terms = [x.lower() for x in atc['Term']]
    all_terms = atc[atc['Term'].notnull()]['Term'].str.split(' ', expand=False)
    all_terms = [x.lower() for term in all_terms for x in term]
    for col in range(0, 8):
        name_split[str(col) + '_atc'] = name_split[col].str.lower().isin(all_terms)
        # name_split[str(col)+'_dose'] = name_split[col].str.extract('(^\d*)')
        name_split[str(col) + '_unit'] = name_split[col].str.split('([0-9\.]+)([A-z%/]+)', expand=False)
    atc_cols = [x for x in name_split.columns if '_atc' in str(x)]
    name_split = name_split[name_split[atc_cols].any(axis=1)]
    name_split.set_index('drugcode', inplace=True)
    cond = (name_split[0].str.contains('interferon')) & ((name_split[1].str.contains('alfa')) | (name_split[1].str.contains('beta')) | (name_split[1].str.contains('gamma')))
    name_split.loc[cond, '0_unit'] = name_split[cond].apply(lambda x: [x[0] + ' ' + x[1]], axis=1)
    name_split.loc[cond, '1_unit'] = name_split[cond].apply(lambda x: [], axis=1)
    name_split.loc[cond, '1_atc'] = False
    new_row_list = []
    for gn, splt in name_split.iterrows():
        new_row = {'drugcode': gn, 'genericname': splt['genericname'], 'atc': splt['atc'], 'freq': splt['freq']}
        #print(gn, splt['genericname'])
        new_row['meds'] = []
        new_row['dose'] = []
        new_row['units'] = []
        prev_word = 'aaa'
        for st in range(0, 8):
            ucol = str(st) + '_unit'
            atc_col = str(st) + '_atc'
            if splt[atc_col]:
                curr_word = splt[ucol][0].lower()
                words_meds = prev_word + ' ' + curr_word
                if words_meds in all_atc_terms:
                    if prev_word in new_row['meds']:
                        new_row['meds'][-1] = words_meds
                    else:
                        new_row['meds'].append(words_meds)
                elif curr_word in all_atc_terms and curr_word != 'sodium' and curr_word != 'calcium':
                    new_row['meds'].append(curr_word)
                prev_word = curr_word
            if splt[ucol] and len(splt[ucol]) > 1:  # It is a dose+unit
                for u in splt[ucol]:
                    if u == '' or u == '/':
                        continue
                    for i in to_remove:
                        if u.endswith(i):
                            u = u.replace(i, '')
                    flt = to_float(u)
                    if is_nan(flt):
                        new_row['units'].append(u.strip())
                    else:
                        new_row['dose'].append(flt)
        new_row_list.append(new_row)
    new_df = pd.DataFrame(new_row_list)

    final_map_list = []
    med_fit_df = new_df[(new_df['meds'].str.len() > 0) &
                        (new_df['units'].str.len() == new_df['meds'].str.len()) &
                        (new_df['dose'].str.len() == new_df['meds'].str.len())]
    for i, dc_info in med_fit_df.iterrows():
        route = get_route(dc_info['genericname'])
        for med_ind in range(0, len(dc_info['meds'])):
            new_row = {'drugcode': dc_info['drugcode'],
                       'genericname': dc_info['genericname'],
                       'atc': dc_info['atc'],
                       'freq': dc_info['freq'],
                       'med': dc_info['meds'][med_ind]+route,
                       'dose': dc_info['dose'][med_ind],
                       'units': unit_names_map.get(dc_info['units'][med_ind], dc_info['units'][med_ind])}
            final_map_list.append(new_row)

    med_ml = new_df[(new_df['meds'].str.len() > 0) &
                    (new_df['units'].str.len() > new_df['meds'].str.len()) &
                    (new_df['dose'].str.len() > new_df['meds'].str.len())]
    for i, dc_info in med_ml.iterrows():
        skip = 0
        route = get_route(dc_info['genericname'])
        for med_ind in range(0, len(dc_info['meds'])):
            un_ind = med_ind + skip
            if dc_info['units'][0] == '3.1-':
                del dc_info['units'][0]
            #   ----- get unit and dose ----
            if '/ml' in dc_info['units'][un_ind] or dc_info['units'][un_ind] == '%':  # ie /1ml
                curr_unit = dc_info['units'][un_ind]
                curr_dose = dc_info['dose'][un_ind]
            elif dc_info['units'][un_ind].endswith('/'):  # 3
                curr_unit = dc_info['units'][un_ind] + dc_info['units'][un_ind+1]
                curr_dose = dc_info['dose'][un_ind] / dc_info['dose'][un_ind+1]
                skip += 1
            else:
                continue
            #  -----
            new_row = {'drugcode': dc_info['drugcode'],
                       'genericname': dc_info['genericname'],
                       'atc': dc_info['atc'],
                       'freq': dc_info['freq'],
                       'med': dc_info['meds'][med_ind] + route,
                       'dose': curr_dose,
                       'units': unit_names_map.get(curr_unit, curr_unit)}
            final_map_list.append(new_row)
    final_map_df = pd.DataFrame(final_map_list)
    # remove non meds entries
    non_meds = ['oil', 'food', 'oxygen']
    for nm in non_meds:
        final_map_df = final_map_df[~final_map_df['med'].str.contains(nm)]

    # Find meds with various units and set multiplier when needed
    final_map_df['multi'] = 1
    converts = [('mg', 'microgram', 1000), ('g', 'mg', 1000), ('microgram', 'nanogram', 1000),
                ('microgram/g', '%', 0.0001), ('mg/g', '%', 0.1), ('mg/ml', 'microgram/ml', 1000),
                ('g/ml', 'mg/ml', 1000), ('mg/hours', 'micrograms/hours', 1000)]
    for med, grp in final_map_df.groupby('med'):
        unts = final_map_df[final_map_df['med'] == med]['units'].unique()
        if len(unts) > 1:
            tot_recs = final_map_df[(final_map_df['med'] == med)]['freq'].sum()
            for cv in converts:
                if cv[0] in unts and cv[1] in unts:
                    final_map_df.loc[(final_map_df['med'] == med) & (final_map_df['units'] == cv[0]), 'multi'] = cv[2]
                    final_map_df.loc[(final_map_df['med'] == med) & (final_map_df['units'] == cv[0]), 'dose'] *= cv[2]
                    final_map_df.loc[(final_map_df['med'] == med) & (final_map_df['units'] == cv[0]), 'units'] = cv[1]
            if med in to_unknown.keys():
                final_map_df.loc[(final_map_df['med'] == med) & (final_map_df['units'] == to_unknown[med]), 'dose'] = 9999
                final_map_df.loc[(final_map_df['med'] == med) & (final_map_df['units'] == to_unknown[med]), 'units'] = 'unknown'
            for un in unts:
                un_recs = final_map_df[(final_map_df['med'] == med) & (final_map_df['units'] == un)]['freq'].sum()
                if (un_recs/tot_recs) <= 0.05:
                    final_map_df.loc[(final_map_df['med'] == med) & (final_map_df['units'] == un), 'dose'] = 9999
                    final_map_df.loc[(final_map_df['med'] == med) & (final_map_df['units'] == un), 'units'] = 'unknown'
            if med in to_split:
                final_map_df.loc[(final_map_df['med'] == med) & (final_map_df['units'].str.contains('/')), 'med'] = med+'_solution'
            if med in to_split_percent:
                final_map_df.loc[(final_map_df['med'] == med) & (final_map_df['units'].str.contains('%')), 'med'] = med+'_solution'
    # --- TEMP: multiply when not int (saved as short in mem ---
    for med, grp in final_map_df.groupby('med'):
        dosage_df = grp[['dose']].copy()
        dosage_df['int_dose'] = dosage_df['dose'].astype(int).astype(float)
        dosage_df['is_int'] = dosage_df['dose'] == dosage_df['int_dose']
        if ~dosage_df['is_int'].all():
            cond = (final_map_df['med'] == med) & (final_map_df['dose'] != 9999)
            final_map_df.loc[cond, 'dose'] *= 1000
            final_map_df.loc[cond, 'units'] = final_map_df[cond]['units'] + '*1000'

    return final_map_df


def get_rate_code_map(filen, path):
    full_file = os.path.join(path, filen)
    df = pd.read_csv(full_file, sep='\t', names=['col1', 'dose_code', 'daily'],
                     dtype={'col1': str, 'dose_code': str, 'daily': float})
    map1 = df.set_index('dose_code')['daily']
    return map1


def load_detailed_signal(therapy_df, detailed_map, fld, out_file):
    time1 = time.time()
    det_therapy_df = therapy_df.merge(detailed_map, how='left', on='drugcode')
    det_therapy_df = det_therapy_df[det_therapy_df['med'].notnull()]
    det_therapy_df['medialid'] = det_therapy_df['medialid'].astype(int)
    det_therapy_df['prscdate'] = det_therapy_df['prscdate'].astype(int)
    det_therapy_df['sig'] = 'Drug_detailed'
    cols = ['medialid', 'sig', 'prscdate', 'med', 'dose', 'units', 'daily']
    write_tsv(det_therapy_df[cols], fld, out_file)
    time2 = time.time()
    print('    save detailed medical file ' + str(det_therapy_df.shape[0]) + ' records in ' + str(time2 - time1))


def load_therapy():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    data_path = fixOS(cfg.raw_source_path)
    code_folder = fixOS(cfg.code_folder)
    raw_path = fixOS(cfg.doc_source_path)

    if not (os.path.exists(data_path)):
        raise NameError('config error - raw_path don''t exists')
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    if not (os.path.exists(code_folder)):
        raise NameError('config error - out_path don''t exists')

    therapy_fld = os.path.join(out_folder, 'therapy')
    dosage_rate_map = get_rate_code_map('dosage_rate', code_folder)
    detailed_map = get_unit_dosage_map(raw_path)

    stat_df = pd.DataFrame()
    id2nr = get_id2nr_map()
    in_file_names = list(filter(lambda f: f.startswith('therapy.'), os.listdir(data_path)))
    #in_file_names = ['therapy.j9953']
    eprint("about to process", len(in_file_names), "files")

    cnt = 0
    for in_file_name in in_file_names:
        cnt = cnt + 1
        pracid = in_file_name[-5:]
        out_file_name = pracid[0] + '_therapy'
        out_file_name_det = pracid[0] + '_detailed_drugs'
        print(str(cnt) + ") reading from " + in_file_name)

        stats = {'prac': pracid}
        time1 = time.time()
        thr_df = read_fwf('therapy', data_path, in_file_name)
        time2 = time.time()
        print('    load medical file ' + str(thr_df.shape[0]) + ' records in ' + str(time2 - time1))
        thr_df['combid'] = pracid + thr_df['patid']
        thr_df['medialid'] = thr_df['combid'].map(id2nr)
        stats["read"] = thr_df.shape[0]
        stats["invalid_therflag"] = thr_df[thr_df['therflag'] != 'Y'].shape[0]
        stats["unknown_id"] = thr_df[thr_df['medialid'].isnull()].shape[0]
        thr_df = thr_df[(thr_df['therflag'] == 'Y') & (thr_df['medialid'].notnull())]
        thr_df['medialid'] = thr_df['medialid'].astype(int)

        thr_df['rate'] = thr_df['doscode'].map(dosage_rate_map)
        thr_df['rate'].fillna(1, inplace=True)

        #thr_df['prscqty'] = thr_df['prscqty'].where(thr_df['prscqty'] > 0, 7)
        thr_df['daily'] = (thr_df['prscqty']/thr_df['rate']).astype(int)
        thr_df['daily'] = thr_df['daily'].where(thr_df['daily'] < 365, 365)
        thr_df['daily'] = thr_df['daily'].where(thr_df['daily'] >= 1, 7)

        thr_df_gb = thr_df[['medialid', 'drugcode', 'prscdate', 'daily']].groupby(['medialid', 'drugcode', 'prscdate'])['daily'].sum().reset_index()
        thr_df_gb['dc_drugcode'] = 'dc:' + thr_df_gb['drugcode'].astype(int).astype(str)
        thr_df_gb['drugcode'] = thr_df_gb['drugcode'].astype(int).astype(str)
        thr_df_gb['daily'] = round(thr_df_gb['daily'])
        thr_df_gb = thr_df_gb[thr_df_gb['prscdate'] >= 19000101]
        #thr_df_gb.sort_values(by=['medialid', 'prscdate'], inplace=True)
        load_detailed_signal(thr_df_gb, detailed_map, therapy_fld, out_file_name_det)
        thr_df_gb['sig'] = 'Drug'
        cols = ['medialid', 'sig', 'prscdate', 'dc_drugcode', 'daily']
        #write_tsv(thr_df_gb[cols], therapy_fld, out_file_name)
        stat_df = stat_df.append(stats, ignore_index=True)
    write_tsv(stat_df, therapy_fld, 'therapy_stats', headers=True)

    #sort all files
    files = os.listdir(therapy_fld)

    # for file in files:
    #     cols = ['medialid', 'sig', 'eventdate', 'val', 'val2']
    #     print(' reading ' + file)
    #     al_file = read_tsv(file, therapy_fld, names=cols, header=None)
    #     print(' sorting ' + file)
    #     al_file.sort_values(by=['medialid', 'eventdate'], inplace=True)
    #     print(' saving ' + file)
    #     full_file = os.path.join(therapy_fld, file)
    #     al_file[cols].to_csv(full_file, sep='\t', index=False, header=False, mode='w', line_terminator='\n')


if __name__ == '__main__':
    load_therapy()
