
def hist(vector):
    d = dict()
    for v in vector:
        if d.get(v) is None:
            d[v] = 0
        d[v] = d[v] + 1
    return d

def histRange(vector, binsRange):
    #binSelection
    d = [0] * (len(binsRange))
    for v in vector:
        binInd = binarySearch(binsRange, v)
        is_middle = binInd - int(binInd) >= 0.1
        if is_middle:
            binInd = int(binInd) + 1
        if binInd >= len(d):
            if binInd >  len(d):
                print('Got %d and has %d elements'%(binInd, len(d)))
            binInd = len(d) -1
        #print('%d\n'%int(binInd))
        d[int(binInd)] += 1
    return d

def roundRange(vector, binsRange):
    #binSelection
    for i in range(len(vector)):
        binInd = binarySearch(binsRange, vector[i])
        is_middle = binInd - int(binInd) >= 0.1
        if is_middle:
            binInd = int(binInd)
        vector[i] = binsRange[binInd]
        if is_middle and binInd + 1 < len(binsRange):
            vector[i] += binsRange[binInd+1]
            vector[i] /= 2
    return vector

def binarySearch(alist, item):
    first = 0
    last = len(alist)-1
    found = None
	
    while first<=last and found is None:
        midpoint = int(round((first + last)/2))
        if alist[midpoint] == item:
            found = midpoint
        else:    
            if item < alist[midpoint]:
                last = midpoint-1    
                if last < first:
                    found = first - 0.5
            else:
                first = midpoint+1
                if last < first:
                    found = last + 0.5

    return found

def binSelection(vec, binCnt = 50):
    if len(vec) == 0 :
        raise NameError('empty array')
    if binCnt < 2:
        raise NameError('binCnt >=2')
    """
    svec = sorted(vec)
    min_val = svec[0]
    max_val = svec[len(vec)-1]
    if len(vec) > 100:
        min_val = svec[ int(len(vec) * 0.01) ]
        max_val = svec[ int((len(vec)-1) * 0.99) ]
    """
    maxIters = 1000
    searchRange = 1
    bin_size = (len(vec) / float(binCnt))
    hist_vals = hist(vec)
    s_vals = sorted(hist_vals.items(), key=lambda kv : kv[0])
    if binCnt >= len(s_vals):
        return [s_vals[i][0] for i in range(len(s_vals))]
    #print (s_vals)
    cum_sum_ind = [0]
    totVal = 0
    for i in range(len(s_vals)):
        totVal += s_vals[i][1]
        cum_sum_ind.append(totVal)
    #print (cum_sum_ind)
    binPoses = [ round(binarySearch( cum_sum_ind, round((i+1) * bin_size))+0.1) for i in range(binCnt-1)]
    #print (binPoses)
    for i in range(1,len(binPoses)):
        if binPoses[i] == binPoses[i-1]:
            #print('here')
            if binPoses[i] <= len(s_vals) - i:
                ind = i
                while ind < len(binPoses) and binPoses[ind] <= binPoses[ind - 1]:
                    binPoses[ind] += 1
                    ind += 1
            else:
                #print('there')
                ind = i-1
                while ind >= 0 and binPoses[ind] >= binPoses[ind + 1]:
                    binPoses[ind] -= 1
                    ind -= 1
        
    #print (binPoses)
    it = 0
    changed = True
    currScore = 0
    ind = 0
    avgVec = []
    cntVec = []
    for i in range(len(binPoses)):
        binInd = binPoses[i]
        is_middle = binInd - int(binInd) >= 0.1
        binSum = 0
        binSize = 0
        while ind < len(s_vals) and ind < binInd:
            binSum += s_vals[ind][0] * s_vals[ind][1]
            binSize += s_vals[ind][1]
            ind += 1
        #if is_middle and ind + 1 < len(s_vals):
        #    binSize += s_vals[ind+1][1] / 2
        #    binSum += s_vals[ind][0] * s_vals[ind][1] / 2
        if binSize == 0 :
            print(binPoses)
            raise ZeroDivisionError('binSize is zero')
        avgVec.append(binSum / binSize)
        cntVec.append(binSize)
        currScore +=  binSize * (avgVec[i]*avgVec[i])
    binSum = 0
    binSize = 0
    while ind < len(s_vals):
        binSum += s_vals[ind][0] * s_vals[ind][1]
        binSize += s_vals[ind][1]
        ind += 1
    avgVec.append(binSum / binSize)
    cntVec.append(binSize)
    currScore +=  binSize * (avgVec[len(avgVec)-1]*avgVec[len(avgVec)-1])
        
    #print(currScore)
    #print(cntVec)
    while it < maxIters and changed:
        changed = False
        #check bin splitting movement of each bin
        maxScore = None
        best_diff = None
        best_bin_ind = None
        for i in range(len(binPoses)):
            binInd = binPoses[i]
            prevInd = int(binPoses[i-1]) if i>0 else 0
            nextInd = int(binPoses[i+1]) if i+1<len(binPoses) else len(s_vals)
            is_middle = binInd - int(binInd) >= 0.1
            diffJump = 0.5 + int(not(is_middle)) * 0.5 + (searchRange-1)
            #print(diffJump)
            itCnt = 2*searchRange + 1
            for df_i in range(itCnt):
                df = (df_i-searchRange) * diffJump
                newIndTest = int(df + binInd)
                if newIndTest < 0 or newIndTest >= len(s_vals) or (i > 0 and newIndTest <=  binPoses[i-1]) or (i < len(binPoses)-1 and newIndTest >=  binPoses[i+1]):
                    continue #out of range
                newScore = currScore
                #remove old binScore and add newBinScore
                #print('here')
                newScore -= (avgVec[i]*avgVec[i] * cntVec[i])
                newScore -= (avgVec[i+1]*avgVec[i+1] * cntVec[i+1]) # remove next partition score
                binSum = 0
                binSize = 0
                for k in range(prevInd, newIndTest):
                    binSum += s_vals[k][0] * s_vals[k][1]
                    binSize += s_vals[k][1]
                if binSize == 0:
                    continue
                newScore += binSum * (binSum / binSize)
                binSum = 0
                binSize = 0
                for k in range(newIndTest, nextInd):
                    binSum += s_vals[k][0] * s_vals[k][1]
                    binSize += s_vals[k][1]
                if binSize == 0:
                    continue
                newScore += binSum * (binSum / binSize)
                #print('old_score = %f new_score=%f  [prev=%d, curr=%d, next=%d]'%(currScore, newScore, prevInd, newIndTest, nextInd))
                if maxScore is None or newScore > maxScore:
                    maxScore = newScore
                    best_diff = df
                    best_bin_ind = i
                
        #check best score:
        changed =  maxScore > currScore
        if changed: #update state: currScore, avgVec, cntVec, binPoses
            #print('Change')
            currScore = maxScore
            prevInd = int(binPoses[best_bin_ind-1]) if best_bin_ind>0 else 0
            nextInd = int(binPoses[best_bin_ind+1]) if best_bin_ind+1<len(binPoses) else len(s_vals)
            newIndTest = int(best_diff + binPoses[best_bin_ind])
            binSum = 0
            binSize = 0
            for k in range(prevInd, newIndTest):
                binSum += s_vals[k][0] * s_vals[k][1]
                binSize += s_vals[k][1]
            avgVec[best_bin_ind] = binSum / binSize
            cntVec[best_bin_ind] = binSize
            binSum = 0
            binSize = 0
            for k in range(newIndTest, nextInd):
                binSum += s_vals[k][0] * s_vals[k][1]
                binSize += s_vals[k][1]
            avgVec[best_bin_ind + 1] = binSum / binSize
            cntVec[best_bin_ind + 1] = binSize
            binPoses[best_bin_ind] = newIndTest
            
        it += 1
    #print(binPoses)
    res  = list(map( lambda x: s_vals[int(x)][0] , binPoses))
    res.insert(0,0)
    res.append(s_vals[len(s_vals)-1][0])
    return res

#vec=  [1,1,1,1,1,   2,2,2, 3,3,3,3,3,3,3, 40,40,40,40,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,50,600,600,600,600,600,600,7000,7000,7000,8000,9000 ]
#res = binSelection(vec,2)
#print(res)