from elasticsearch import Elasticsearch
from elasticsearch import helpers
import time
from config import mappings, files, query_template, pose_set, index_name
from util import get_within_fixed
from collections import defaultdict
from bert_serving.client import BertClient
import numpy as np
import json
import gc
import dill
# import pickle as pkl
import re
import os
import re

class SearchEngine:
    chinese_pattern=re.compile(r"[^\u4e00-\u9fa5]+")
    def __init__(self, index_name):
        '''
        argv:("test-index"),es的索引名
        change state:存入索引名,初始化sentence_log,更新docs_num和avgdl两个属性
        '''
        self.wrong_log = 'wrong.log'
        self.sentence_log_path = 'sentence_log'
        self.read_sentence_log()

        self.bc = BertClient()
        self.es = Elasticsearch()

        self.index_name = index_name
        self.mappings = mappings
        if not self.es.indices.exists(index=self.index_name):
            self.es.indices.create(index=self.index_name, ignore=[400, 404], body = self.mappings)
        else:
            self.get_docs_num()
        

    # def delete_index(self, index_name):
    #     self.es.indices.delete(index=index_name, ignore=[400, 404])
    #     print('Delete index {} succesful!'.format(index_name))

    def read_sentence_log(self):
        '''
        state:加载self.sentence_log对应的pickle 字典, 如果不存在创建一个空的defaultdict
        '''
        try:
            with open(self.sentence_log_path, 'rb') as f:
                self.sentence_log = dill.load(f)
        except:
            # 不需要创建, 如果需要写, 自然会写
            self.sentence_log = defaultdict(lambda:0)

    def write_sentence_log(self):
        '''
        state:写文件
        '''
        with open(self.sentence_log_path, 'wb') as f:
            dill.dump(self.sentence_log,f)
    @staticmethod
    def split_word_pos(word_poses):
        '''返回词列表, 比如['明天/n','你好/v']->['明天','你好']'''
        return [word.split('/')[0] for word in word_poses]

    def store_index(self, result):
        '''其中result是一个列表, 每一个成员是一个列表, 包括了
        "0秒之内就再次燃烧起来了。"
        "0秒","之内","就","再次","燃烧","起来","了","。"
        "0秒/t","之内/f","就/d","再次/d","燃烧/v","起来/v","了/u","。/w"
        id, id没什么用
        state:存入到es中(self.index_name),写sentence_log文件,更新docs_num和avgdl两个属性
        call:被index_file调用
        '''
        embedding = self.bc.encode([SearchEngine.chinese_pattern.sub('',row[0]) for row in result])
        action = ({
                    "_source": {
                        # 'text': row[0], 'poses': row[1]
                        'origin': row[0],
                        'words': row[1],
                        'words_poses': row[2],
                        "embedding": vec
                    },
                    "_id": row[3]
                } for row,vec in zip(result,embedding))
        helpers.bulk(self.es, action, index=self.index_name, raise_on_error=True)
        self.write_sentence_log()
        self.get_docs_num()

    def index_file(self, file_name, max_line=1200000, batch_num=100000):
        '''
        处理一个新闻文件,
        argv:文件路径
        state:改es,sentence_log
        imple:文本处理+store_index
        '''
        begin_time = time.time()
        file_base_name=os.path.basename(file_name)
        start_line_number = self.sentence_log["file_base_name"]+1
        with open(file_name) as f:
            print("Begin read {}".format(file_name))
            result = []
            for linenum, line in enumerate(f,start_line_number):
                line = line.strip()
                if line == '':
                    continue
                words_poses = line.split(' ')
                # try:
                words = self.split_word_pos(words_poses) # word:['苹果','好吃'] poses:['n','adj']
                result.append([''.join(words), words, words_poses, linenum])
                if linenum % batch_num == 0: # 每隔200000句清空一下这个变量
                    end_time = time.time()
                    self.store_index(result) # 存在es中
                    self.sentence_log[file_base_name]=linenum
                    result = []
                    time_diff = end_time - begin_time
                    print("Handle {} sentence! Time Use: {}".format(linenum, time_diff))
                    if linenum>=max_line:
                        break
                # except:
                #     continue
            self.store_index(result) # 处理剩余的结果
            self.sentence_log[file_base_name]=linenum
            time_diff = time.time() - begin_time
            print("Read {} over! Handle {} sentence! Time Use: {}".format(file_name, linenum, time_diff))

    @staticmethod
    def get_query_body(query_str, strict=False):
        '''
        query_str是用户直接搜索的字符串(已去除strict和fixed), strict(=False)严格模式
        返回是es的query body, 用于es.search
        '''
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
        '''
        参数: query_body是es的_search的body(通过get_query_body获取), size是es返回的最大结果数,默认50
        返回: 根据query_body获得es的查询结果, res['hits']['hits'], 是列表
        '''
        res = self.es.search(index=self.index_name, body=query_body, size=size)
        return res['hits']['hits']
    @staticmethod
    def query_pos_filter(res_body, query_str, within=np.inf, fix=False):
        '''
        仅在开启严格模式时才会调用
        within是位置约束(within=5, 表示前一个词与后一个词之间的词数不能超过 5),fix为是否按严格的先后顺序
        返回res_body(es返回的搜索结果)中符合位置约束的过滤结果
        '''
        # keywords是已经split过的列表
        keywords = query_str.split(' ')
        n=len(keywords)
        # 先得到可能的结果列表
        filter_res=[]
        for res in res_body:
            pos_list = [] # 这是个列表, 其元素也是列表, 对应的是query_str第一个分词在这个res中的位置索引列表, 比如, '锅炉', 如果'锅炉'词列表中出现了多次, 那么就返回这些索引, 由于res都是严格匹配的, 不应该出现为空的情况
            res_poses=[word_pose.split('/')[1] for word_pose in res["_source"]["words_poses"]]
            for keyword in keywords: # 找出满足约束的位置
                if keyword in pose_set:
                    pos_list.append([i for i,j in enumerate(res_poses) if j==keyword])
                elif '/' in keyword:
                    pos_list.append([i for i,j in enumerate(res["_source"]["words_poses"]) if j == keyword])
                else:
                    pos_list.append([i for i,j in enumerate(res["_source"]["words"]) if j == keyword])
            b=[0 for _ in range(n)]
            def dfs(k, b): # 检查位置是否满足约束
                if (k == n):
                    _b=b if fix else sorted(b) # 史诗级bug纪念碑
                    for i in range(n - 1):
                        if not (_b[i + 1] - _b[i] > 0 and _b[i + 1] - _b[i] <= (within + 1)):
                            return False
                    return True
                else:
                    for i in pos_list[k]:
                        b[k] = i
                        if dfs(k + 1,b):
                            return True # 为了不再搜索
            if(dfs(0, b)):
                filter_res.append(res)
        return filter_res

    def keyword_hit_num(self,keyword):
        '''
        既支持含有pose的, 又支持不含有pose的, 也就是说, '锅炉'可以, '锅炉/n'也可以
        返回index中出现了keyword的文档的个数
        '''
        # bug:本来"minimum_should_match": 1, 在should为空的情况下, 是一个也不会返回的
        query = json.loads(json.dumps(query_template))
        query["size"] = 0 # 因为只需要个数
        if '/' in keyword:
            query['query']['bool']['filter'].append({'match': {'words_poses': keyword}})
        else:
            query['query']['bool']['filter'].append({'match': {'words': keyword}})
        return self.es.search(index=self.index_name, body=query)['hits']['total']['value']

    def sort_query(self,res_body,query_str,is_tf_idf=False,k=1.2,b=0.2):
        '''
        query_str是用户直接搜索的字符串(不包括fixed等),is_tf_idf=False表示用BM25方法,k与b是PM2.5的参数
        返回是np数组, 是result索引的一个列表以及对应的score
        '''
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
        '''state:更新docs_num和avgdl两个属性'''
        self.docs_num=self.es.count(index=self.index_name)["count"]
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
        self.avgdl=self.es.search(index=self.index_name,body=query,size=0)["aggregations"]["avg_size"]["value"]

    def get_filter_query_res(self, query_str, is_strict):
        '''
        根据原始的query_str(就是用户在输入框输入的, 包含关键词, 和within等), 返回满足的结果, 未排序
        返回:query_str(字符串, 不是列表, 去除了within和fixed), 过滤后res_body,未排序,相当于pipeline
        '''
        query_str, within, fixed = get_within_fixed(query_str)  # 处理字符串, 得到within, fixed的信息
        query_dict = self.get_query_body(query_str, strict=is_strict)
        res_body = self.get_query_res(query_dict)  # 获得查询结果
        if is_strict:  # 如果是严格模式, 还需要过滤
            if not within:
                within = np.inf
            res_body = self.query_pos_filter(res_body, query_str, within=within, fix=fixed)
        return query_str, res_body
    def get_embedding_query_res(self, query_str, max_num=10):
        # import pdb;pdb.set_trace()
        query_str, _, _ = get_within_fixed(query_str)
        query_vector=self.bc.encode([SearchEngine.chinese_pattern.sub('',query_str)])[0]
        script_query = {
        "script_score": {
            "query": {"match_all": {}},
            "script": {
                "source": "cosineSimilarity(params.query_vector, doc['embedding']) + 1.0",
                "params": {"query_vector": query_vector} # params这个字段应该是给script传参, 在source中(source也就是脚本代码内容)通过params.query_vector来引用
                }
            }
        }

        # search_start = time.time()
        response = self.es.search(
            index=self.index_name,
            body={
                "size": max_num,
                "query": script_query
            }
        )
        return response["hits"]["hits"]
        # search_time = time.time() - search_start


if __name__=='__main__':
    #%% 构建索引
    se = SearchEngine(index_name='embedding-index-0')
    # for file in files:
    #     se.index_file(file,max_line=1000,batch_num=1000)
    # pdb.set_trace()
