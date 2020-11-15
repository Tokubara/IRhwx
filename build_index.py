from elasticsearch import Elasticsearch
from elasticsearch import client
from elasticsearch import helpers
from datetime import datetime
from config import maps, files_to_handle, query_template, pose_set
from sys import getrefcount
from util import get_within_fixed
import numpy as np
import json
import gc
import re

class SearchEngine:
    def __init__(self, wrong_log='wrong.log', sentence_log='sentence_id', index_name='test-index'):
        self.es = Elasticsearch()
        self.get_docs_num()
        # self.files = [] # 保存处理过的文件名
        self.wrong_log = wrong_log
        self.sentence_log = sentence_log
        self.sentence_id = self.read_sentence_id()
        self.maps = maps
        self.index_name = index_name
        # self.stop_words = self.read_stop_words() #  不需要stopword

    # def read_stop_words(self):
    #     #     stop_words = set()
    #     #     try:
    #     #         with open('stop_words.txt', 'r') as f:
    #     #             for linenum, line in enumerate(f):
    #     #                 line = line.strip()
    #     #                 if line == '':
    #     #                     continue
    #     #                 stop_words.add(line)
    #     #     except FileNotFoundError as e:
    #     #         print("Can't find stop words dictionary!")
    #     #     return stop_words

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
        # poses = []
        for word in word_poses:
            matchObj = re.match(r'(.+)/.+$', word)
            # try:
                # if matchObj.group(1) in self.stop_words:
                #     continue
            words.append(matchObj.group(1))
                # poses.append(matchObj.group(2))
            # except:
            #     wrong_word.write('{}\t{}\n'.format(self.sentence_id, word)) # 会给出是哪一个句子遇到了问题,
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

    def index_file(self, file_name):
        '''处理一个文件'''
        begin_time = datetime.now()
        with open(file_name) as f:
            print("Begin read {}".format(file_name))
            result = []
            for linenum, line in enumerate(f):
                line = line.strip() # 从后面推测来看, line应该长这样"苹果/n 好吃/adj", 而且一个line猜测是对应一条新闻的
                if line == '':
                    continue
                words_poses = line.split(' ')
                try:
                    words = self.split_word_pos(words_poses) # word:['苹果','好吃'] poses:['n','adj']
                    result.append([''.join(words), words, words_poses, self.sentence_id]) # 把一条新闻的结果添加进去
                    self.sentence_id += 1
                    if self.sentence_id % 200000 == 0: # 每隔200000句清空一下这个变量
                        end_time = datetime.now()
                        self.store_index(result) # 把这则数据存在es中
                        del result # 删除一下这个局部变量, 因为它已经存了, 用不到它了
                        gc.collect() # 但从文章来看, 我总怀疑是多余的, 我怀疑del已经可以了
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
            # sel


    def create_index(self):
        if not self.es.indices.exists(index=self.index_name):
            self.es.indices.create(index=self.index_name, ignore=[400, 404], body = self.maps)
            print('Create index {}.'.format(self.index_name))
        else:
            print('Find index {}. So don\'t create a new one.'.format(self.index_name))
        # for file_name in self.files:
        #     self.read_source(file_name)
        # print("Total sentence number is {}!".format(self.sentence_id))

    def get_query_dict(self, query_str, pos=False):
        '''query_str是用户直接搜索的字符串, 返回是字典'''
        # TODO 把者共函数改为私有函数
        keywords=set(query_str.split(' '))
        query = json.loads(json.dumps(query_template))
        # 没有词性约束
        if not pos:
            query['query']['bool']['minimum_should_match'] = 1
            for keyword in keywords:
                if('/' in keyword):
                    query['query']['bool']['should'].append({'match': {'words_poses' : keyword}})
                else:
                    query['query']['bool']['should'].append({'match': {'words': keyword}})
        else:
            for keyword in keywords:
                if ('/' in keyword):
                    query['query']['bool']['must'].append({'match': {'words_poses': keyword}})
                else:
                    query['query']['bool']['must'].append({'match': {'words': keyword}})
        return query
        #     query['query']['bool']['must'].append({'filter': {'text' : keyword}})

    def get_query_res(self, query_dict, size=50):
        '''pos表示打开了位置约束, within表示最多可以间隔的, 比如within=0表示必须紧挨着, fix表示顺序必须是关键词出现的顺序'''
        res = self.es.search(index=self.index_name, body=query_dict, size=size)
        # assert res['hits']['total']['value']==len(res['hits']['hits']), "长度不相等"
        return res['hits']['hits']

    def query_pos_filter(self, res_body, query_str, within=np.inf, fix=False):
        '''仅在开启位置过滤时才会调用'''
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
            # print(pos_list)
            ans=[]
            def dfs(k, b,ans):
                # print(pos_list)
                if (k == n):
                    if not fix:
                        b.sort()
                    for i in range(n - 1):
                        if not (b[i + 1] - b[i] > 0 and b[i + 1] - b[i] <= (within + 1)):
                            return
                    ans.append(b[:])
                    # return True
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

    def sort_query(self,res_body,query_str,method="BM25",k=1.2,b=0.2):
        '''query_str是用户直接搜索的字符串, 返回是np数组, 是result索引的一个列表, 也返回对应score'''
        # TODO 如果关键词重复怎么办?
        res_num=len(res_body)
        keywords = query_str.split(' ')
        keywords_num=len(keywords)
        if method=="TF-IDF":
            idf = np.zeros(shape=(keywords_num))
            tf = np.zeros(shape=(keywords_num, res_num))
            for i in range(keywords_num):
                hit_num_corpus=self.keyword_hit_num(keywords[i])
                idf[i] = np.log(self.docs_num / hit_num_corpus) # TODO 这里可以优化, 但是向量太短了, 完全没有优化的价值
                for j in range(res_num):
                    hit_num_in_doc=res_body[j]["_source"]["words"].count(keywords[i].rsplit('/')[0]) # bug: res_body[j]["words"]是错的, 应该是res_body[j]["_source"]["words"]
                    tf[i][j]=hit_num_in_doc/len(res_body[j]["_source"]["words"])
            tf_idf=tf*idf[:,np.newaxis]
            res_tf_idf=np.sum(tf_idf,axis=0)
            sort_res= (-res_tf_idf).argsort()
            return sort_res
        elif method=="BM25": # TODO 多数代码相似, 怎么改才能共用
            idf = np.zeros(shape=(keywords_num))
            ktf = np.zeros(shape=(keywords_num, res_num)) # 其实就是右边这一项
            for i in range(keywords_num):
                hit_num_corpus = self.keyword_hit_num(keywords[i])
                idf[i] = np.log(self.docs_num / hit_num_corpus)  # TODO 这里可以优化, 但是向量太短了, 完全没有优化的价值
                for j in range(res_num):
                    hit_num_in_doc = res_body[j]["_source"]["words"].count(keywords[i].rsplit('/')[0])
                    ktf[i][j] = hit_num_in_doc / (hit_num_in_doc+ k*( 1-b+b*(len(res_body[j]["_source"]["words"])/self.avgdl)))
            tf_idf = ktf * idf[:, np.newaxis]
            res_tf_idf = np.sum(tf_idf, axis=0)
            sort_res = (-res_tf_idf).argsort()
            return sort_res, np.sort(res_tf_idf)[::-1]

    def get_docs_num(self):
        # TODO 每次更新, 需要再次调用这个函数
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


if __name__=='__main__':
    query_str="灰尘 微粒/n 细菌/n within=3"
    se = SearchEngine(sentence_log='sentence_id',index_name="full-index")
    pos_search=True
    query_str, within, fixed = get_within_fixed(query_str)
    query_dict = se.get_query_dict(query_str, pos=pos_search)
    res_body = se.get_query_res(query_dict)
    if pos_search:
        res_body = se.query_pos_filter(res_body, query_str, within=within, fix=fixed)
    sort_res = se.sort_query(res_body, query_str)
    res_num = len(res_body)
    if (res_num > 10):
        sort_res = sort_res[:10]
    res_body = [res_body[i] for i in sort_res]
    print(len(res_body))
    # render_template('search.html', res_body=res_body, pos_search=pos_search)
    # 检测排序
    # query_str = "细菌/n 微粒/n 灰尘/n"
    # query_dict = my_es.get_query_dict(query_str,pos=True)
    # res_body = my_es.get_query_res(query_dict)
    # filter_res=my_es.query_pos_filter(res_body,query_str,within=2,fix=True)
    # print(len(filter_res))

    # sort_res = my_es.sort_query(res_body, query_str,method="TF-IDF")
    # print(sort_res[:10])

    # print(my_es.avgdl)

    # indexCreater.create_index()
    # indexCreater.index_file("tmp_output.txt") # 错误处理

    # import timeit
    # print(indexCreater.keyword_hit_num())
    # print(indexCreater.docs_num)
    # query_str = "意竹/n"
    # print(json.dumps(query(query_str)))
    # res = indexCreater.query(query)
    # print("Got %d Hits:" % requery['query']['bool']['minimum_should_match']=1s['hits']['total']['value'])
    # cnt = 0
    # for hit in res['hits']['hits']:
    #     print(cnt)
    #     print(hit["_source"])
    #     cnt += 1
    # res = es.search(index=index_name, body=query)
    # print("Got %d Hits:" % res['hits']['total']['value'])
    # print(res)

