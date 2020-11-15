from elasticsearch import Elasticsearch
from elasticsearch import client
from elasticsearch import helpers
from datetime import datetime
from config import maps, files, query_template, pose_set
from sys import getrefcount
from util import get_within_fixed
import numpy as np
import json
import gc
import re

class SearchEngine:
    def __init__(self, index_name, wrong_log='wrong.log', sentence_log='sentence_id'):
        self.es = Elasticsearch()
        self.get_docs_num()
        # self.files = [] # 保存处理过的文件名
        self.wrong_log = wrong_log
        self.sentence_log = sentence_log
        self.sentence_id = self.read_sentence_id()
        self.maps = maps
        self.index_name = index_name

    def delete_index(self, index_name):
        self.es.indices.delete(index=index_name, ignore=[400, 404])
        print('Delete index {} succesful!'.format(index_name))

    def read_sentence_id(self):
        '''用于初始化sentence_id这个变量,其实就是读取文件中的一个数'''
        try:
            with open(self.sentence_log, 'r') as f:
                return int(f.readline().strip())
        except FileNotFoundError as e:
            # 不需要创建, 如果需要写, 自然会写
            return 0

    def write_sentence_id(self):
        # 写sentence_id文件
        with open(self.sentence_log, 'w') as f:
            f.write('{}'.format(self.sentence_id))

    def split_word_pos(self, word_poses):
        '''返回词列表, 和词性列表, 词列表为words, 词性列表为pose'''
        wrong_word = open(self.wrong_log, 'a') # 打开wrong.log文件, 准备写入内容
        words = []
        for word in word_poses:
            matchObj = re.match(r'(.+)/.+$', word)
            words.append(matchObj.group(1))
        wrong_word.close()
        return words

    def store_index(self, result):
        '''其中result是一个列表, 每一个成员是一个列表, 包括了
        "0秒之内就再次燃烧起来了。"
        "0秒","之内","就","再次","燃烧","起来","了","。"
        "0秒/t","之内/f","就/d","再次/d","燃烧/v","起来/v","了/u","。/w"
        id, id没什么用
        '''
        action = ({
                    # "_index": self.index_name,
                    "_source": {
                        # 'text': row[0], 'poses': row[1]
                        'origin': row[0],
                        'words': row[1],
                        'words_poses': row[2]
                    },
                    "_id": row[3]
                } for row in result)
        helpers.bulk(self.es, action, index=self.index_name, raise_on_error=True)
        self.write_sentence_id()
        self.get_docs_num()

    def index_file(self, file_name):
        '''处理一个文件'''
        begin_time = datetime.now()
        with open(file_name) as f:
            print("Begin read {}".format(file_name))
            result = []
            for linenum, line in enumerate(f):
                line = line.strip()
                if line == '':
                    continue
                words_poses = line.split(' ')
                try:
                    words = self.split_word_pos(words_poses) # word:['苹果','好吃'] poses:['n','adj']
                    result.append([''.join(words), words, words_poses, self.sentence_id])
                    self.sentence_id += 1
                    if self.sentence_id % 200000 == 0: # 每隔200000句清空一下这个变量
                        end_time = datetime.now()
                        self.store_index(result) # 存在es中
                        del result # 防止占用内存过大, 但内存问题似乎还是没有解决
                        gc.collect()
                        result = []
                        time_diff = end_time - begin_time
                        print("Handle {} sentence! Time Use: {}".format(self.sentence_id, time_diff))
                except:
                    continue
            self.store_index(result) # 处理剩余的结果
            del result
            gc.collect()
            time_diff = datetime.now() - begin_time
            print("Read {} over! Handle {} sentence! Time Use: {}".format(file_name, self.sentence_id, time_diff))

    def create_index(self):
        if not self.es.indices.exists(index=self.index_name):
            self.es.indices.create(index=self.index_name, ignore=[400, 404], body = self.maps)
            print('Create index {}.'.format(self.index_name))
        else:
            print('Find index {}. So don\'t create a new one.'.format(self.index_name))

    def get_query_body(self, query_str, strict=False):
        '''query_str是用户直接搜索的字符串, 返回是对es的query body'''
        keywords=set(query_str.split(' '))
        query = json.loads(json.dumps(query_template))
        should_or_must = "must" if strict else "should" # 根据是否是严格模式决定query是must还是should
        query['query']['bool']['minimum_should_match'] = 0 if strict else 1
        for keyword in keywords:
            if keyword not in pose_set: # 只是词性, 比如n是不添加到query中的
                if '/' in keyword:
                    where='words_poses'
                else:
                    where="words"
                query['query']['bool'][should_or_must].append({'match': {where: keyword}})
        return query

    def get_query_res(self, query_body, size=50):
        '''根据query_body获得es的查询结果,size是es返回的最大结果数,默认50'''
        res = self.es.search(index=self.index_name, body=query_body, size=size)
        return res['hits']['hits']

    def query_pos_filter(self, res_body, query_str, within=np.inf, fix=False):
        '''仅在开启严格模式时才会调用, 仅返回res_body中符合位置约束的结果'''
        # keywords是已经split过的列表
        keywords = query_str.split(' ')
        n=len(keywords)
        # 先得到可能的结果列表
        filter_res=[]
        for res in res_body:
            pos_list = []
            res_poses=[word_pose.split('/')[1] for word_pose in res["_source"]["words_poses"]]
            for keyword in keywords: # 找出满足约束的位置
                if keyword in pose_set:
                    pos_list.append([i for i,j in enumerate(res_poses) if j==keyword])
                elif '/' in keyword:
                    pos_list.append([i for i,j in enumerate(res["_source"]["words_poses"]) if j == keyword])
                else:
                    pos_list.append([i for i,j in enumerate(res["_source"]["words"]) if j == keyword])
            b=[0 for _ in range(n)]
            ans=[]
            def dfs(k, b,ans): # 检查位置是否满足约束
                if (k == n):
                    if not fix:
                        b.sort()
                    for i in range(n - 1):
                        if not (b[i + 1] - b[i] > 0 and b[i + 1] - b[i] <= (within + 1)):
                            return
                    ans.append(b[:])
                else:
                    for i in pos_list[k]:
                        b[k] = i
                        dfs(k + 1,b,ans)
            dfs(0, b, ans)
            if(len(ans)>0):
                filter_res.append(res)
        return filter_res

    def keyword_hit_num(self,keyword):
        '''返回一个词在index中总共出现的次数,既支持含有pose的, 又支持不含有pose的'''
        # bug:本来"minimum_should_match": 1, 在should为空的情况下, 是一个也不会返回的
        query = json.loads(json.dumps(query_template))
        query["size"] = 0
        if '/' in keyword:
            query['query']['bool']['filter'].append({'match': {'words_poses': keyword}})
        else:
            query['query']['bool']['filter'].append({'match': {'words': keyword}})
        return self.es.search(index=self.index_name, body=query)['hits']['total']['value']

    def sort_query(self,res_body,query_str,is_tf_idf=False,k=1.2,b=0.2):
        '''query_str是用户直接搜索的字符串, 返回是np数组, 是result索引的一个列表, 也返回对应score'''
        res_num=len(res_body)
        keywords = query_str.split(' ')
        # 初始化矩阵
        keywords_num=len(keywords)
        idf = np.zeros(shape=(keywords_num))
        tf = np.zeros(shape=(keywords_num, res_num)) # 其实就是右边这一项

        for i in range(keywords_num):
            hit_num_corpus = self.keyword_hit_num(keywords[i])
            if hit_num_corpus==0: # 毫无意义的关键词
                continue # 由于idf与tf初始化为0, 因此可以直接continue
            idf[i] = np.log(self.docs_num / hit_num_corpus)  # 这里可以优化, 但是向量太短了, 完全没有优化的价值
            for j in range(res_num):
                hit_num_in_doc = res_body[j]["_source"]["words"].count(keywords[i].rsplit('/')[0])
                tf[i][j] = hit_num_in_doc / (hit_num_in_doc+ k*( 1-b+b*(len(res_body[j]["_source"]["words"])/self.avgdl))) if not is_tf_idf else hit_num_in_doc/len(res_body[j]["_source"]["words"])
        tf_idf = tf * idf[:, np.newaxis]
        res_tf_idf = np.sum(tf_idf, axis=0)
        sort_res = (-res_tf_idf).argsort()
        return sort_res, np.sort(res_tf_idf)[::-1]

    def get_docs_num(self):
        '''更新docs_num和avgdl两个属性'''
        self.docs_num=self.es.count()["count"]
        query={
            "aggs": {
                "avg_size": {
                    "avg": {
                        "script": {
                            "source": "doc.words.size()"
                        }
                    }
                }
            }
        }
        self.avgdl=self.es.search(body=query,size=0)["aggregations"]["avg_size"]["value"]

    def get_filter_query_res(self, query_str, is_strict):
        query_str, within, fixed = get_within_fixed(query_str)  # 处理字符串, 得到within, fixed的信息
        query_dict = self.get_query_body(query_str, strict=is_strict)
        res_body = self.get_query_res(query_dict)  # 获得查询结果
        if is_strict:  # 如果是严格模式, 还需要过滤
            if not within:
                within = np.inf
            res_body = self.query_pos_filter(res_body, query_str, within=within, fix=fixed)
        return query_str, res_body


if __name__=='__main__':
    #%% 构建索引
    se = SearchEngine(sentence_log='sentence_id', index_name="test-index")
    se.create_index()
    for file in files:
        se.index_file(file)
    #%% 用于测试搜索结果, 是一个完整的搜索流程, 但有错误, 因此与app.py中的大致相似但不一样
    # query_str="灰尘 微粒/n 细菌/n within=3"
    # se = SearchEngine(sentence_log='sentence_id',index_name="full-index")
    # pos_search=True
    # query_str, within, fixed = get_within_fixed(query_str)
    # query_dict = se.get_query_dict(query_str, pos=pos_search)
    # res_body = se.get_query_res(query_dict)
    # if pos_search:
    #     res_body = se.query_pos_filter(res_body, query_str, within=within, fix=fixed)
    # sort_res = se.sort_query(res_body, query_str)
    # res_num = len(res_body)
    # if (res_num > 10):
    #     sort_res = sort_res[:10]
    # res_body = [res_body[i] for i in sort_res]
    # print(len(res_body))

    #%% 检测排序结果
    # query_str = "细菌/n 微粒/n 灰尘/n"
    # query_dict = my_es.get_query_dict(query_str,pos=True)
    # res_body = my_es.get_query_res(query_dict)
    # filter_res=my_es.query_pos_filter(res_body,query_str,within=2,fix=True)
    # print(len(filter_res))

    # sort_res = my_es.sort_query(res_body, query_str,method="TF-IDF")
    # print(sort_res[:10])
