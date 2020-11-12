import numpy as np
import re

def get_pos_explain(explanation_file='pos_explaination.txt'):
    pos2chin = {} # 目标字典, 希望得到'n:名词'这种
    pos_list = [] # 这是词性列表, 比如'n'等
    pos2show = {} # 这个字典, 大概是词性:True, 比如'n:True'
    with open(explanation_file, 'r') as f:
        for linenum, line in enumerate(f):
            line = line.strip()
            if line == '':
                continue
            line_content = line.split(' ')
            for item in line_content:
                matchObj = re.match(r'(.+)/(.+)$', item)
                pos2chin[matchObj.group(1)] = matchObj.group(2)
                pos_list.append(matchObj.group(1))
    for key in pos2chin:
        pos2show[key] = True
    return pos2chin, pos2show, pos_list



def check_index(words, poses, i, poses_set): # words这个不是多余的么?
    return poses[i] in poses_set

def getSortKey(elem):
    return elem['tf']

def cal_tf(show_list, avgl, k=1.2, b=0.75):
    # 这是在计算tf吧, avgl调用的时候是windowsize
    for item in show_list:
        item['tf'] = item['termFreq'] * (k + 1) / (item['termFreq'] + k * (1 - b + b * item['dis'] / avgl))


def count_words(results, keywords_list, windowsize=5, poses_set=set(['w'])):
    '''这个函数最为重要,它关系到不同句子的排序'''
    show_list = []
    # 下面几个字典, 猜测它们的key都是词
    words_freq = {} # 是每一个词在所有结果中的出现次数? 但是也需要每一个词, 在每一个句子的次数吧
    words_dis = {} # 表示其它词与这个词的间隔距离(在除去stop word之后)
    words_pos = {} # 词性
    key_words_set = set(keywords_list[0]) # 为什么要在列表外面再套一层列表?
    for k in range(len(results)): # 什么情况下, 长度会>1, 也就是会有多于一个列表
        result = results[k]
        keywords = keywords_list[k]
        for items in result:
            # 这是在对结果中的每一句话处理
            origin_words = items['_source']['text'] # 有哪些词
            origin_poses = items['_source']['poses'] # 词性是什么
            for key in keywords:
                index_key = origin_words.index(key) # 它是出现在这句话的第几个词
                start = max(0, index_key - windowsize) # 窗的左边, 这样index_key左边(不包括它自己)取了windowsize个词
                end = min(len(origin_words), index_key + windowsize + 1) # 在index_key左边(不包括它自己)取了windowsize个词, +1是因为不取等, 猜测这个词本身不会显示
                ans_list = filter(lambda x: origin_poses[x] in poses_set, range(start, end)) # 这是在筛选词性, 用户不是选择了一次词性么, 必须得是这个子集, 否则不显示. 但我感觉逻辑不太对, 这么说, 筛选前有2*窗宽个, 但是筛选后可能达不到窗宽需要的数目
                for i in ans_list: # i是在origin_words中的索引
                    if origin_words[i] not in key_words_set and i != index_key: # 这是在要求这个词本身不能是关键词
                        if origin_words[i] not in words_freq: # 为什么只看是不是words_freq, 这3个字典是一体的, 它们的key完全相同
                            words_freq[origin_words[i]] = 0
                            words_dis[origin_words[i]] = []
                            words_pos[origin_words[i]] = origin_poses[i] # 也就是这句话的词性表['m', 'q', 'n', 'x', 'n'
                        words_freq[origin_words[i]] += 1
                        words_dis[origin_words[i]].append(abs(index_key - i)) # 这个词距目标关键词的距离, 似乎已经去掉了停词再计算的
    for word, cnt in words_freq.items():
        show_list.append({'words': word, 'termFreq': cnt, 'dis': np.mean(words_dis[word]), 'pos': words_pos[word]})
    cal_tf(show_list, windowsize)
    show_list.sort(key=getSortKey, reverse=True)
    return show_list
