import random, math
from numpy import histogram
from scipy import stats

def testNormal(k, stdVal = 100, loopSize = 1000):
    allSamples = []
    for lo in range(loopSize):
        vector = []
        for i in range(k):
            num = random.normalvariate(0, stdVal)
            vector.append(num)
    
        meanAvg = sum(vector) / len(vector)
        varVec = math.sqrt(sum( map( lambda x: (x-meanAvg)*(x-meanAvg) , vector) ) / len(vector))
        allSamples.append(meanAvg)
        #print('%2.3f'%meanAvg)
        #log_likeli = map( lambda x: math.pow((x-meanAvg),2) / varVec ,vector)
        #final_sum = sum(log_likeli) + math.log(math.sqrt(varVec)) #now compare to normal_dist with len(vector) elements
        #final_sum = sum(log_likeli) + math.log(math.sqrt(stdVal)) #now compare to normal_dist with len(vector) elements
        #final_sum = final_sum / k
        #allSamples.append(final_sum)
    return allSamples

def prctile(vec, p):
    if p > 1 or p < 0:
        raise NameError('wrong argument')
    s = sorted(vec, reverse = True)
    ind = p*len(vec)
    res = s[ int(ind) ]
    rest = ind - int(ind)
    additional = s[ int(ind) ]
    if int(ind) + 1 < len(vec):
        additional =  s[ int(ind) + 1 ]
    res = res * (1-rest) + additional * rest
    return res

def kld_score(v1,v2, binCnt = 50):
    min_all = min([min(v1), min(v2)])
    max_all = max([max(v1), max(v2)])
    binRange = [ min_all + (float(i)/binCnt)*(max_all - min_all)   for i in range(binCnt + 1)]
        #print(binRange)
    h1, binRange = histogram(v1, density = False, bins = binRange)
    h2, tmp = histogram(v2, density = False, bins = binRange)
    score = 0
    for i in range(len(h1)):
        if (h1[i]> 0):
            if (h2[i] > 0):
                score  = score + h1[i] * math.log(h1[i] /h2[i])
            else:
                score  = score + h1[i] * math.log(1.0 / 0.1)
    #print ('%2.3f'%score)
    return score, -score
    #return score, math.exp(-score/ (binCnt * 10))

def testStat(statName, statFunc = stats.ks_2samp, numSamples = 10000, meanVal = 10, stdVal = 1, noiseFactor = 0, loopCnt = 100):
    probVec = []
    for k in range(loopCnt):
        vector = []
        vec_ref = []
        for i in range(numSamples):
            num = random.normalvariate(meanVal, stdVal)
            num_ref = random.normalvariate(meanVal, stdVal)
            if noiseFactor > 0:
                noise = random.normalvariate(0, 1)
                num = num + noise * noiseFactor
            vector.append(num)
            vec_ref.append(num_ref)
        sz, prob = statFunc(vector, vec_ref)
        probVec.append(prob)
        #print('got %2.3f with p_value= %2.3f'%(sz, prob))
    avgVal = sum(probVec) / float(loopCnt)
    med = prctile(probVec,  0.5)
    p80 = prctile(probVec,  0.8)
    p90 = prctile(probVec,  0.9)
    p95 = prctile(probVec,  0.95)
    print('%s - Got avg=%2.3f, med=%2.3f, prctile_0.8=%2.3f, prctile_0.9=%2.3f, prcile_0.95=%2.3f'%(statName, avgVal, med, p80, p90,p95))
    return probVec


#probVec_ks = testStat('kolmagorov_smirnov',stats.ks_2samp, numSamples = 10000, noiseFactor = 0)
#probVec_mann = testStat('mannwhitneyu', stats.mannwhitneyu, numSamples = 10000 , noiseFactor = 0)
probVec_kld = testStat('kld', lambda x,y: kld_score(x,y, 100) , numSamples = 10000, noiseFactor = 0) 

"""
res = testNormal(100, 100, 1000)
avgVal = sum(res) /len(res)
stdVec = math.sqrt( sum( map( lambda x: (x-avgVal)*(x-avgVal) , res) ) / len(res))
print('val=%2.3f std=%2.3f'%(avgVal, stdVec))
"""