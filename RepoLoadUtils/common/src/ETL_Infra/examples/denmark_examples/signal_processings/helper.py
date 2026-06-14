def conv_date(ss):
    mm_conv={ 'jan':1, 'feb':2, 'mar':3, 'apr':4, 'may':5, 'jun':6, 'jul':7, 'aug':8, 'sep':9, 'oct':10, 'nov':11, 'dec': 12 }
    day=int(ss[:2])
    month=ss[2:5].lower()
    year=int(ss[5:])
    month = mm_conv[month]
    return year*10000+ month*100+ day

