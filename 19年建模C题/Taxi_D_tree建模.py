# -*- coding: utf-8 -*-
"""
Created on Thu Sep 12 22:27:36 2019
@author: Maibenben
"""

import numpy as np
import pandas as pd
from collections import Counter


class Node(object):
    def __init__(self, x=None, label=None, y=None, data=None):
        self.label = label   # label:子节点分类依据的特征
        self.x = x           # x:特征
        self.child = []      # child:子节点
        self.y = y           # y:类标记（叶节点才有）
        self.data = data     # data:包含数据（叶节点才有）

    def append(self, node):  # 添加子节点
        self.child.append(node)

    def predict(self, features):  # 预测数据所述类
        if self.y is not None:
            return self.y
        for c in self.child:
            if c.x == features[self.label]:
                return c.predict(features)


def printnode(node, depth=0):  # 打印树所有节点
    if node.label is None:
        print(depth, (node.label, node.x, node.y, len(node.data)))
    else:
        print(depth, (node.label, node.x))
        for c in node.child:
            printnode(c, depth+1)


class DTreeID3(object):
    def __init__(self, epsilon=0, alpha=0):
        # 信息增益阈值
        self.epsilon = epsilon
        self.alpha = alpha
        self.tree = Node()

    # 求概率
    def prob(self, datasets):
        datalen = len(datasets)
        labelx = set(datasets)
        p = {l: 0 for l in labelx}
        for d in datasets:
            p[d] += 1
        for i in p.items():
            p[i[0]] /= datalen
        return p

    # 求数据集的熵
    def calc_ent(self, datasets):
        p = self.prob(datasets)
        value = list(p.values())
        return -np.sum(np.multiply(value, np.log2(value)))

    # 求条件熵
    def cond_ent(self, datasets, col):
        labelx = set(datasets.iloc[col])
        p = {x: [] for x in labelx}
        for i, d in enumerate(datasets.iloc[-1]):
            p[datasets.iloc[col][i]].append(d)
        return sum([self.prob(datasets.iloc[col])[k] * self.calc_ent(p[k]) for k in p.keys()])

    # 求信息增益
    def info_gain_train(self, datasets, datalabels):
        datasets = datasets.T
        ent = self.calc_ent(datasets.iloc[-1])
        gainmax = {}
        for i in range(len(datasets) - 1):
            cond = self.cond_ent(datasets, i)
            gainmax[ent - cond] = i
        m = max(gainmax.keys())
        return gainmax[m], m

    def train(self, datasets, node):
        labely = datasets.columns[-1]
        # 判断样本是否为同一类输出Di，如果是则返回单节点树T。标记类别为Di
        if len(datasets[labely].value_counts()) == 1:
            node.data = datasets[labely]
            node.y = datasets[labely][0]
            return
        # 判断特征是否为空，如果是则返回单节点树T，标记类别为样本中输出类别D实例数最多的类别
        if len(datasets.columns[:-1]) == 0:
            node.data = datasets[labely]
            node.y = datasets[labely].value_counts().index[0]
            return
        # 计算A中的各个特征（一共n个）对输出D的信息增益，选择信息增益最大的特征Ag。
        gainmaxi, gainmax = self.info_gain_train(datasets, datasets.columns)
        # 如果Ag的信息增益小于阈值ε，则返回单节点树T，标记类别为样本中输出类别D实例数最多的类别。
        if gainmax <= self.epsilon:
            node.data = datasets[labely]
            node.y = datasets[labely].value_counts().index[0]
            return
        # 按特征Ag的不同取值Agi将对应的样本输出D分成不同的类别Di。每个类别产生一个子节点。对应特征值为Agi。返回增加了节点的数T。
        vc = datasets[datasets.columns[gainmaxi]].value_counts()
        for Di in vc.index:
            node.label = gainmaxi
            child = Node(Di)
            node.append(child)
            new_datasets = pd.DataFrame([list(i) for i in datasets.values if i[gainmaxi]==Di], columns=datasets.columns)
            self.train(new_datasets, child)

    #训练数据
    def fit(self, datasets):
        self.train(datasets, self.tree)

    # 找到所有节点
    def findleaf(self, node, leaf):
        for t in node.child:
            if t.y is not None:
                leaf.append(t.data)
            else:
                for c in node.child:
                    self.findleaf(c, leaf)

    def findfather(self, node, errormin):
        if node.label is not None:
            cy = [c.y for c in node.child]
            if None not in cy:  # 全是叶节点
                childdata = []
                for c in node.child:
                    for d in list(c.data):
                        childdata.append(d)
                childcounter = Counter(childdata)

                old_child = node.child  # 剪枝前先拷贝一下
                old_label = node.label
                old_y = node.y
                old_data = node.data

                node.label = None  # 剪枝
                node.y = childcounter.most_common(1)[0][0]
                node.data = childdata

                error = self.c_error()
                if error <= errormin:  # 剪枝前后损失比较
                    errormin = error
                    return 1
                else:
                    node.child = old_child  # 剪枝效果不好，则复原
                    node.label = old_label
                    node.y = old_y
                    node.data = old_data
            else:
                re = 0
                i = 0
                while i < len(node.child):
                    if_re = self.findfather(node.child[i], errormin)  # 若剪过枝，则其父节点要重新检测
                    if if_re == 1:
                        re = 1
                    elif if_re == 2:
                        i -= 1
                    i += 1
                if re:
                    return 2
        return 0

    def c_error(self):  # 求C(T)
        leaf = []
        self.findleaf(self.tree, leaf)
        leafnum = [len(l) for l in leaf]
        ent = [self.calc_ent(l) for l in leaf]
        print("Ent:", ent)
        error = self.alpha*len(leafnum)
        for l, e in zip(leafnum, ent):
            error += l*e
        print("C(T):", error)
        return error

    def cut(self, alpha=0):  # 剪枝
        if alpha:
            self.alpha = alpha
        errormin = self.c_error()
        self.findfather(self.tree, errormin)


if __name__ == "__main__":
    # 计算是否上网课的满意度
    datasets = np.array([
        ['0', '0', '0', '0', '0', '0'],
        ['0', '0', '1', '1', '1', '1'],
        ['0', '0', '1', '0', '0', '0'],
        ['0', '0', '2', '1', '2', '2'],
        ['0', '0', '2', '0', '1', '1'],
        ['0', '1', '2', '1', '2', '2'],
        ['0', '1', '0', '0', '1', '0'],
        ['0', '1', '0', '1', '1', '1'],
        ['0', '1', '1', '0', '1', '1'],
        ['0', '1', '1', '1', '2', '2'],
        ['0', '2', '0', '0', '1', '1'],
        ['0', '2', '0', '1', '1', '2'],
        ['0', '2', '1', '0', '0', '0'],
        ['0', '2', '1', '1', '2', '2'],
        ['0', '2', '2', '1', '1', '2'],
        ['0', '3', '0', '0', '1', '1'],
        ['0', '3', '0', '1', '2', '2'],
        ['0', '3', '1', '0', '1', '1'],
        ['0', '3', '1', '1', '2', '2'],
        ['0', '3', '2', '1', '1', '2'],
        ['1', '0', '0', '1', '0', '0'],
        ['1', '0', '1', '1', '1', '1'],
        ['1', '0', '2', '1', '1', '1'],
        ['1', '1', '0', '1', '1', '1'],
        ['1', '1', '0', '0', '0', '0'],
        ['1', '1', '2', '1', '1', '1'],
        ['1', '2', '1', '0', '0', '1'],
        ['1', '2', '1', '1', '1', '2'],
        ['1', '2', '2', '1', '2', '2'],
        ['1', '2', '2', '1', '1', '2'],
        ['1', '3', '1', '1', '1', '2'],
        ['1', '3', '2', '1', '1', '2'],
        ['1', '3', '2', '0', '0', '0']])   # 在原始数据上多加了最后这行数据，以便体现剪枝效果

    """
    No.1：居住地：村镇：0； 城市：1；
    No.2：年级：大一：0； 大二：1； 大三：2； 大四：3；
    No.3：上课工具：手机：0； 电脑：1； Ipad：2；
    No.4：无线网络：否：0； 是：1；
    No.5：上课氛围：较差：0； 一般：1； 融洽：2；
    Prediction：满意度：0：不满意； 1：较满意； 2：满意；
    """

    datalabels = np.array(['居住地', '年级', '上课工具', '无线网络', '上课氛围', '满意度'])
    train_data = pd.DataFrame(datasets, columns=datalabels)
    # 输入测试数据
    test_data = ['1', '1', '1', '1', '1']

    dt = DTreeID3(epsilon=0)  # 可修改epsilon查看预剪枝效果
    dt.fit(train_data)

    y = dt.tree.predict(test_data)
    if int(y) == 0:
        print('结果：不满意')
    elif int(y) == 1:
        print('结果：较满意')
    elif int(y) == 2:
        print('结果：满意')


    """
    dt.cut(alpha=0.5)  #可修改正则化参数alpha查看后剪枝效果

    print('DTree:')
    printnode(dt.tree)
    y = dt.tree.predict(test_data)
    print('结果,是否回市区拉人：', y)
    """






