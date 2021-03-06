import numpy as np
import pandas as pd
from optmize import *
import cv2
from sklearn import metrics
from sklearn.metrics import pairwise_distances

def evaluate(membership,dataSet):
    exp = np.array(getExpResult(membership))
    index = metrics.silhouette_score(np.array(dataSet), exp, metric='euclidean')
    print index
    return index


class TS(TabuSearch):
    def start(self, U, V, J, VQue):
        _U, _V, _J = U, V, J
        curTimes = 0
        _tabuLength = 0
        epsilon = 1e-6
        lastlocationJ = _J
        while (curTimes < self.MAX_ITERATION):
            locationJ = float('inf')
            locationA = 0
            locationU = locationV = None
            neighbourhoodVs = deque([])
            judge = deque([])
            for i in xrange(self.maxSearchNum):
                neighbourV = self.circleNeighbourhoodV(V)
                neighbourhoodVs.append(neighbourV)
                judge.append(self.tabuJudge(neighbourV))
            neighbourhoodVs = np.array(neighbourhoodVs)
            judge = np.array(judge)

            if not judge.all():
                neighbourhoodVs = neighbourhoodVs[judge == False]
            for neighbourV in neighbourhoodVs:
                temU, temV, temJ, temVQue = fcmIteration(
                    U, neighbourV, self.dataSet, self.m, self.c, 1)
                temA = evaluate(temU, self.dataSet)
                # if temJ < locationJ:
                if temA > locationA:
                    locationU = temU
                    locationV = temV
                    locationJ = temJ
                    locationA = temA
                    locationVQue = temVQue

            # if locationJ < _J:
            if locationA <= accuracy:
                self.neighbourhoodTimes = max(1, self.neighbourhoodTimes - 1)
            else:
                if locationA > _accuracy:
                    _U, _V, _J, _accuracy, _VQue = locationU, locationV, locationJ, locationA, locationVQue
                self.neighbourhoodTimes = min(10, self.neighbourhoodTimes + 1)
            U, V = locationU, locationV
            if _tabuLength < self.tabuLength:
                self.addTabuObj(locationV)
                _tabuLength += 1
            else:
                self.updateList(locationV)
            # if -epsilon <= lastlocationJ - locationJ <= epsilon:
            #     break
            # else:
            #     lastlocationJ = locationJ
            curTimes += 1

        return _U, _V, _J


def convert2D(origin, shape, colNum=1):
    return origin.reshape(shape[0] * shape[1], colNum)


def convert3D(origin, shape, colNum=3):
    return origin.reshape(shape[0], shape[1], colNum)


def rangeMat(data):
    res = np.zeros((2, data.shape[1]))
    res[0] = np.max(data, axis=0)
    res[1] = np.min(data, axis=0)
    return res


def cosMat(verctor, mat):
    dot = np.sum(verctor * mat, axis=1)
    norm = np.linalg.norm(mat, axis=1) * np.linalg.norm(verctor)
    return np.float_(dot) / norm


def inv_normalization(data, rangeMat):
    data = data * (rangeMat[0] - rangeMat[1]) + rangeMat[1]
    return data


def matchByFrequency(originExp, targetExp):
    """ match by the order of the number of points within the cluster  """
    series = pd.Series(targetExp)
    targetKeys = series.value_counts().keys()
    series = pd.Series(originExp)
    originKeys = series.value_counts().keys()
    originLength = len(originKeys)
    targetLength = len(targetKeys)
    matchMap = {}
    for i in range(originLength):
        matchMap[originKeys[i]] = targetKeys[i % originLength]
    return matchMap


def stdMat(data, V, exp):
    c = V.shape[0]
    mat = np.zeros(V.shape)
    for i in range(c):
        mask = exp == i
        dataSlice = data[mask]
        mat[i, :] = np.std(dataSlice, axis=0)
    return mat


def matchByCos(origin, target, seq=None):
    """ match by the cosine similarity of (means,std) vector """
    originLen = len(origin)
    targetLen = len(target)
    targetDict = {}
    matchMap = {}
    for i in range(targetLen):
        targetDict[i] = True
    _targetDict = targetDict.copy()
    iteration = seq if seq else range(originLen)
    for i in iteration:
        keys = targetDict.keys()
        if not len(keys):
            targetDict = _targetDict.copy()
            keys = targetDict.keys()
        mat = cosMat(origin[i], target[[int(item) for item in targetDict]])
        selectIndex = np.argmax(mat)
        """ match by the Euclidean distance """
        # mat = distanceMat(
        #     origin[i].reshape(1,origin.shape[1]),
        #     target[[int(item) for item in targetDict]])
        # selectIndex = np.argmin(mat)
        matchMap[i] = int(keys[selectIndex])
        del targetDict[keys[selectIndex]]
    return matchMap


def matchByChannel(origin, target):
    """ match by the order of the color channel """
    originIndex = np.argsort(origin[:, 0])
    targetIndex = np.argsort(target[:, 0])
    originLength = len(originIndex)
    targetLength = len(targetIndex)
    matchMap = {}
    for i in range(originLength):
        ti = i if i < targetLength else targetLength - 1
        matchMap[originIndex[i]] = targetIndex[ti]
    return matchMap


def transferInRGB(originExp, originKeys, targetV, targetKeys):
    """ color transfer in RGB space instead of lab space """
    img = cv2.imread(originImagePath, 0)
    img = cv2.equalizeHist(img)
    out = convert2D(img, img.shape, 1) * np.ones(3)
    out = normalization(out) * 0.5 + 0.5
    for i in range(c):
        mask = originExp == originKeys[i]
        out[mask] = out[mask] * targetV[targetKeys[i]]
    out[:, [0, -1]] = out[:, [-1, 0]]
    return out


def data2image(data, shape, type='lab'):
    """ convert a 2-d dataSet to a image data 
    Args:
        data: 2-d dataSet, every item is the color of a pixel
        shape: the shape of the out image
        *type: the color space of the data
    Returns:
        a image mat in RGB color space
    """
    data = np.uint8(data)
    data = convert3D(data, shape, 3)
    return cv2.cvtColor(data, cv2.COLOR_LAB2RGB)


def transfer(originU, originV, originData, originRange, targetU, targetV,
             targetData, targetRange):
    c = originV.shape[0]
    targetV = inv_normalization(targetV, targetRange)
    targetData = inv_normalization(targetData, targetRange)
    originV = inv_normalization(originV, originRange)
    originData = inv_normalization(originData, originRange)

    targetExp = getExpResult(targetU)
    originExp = getExpResult(originU)
    originStd = stdMat(originData, originV, originExp)
    targetStd = stdMat(targetData, targetV, targetExp)

    # use l channel to match
    series = pd.Series(originExp)
    originKeys = series.value_counts().keys()
    # matchMap = matchByCos(originStd, targetStd, originKeys.tolist())
    # matchMap = matchByCos(
    #     np.column_stack((normalization(originV, axis=None), normalization(
    #         originStd, axis=None))),
    #     np.column_stack((normalization(targetV, axis=None), normalization(
    #         targetStd, axis=None))), originKeys.tolist())
    matchMap = matchByChannel(originV, targetV)

    # print targetV
    # use frequency to match
    # matchMap = matchByFrequency(originExp,targetExp)

    img = cv2.imread(originImagePath)
    # out = convert3D(img,img.shape,1)* np.ones(3)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    out = np.float_(convert2D(img, img.shape, 3))
    out_color = out.copy()
    for i in range(c):
        originMask = originExp == i
        targetMask = targetExp == matchMap[i]
        originSlice = out[originMask]
        originStd = np.std(originSlice, axis=0)
        originMeans = originV[i]
        targetMeans = targetV[matchMap[i]]
        out[originMask] = (
            originSlice - originMeans[0:3]
        ) * targetStd[matchMap[i]][0:3] / originStd[0:3] + targetMeans[0:3]
        out_color[originMask] = np.zeros(
            originSlice.shape) + targetV[matchMap[i]][0:3]

    # normalization
    outRange = rangeMat(out)
    outRange[outRange > 255] = 255
    outRange[outRange < 0] = 0
    out = normalization(out)
    out = inv_normalization(out, outRange)

    out = data2image(out, img.shape)
    out_color = data2image(out_color, img.shape)
    timeString = time.strftime('%Y_%m_%d-%H%M%S')
    plt.imsave('./' + timeString + '.color.png', out_color)
    plt.imsave('./' + timeString + '.transfer.png', out)


def showClustering(U, V, rangeMat, data, shape):
    """ save color segement result of the origin image """
    V = inv_normalization(V, rangeMat)
    data = inv_normalization(data, rangeMat)
    exp = getExpResult(U)
    for i in range(V.shape[0]):
        mask = exp == i
        dataSlice = data[mask]
        data[mask] = np.zeros(dataSlice.shape) + V[i]
    data = np.uint8(data[:, 0:3])
    data = convert3D(data, shape, 3)
    data = cv2.cvtColor(data, cv2.COLOR_LAB2RGB)
    plt.imsave('./' + time.strftime('%Y_%m_%d-%H%M%S') + '.clustering.png',
               data)


def loadImageData(url, meanshift=False, position=True):
    """ load data form a image

    Args:
        url: the path of the image
        meanshift: bool, whether use meanshift on the image
        position: bool, whether add position information to the dataSet
    Returns:
        a tuple(dataSet,shape) consist of image information and the image shape
        the dataSet include the color information of the image in lab color space, 
        the location(x,y) of every pixels is optional
    """
    img = cv2.imread(url)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    if meanshift:
        img = cv2.pyrMeanShiftFiltering(img, 9, 50)
    out = conv2D = np.float32(convert2D(img, img.shape, 3))
    if position:
        out = np.zeros((conv2D.shape[0], conv2D.shape[1] + 2))
        out[:, 0:-2] = conv2D
        out[:, -2] = np.repeat(range(img.shape[0]), img.shape[1])
        out[:, -1] = np.tile(range(img.shape[1]), img.shape[0])
    return out, img.shape


if __name__ == '__main__':
    originImagePath = '../images/filter/scream_200.jpg'
    targetImagePath = '../images/filter/picasso_1_200.jpg'
    start = time.clock()
    filterData, filterShape = loadImageData(targetImagePath, True, False)
    originData, originShape = loadImageData(originImagePath, True, False)
    filterRange = rangeMat(filterData)
    originRange = rangeMat(originData)
    filterData = normalization(filterData)
    originData = normalization(originData)
    c = int(5)  # number of cluster
    m = int(2)  # power of membership
    originU, originV, originJ, originVque = fcm(originData, m, c, 1)
    print evaluate(originU,originData)
    # targetU, targetV, targetJ,targetVque = fcm(filterData, m, c,1)
    # showClustering(originU, originV, originRange, originData, originShape)
    # showClustering(targetU, targetV, filterRange, filterData, filterShape)
    # transfer(originU, originV, originData, originRange, targetU, targetV,
    #          filterData, filterRange)
    # print('before origin J:{}').format(originJ)
    # print('before target J:{}').format(targetJ)
    # print time.clock() - start

    # start = time.clock()
    # filterTs = TS(MAX_ITERATION=20,
    #               extra={'dataSet': filterData,
    #                      'm': m,
    #                      'c': c})
    # targetU, targetV, targetJ = filterTs.start(targetU, targetV, targetJ, targetVque)
    # originTs = TS(MAX_ITERATION=40,
    #               extra={'dataSet': originData,
    #                      'm': m,
    #                      'c': c})
    # originU, originV, originJ = originTs.start(
    #     originU, originV, originJ, originVque)
    # print evaluate(originU,originData)
    # showClustering(originU, originV, originRange, originData, originShape)
    # showClustering(targetU, targetV, filterRange, filterData, filterShape)
    # transfer(originU, originV, originData, originRange, targetU, targetV,
    #          filterData, filterRange)
    # print('after origin J:{}').format(originJ)
    # print('after target J:{}').format(targetJ)
    print time.clock() - start
