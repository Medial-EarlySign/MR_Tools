import numpy as np
from common import *
from Configuration import *
import random, math

def initClusters(data, factors, commonVal = None, out_file_fixed = None):
    factorGrps = [] 
    meani = list()
    stdi = list()
    cnti = list()
    if commonVal is not None and type(commonVal) == str and len(commonVal) > 0:
        commonVal = float(commonVal)
    if commonVal is None or (type(commonVal) == str and len(commonVal) == 0):
        # TODO: handle 0 as most common value
        valHist = hist(data)
        tups = sorted(valHist.items(), key = lambda kv: kv[1], reverse = True)
        tups = list(filter( lambda tp : tp[0] > 0  ,tups))
        if len(tups) == 0:
            raise NameError('data is empty or all values are <= 0')
        commonVal = tups[0][0]
    
    factorGrps = [None for i in range(len(data))]
    for i in range(len(factors)):
        meani.append( commonVal / factors[i])
        stdi.append(math.sqrt(1.0 / factors[i]))
        cnti.append(1)
    print('common value found for average - %2.3f'%commonVal)
    if out_file_fixed is not None:
        out_file_fixed.write('common value found for average - %2.3f'%commonVal)
        
    return [factorGrps, meani, stdi, cnti, commonVal]

def getRandomClusters(data, factors):
    factorGrps = [] 
    meani = list()
    stdi = list()
    cnti = list()
    do_again = True
    while do_again:
        do_again = False
        for i in range(len(data)):
            factorGrps.append (random.randrange(0,len(factors))) #random set groups
            
        for i in range(len(factors)):
            factorInds = list(filter(lambda k: factorGrps[k] == i , range(len(factorGrps))))
            if len(factorInds) == 0:
                do_again = True
                break
            factorData = list(map( lambda k: data[k] ,factorInds))
            mean_all, std_all = np.mean(factorData), np.std(factorData)
            meani.append(mean_all)  
            stdi.append(std_all)
            cnti.append(len(factorData))
    return [factorGrps, meani, stdi, cnti]

def fixFactorsMixtureGaussian(data, factors, commonVal = None, forceStd = False, out_file_fixed = None):
    cfg = Configuration()
    max_iters = 1000
    if len(factors) <= 0:
        return data
    factors = list(map(float,factors))
    #EM - calc mean, std for all data
    #mean_all, std_all = np.mean(data), np.std(data)

    #init clusters:
    factors.append(1.0) 
    #factorGrps, meani, stdi, cnti = getRandomClusters(data, factors)
    factorGrps, meani, stdi, cnti, commonVal = initClusters(data, factors, commonVal, out_file_fixed)
   
    #check which factor is more probable for current clusters params: M-step
    changes = 1
    iter = 0
    while changes > 0 and iter < max_iters:
        changes = 0
        print('status iter=%d, all_means=%s all_std=%s, all_cnts=%s'%(iter, meani, stdi, cnti))
        if out_file_fixed is not None:
            out_file_fixed.write('status iter=%d, all_means=%s all_std=%s, all_cnts=%s'%(iter, meani, stdi, cnti))
        for i in range(len(data)):
            x = data[i]
            bestScore = None
            for k in range(len(factors)):
                if cnti[k] == 0:
                    continue #empty group :)
                stdC = stdi[k]
                if stdC == 0:
                    stdC = 0.1
                    eprint('small std in factor=%2.3f cnt=%d, mean=%2.3f'%(factors[k], cnti[k], meani[k]))
                    if out_file_fixed is not None:
                        out_file_fixed.write('small std in factor=%2.3f cnt=%d, mean=%2.3f'%(factors[k], cnti[k], meani[k]))
                if forceStd:
                    stdC = 1.0 / math.sqrt(factors[k])
                z = (x - meani[k])/stdC
                currScore = z*z
                if bestScore is None or currScore < bestScore:
                    bestScore = currScore
                    bestFactor = k
            changes += (factorGrps[i] is None or factorGrps[i]!=bestFactor)
            factorGrps[i] = bestFactor
        # calc new mean, std for each cluster - E-step:
        
        for k in range(len(factors)):
            factorInds = list(filter(lambda i: factorGrps[i] == k , range(len(factorGrps))))
            if len(factorInds) == 0:
                eprint('warnning empty group found factor=%2.3f! iter=%d, meani[k]=%2.3f, stdi[k]=%2.3f, cnti[k]=%d, allMeans=%s'%(factors[k], iter, meani[k], stdi[k], cnti[k], meani))
                if out_file_fixed is not None:
                    out_file_fixed.write('warnning empty group found factor=%2.3f!! iter=%d, meani[k]=%2.3f, stdi[k]=%2.3f, cnti[k]=%d, allMeans=%s'%(factors[k],iter, meani[k], stdi[k], cnti[k], meani))
                stdi[k] = stdi[k] * 2 # get more chance
                #meani[k] = 0
                cnti[k] = 1
                continue
            factorData = list(map( lambda i: data[i] ,factorInds))
            factorData = list(filter( lambda x: x != 0, factorData)) # zeroes do not count when calculating mean and std
            previusStd = stdi[k]
            previousMean = meani[k]
            meani[k], stdi[k] = np.mean(factorData),  np.std(factorData)
            cnti[k] = len(factorData)
            if cnti[k] < 50: # small sample
                eprint('warnning small cluster factor=%2.3f. iter=%d, meani[k]=%2.3f->%2.3f, stdi[k]=%2.3f->%2.3f, cnti[k]=%d. all_means=%s'%(factors[k],iter, previousMean, meani[k], previusStd, stdi[k], cnti[k], meani))
                if out_file_fixed is not None:
                    out_file_fixed.write('warnning small cluster factor=%2.3f. iter=%d, meani[k]=%2.3f->%2.3f, stdi[k]=%2.3f->%2.3f, cnti[k]=%d. all_means=%s'%(factors[k],iter, previousMean, meani[k], previusStd, stdi[k], cnti[k], meani))
                #take other cluster std and multiply it
                #stdi[k] = bigStd / factors[k]
                stdi[k] = previusStd * 2 #increase std to get bigger group
                #meani[k] = previousMean
            if stdi[k] > 1000:
                eprint('warnning std is big in factor=%2.3f. iter=%d. stdi[k]=%2.3f, cnti[k]=%d. all_means=%s'%(factors[k],iter,  stdi[k], cnti[k], meani))
                if out_file_fixed is not None:
                    out_file_fixed.write('warnning std is big in factor=%2.3f. iter=%d. stdi[k]=%2.3f, cnti[k]=%d. all_means=%s'%(factors[k],iter,  stdi[k], cnti[k], meani))
                stdi[k] = 1000
            if forceStd and ((meani[k]/(commonVal/factors[k])) >= 10 or (meani[k]/(commonVal/factors[k])) <= 0.1):
                eprint('mean is too far.. iter=%d, factor=%2.3f, mean=%2.3f'%(iter, factors[k], meani[k]))
                if out_file_fixed is not None:
                    out_file_fixed.write('mean is too far.. iter=%d, factor=%2.3f, mean=%2.3f'%(iter, factors[k], meani[k]))
                meani[k] = commonVal/factors[k]
        iter += 1
        
    #do mathcing for factors, till now the guasian can (theoritically) be with diffrent factors matchig 
    minimalMean = None
    maxFactor = None
    minimal_mean_ind = None
    max_factor_ind = None
    max_factor_dict = set()
    for i in range(len(meani)):
        if minimalMean is None or minimalMean  > meani[i]:
            minimalMean = meani[i]
            minimal_mean_ind = i
        if maxFactor is None or factors[i] > maxFactor:
            max_factor_ind = i
            maxFactor = factors[i] #may be diffrent i that maximize
    finalMean = minimalMean*maxFactor
    max_factor_dict.add(max_factor_ind)
    #match all factors with respect to this group with (minimalMean , minimal_mean_ind) =>(, maxFactor)  
    f_matches = [None for i in range(len(factors))] 
    f_matches[minimal_mean_ind] = maxFactor
    print('reference guassians mean is %2.3f with factor %2.3f - after multiply=  %2.3F'%(meani[minimal_mean_ind], f_matches[minimal_mean_ind], finalMean))
    if out_file_fixed is not None:
        out_file_fixed.write('reference guassians mean is %2.3f with factor %2.3f - after multiply=  %2.3F'%(meani[minimal_mean_ind], f_matches[minimal_mean_ind], maxFactor*minimalMean))
    #eprint('f_matches= ', f_matches, ' meani=', meani, ' factors=', factors)
    for k in range(len(f_matches)):
        if f_matches[k] is not None:
            continue
        minDf = None
        bestInd = None
        for ind in range(len(factors)):
            if ind in max_factor_dict: # factor already choosed
                continue
            df = abs(meani[k] * factors[ind] - finalMean)
            if minDf is None or df < minDf:
                minDf = df
                bestInd = ind
                
        f_matches[k] = factors[bestInd] # the best matching factor for this k guassian is ind. dont allow bestInd again?
        print('validting matching guassians to factors. mean=%2.3f factor=%2.3f after_multiply=%2.3f with diff=%2.3f'%(meani[k], f_matches[k], meani[k]*f_matches[k], minDf))
        if out_file_fixed is not None:
            out_file_fixed.write('validting matching guassians to factors. mean=%2.3f factor=%2.3f after_multiply=%2.3f with diff=%2.3f\n'%(meani[k], f_matches[k], meani[k]*f_matches[k], minDf))
        if finalMean == 0 or minDf / finalMean >= cfg.fix_mean_threshold:
            eprint('f_matches= ', f_matches, ' iters=', iter)
            raise NameError('change in mean of more than %f%% - Error. has %2.3f%% change'%(cfg.fix_mean_threshold*100 ,100*minDf / finalMean if finalMean >0 else 0))

    #set data:
    for i in range(len(data)):
        ind = factorGrps[i] # get data point group index
        data[i] = f_matches[ind] * data[i] # multiply by group factor

    grpSizesStr = ', '.join(list(map( lambda i :  '%2.3f - %d'%(f_matches[i] ,cnti[i])  ,range(len(factors)))))
    if changes > 0:
        eprint('Didn''t converge - has %d changes in last round'%changes)
        if out_file_fixed is not None:
            out_file_fixed.write("Didn''t converge - has %d changes in last round. factor group sizes: [%s]\n"%(changes, grpSizesStr))
    else:
        print('fix factors Converged after %d iters!!'%iter)
        if out_file_fixed is not None:
            out_file_fixed.write("fix factors Converged after %d iters!! factor groups sizes: [%s]\n"%(iter, grpSizesStr))
    return data

random.seed()
if __name__ == "__main__":
    n1 = 1000
    n2 = 1500
    m1 = 13
    s1 = 2
    m2 = 130
    s2 = 20
    factor = [0.1]
    
    x1 = []
    x2 = []
    for i in range(n1):
        x1.append( random.normalvariate(m1,s1) )
    for i in range(n2):
        x2.append( random.normalvariate(m2,s2) )

    testData = x1 + x2
    fixed = fixFactorsMixtureGaussian(testData, factor, 14, False) 
    #fixed = fixFactorsMixtureGaussian(testData, factor) # without common value if n2 is effecting common value, than we will have error
    

