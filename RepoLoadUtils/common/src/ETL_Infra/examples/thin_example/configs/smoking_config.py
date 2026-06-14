MAX_INTENSITY = 120

# ignore because rare and/or unclear
ignore =    ['137k.00', # Refusal to give smoking status
             '137I.00', # Passive smoker
             '137U.00', # Not a passive smoker
             '137E.00', # Tobacco consumption unknown
             '137D.00', # dmitted tobacco cons untrue ?
             '137W.00', # Chews tobacco
             '137i.00', # Ex-tobacco chewer
             '137g.00', # Cigarette pack-years
             '137c.00', # Thinking about stopping smoking
             '137I000', # Exposed to tobacco smoke at home
             '137h.00', # Minutes from waking to first tobacco consumption
             '137n.00', # Total time smoked'
            ]


# ex_smoker accpet only D, and 'N by mistake' (as D)
    # 'N by mistake' is N with intensity data > 0 indicating the N is wrong
    # we could look at stopdate data as well - but it seems rare if at all
ex_smoker = ['137S.00', # Ex smoker
             '1379.00', # Ex-moderate smoker (10-19/day)
             '137F.00', # Ex-smoker - amount unknown
             '1378.00', # Ex-light smoker (1-9/day)
             '137A.00', # Ex-heavy smoker (20-39/day)
             '1377.00', # Ex-trivial smoker (<1/day)
             '137K.00', # stopped smoking
             '137B.00', # Ex-very heavy smoker (40+/day)
             '137T.00', # Date ceased smoking
             '137N.00', # Ex pipe smoker
             '137O.00', # Ex cigar smoker
             '137l.00', # Ex roll-up cigarette smoker
            ]
 
# accept all smoking status
generic_smoker = ['137..00',  # Tobacco consumption - some clinics use it to report N and D, and not just Y
                 ]

# smoker accpet only Y
smoker =    ['137P.00',  # Cigarette smoker
             '137R.00',  # Current smoker
             '1372.11',  # Occasional smoker
             '1372.00',  # Trivial smoker - < 1 cig/day
             '1373.00',  # Light smoker
             '1374.00',  # Moderate smoker
             '1375.00',  # Heavy smoker - 20-39 cigs/day
             '1376.00',  # Very heavy smoker - 40+cigs/d
             '137M.00',  # Rolls own cigarettes
             '137G.00',  # Trying to give up smoking
             '137P.11',  # Smoker
             '137Z.00',  # Tobacco consumption NOS
             '137C.00',  # Keeps trying to stop smoking
             '137J.00',  # Cigar smoker
             '137H.00',  # Pipe smoker
             '137X.00',  # Cigarette consumption
             '137Y.00',  # Cigar consumption
             '137a.00',  # CPipe tobacco consumption
             '137d.00',  # Not interested in stopping smoking
             '137..11',  # Smoker - amount smoked
             '137V.00',  # Smoking reduced
             '137Q.11',  # Smoking restarted
             '137Q.00',  # Smoking started
             '137m.00',  # Failed attempt to stop smoking
             '137o.00',  # Waterpipe tobacco consumption
             '137e.00',  # Smoking restarted
             '137f.00',  # Reason for restarting smoking
             '6791.00',  # Health ed. - smoking
			 '8CAL.00',  # Smoking cessation advice
			 '13p5.00',  # Smoking cessation programme start date
			 '8IEM.00',  # Smoking cessation drug therapy declined
			 '8CA..00',  # Patient given advice
           ]

# ever_smoker accpet Y, D and 'N by mistake' (as D)
ever_smoker = ['137j.00', # Ex-cigarette smoker: not common, in practice unclear mix of Y and D
               '137K000', # Recently stopped smoking: not common, in practice unclear mix of Y, N and D
               '137b.00', # Ready to stop smoking
              ]
 
# never accept just 'clean N'
# 'clean N' is N with no additional data
never_smoker = ['1371.00', # Never smoked tobacco
               ]

# non_smoker accpet D, N, and 'N by mistake' (as D)
non_smoker = ['1371.11', # Non-smoker
              '137L.00', # Current non-smoker
             ]

# check if N has valid intensity value so he should be D 
def N2D(data, MAX_INTENS):
    df = data[data.data1=='N'].copy()
    df = df[df.data2.str.isnumeric()]
    df = df[df.data2.astype(int).between(1,MAX_INTENS)]
    df['N2D'] = True
    print('Convert ', len(df), ' N to D')
    data = data.merge(df[['pid', 'time_0', 'N2D']], on=['pid', 'time_0'], how='left')
    data.loc[data.N2D==True, 'data1'] = 'D'
    return data
