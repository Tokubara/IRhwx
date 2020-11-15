from flask import Flask
from flask import render_template
from flask import request
from build_index import SearchEngine
# from config import files_to_handle
from util import get_within_fixed
import numpy as np
# from word2vec import get_similar_word, load_wordvector
# import re

se = SearchEngine(index_name='full-index')
app = Flask(__name__)
# pos2chin, pos2show, pos_list = get_pos_explain()
# pos2show['w'] = False # w对应的是标点
# pos2show['x'] = False # x对应的是其它
# pos_info = {'pos2chin': pos2chin, 'pos2show': pos2show, 'pos': pos_list, 'length': len(pos_list)} # 把有关词性的信息打包到字典中,pos_info
# pos_search_search = True
# wv = None

def transfer_checkbox(value):
    return value is not None



@app.route('/', methods=['GET', 'POST'])
@app.route('/search', methods=['GET', 'POST'])
def index(): #? 奇怪的是, 这里不是dynamic pattern,为什么有name参数, 猜测是多余的
    # is_strict = False # 控制是否控制位置搜索
    if request.method =='POST': # 这个函数几乎全部都是这里了, 可见主要是如何处理表单
        query_str = request.form['keyword'] # 第一个输入框, 也就是要查询的
        old_query_str=query_str
        is_strict = transfer_checkbox(request.form.get('is_strict')) #? 是不是这样的, 意味着, 如果checkbox不勾选, 那么返回是None, 否则返回不是None
        is_tf_idf=transfer_checkbox(request.form.get('is_tf_idf'))
        method="TF-IDF" if is_tf_idf else "BM25"
        # se = SearchEngine(sentence_log='sentence_id', index_name="full-index")
        # is_strict = True
        query_str, within, fixed = get_within_fixed(query_str)
        query_dict = se.get_query_dict(query_str, pos=is_strict)
        res_body = se.get_query_res(query_dict)
        if is_strict:
            if not within:
                within=np.inf
            res_body = se.query_pos_filter(res_body, query_str, within=within, fix=fixed)
        sort_res = se.sort_query(res_body, query_str, method=method)
        res_num = len(res_body)
        if (res_num > 10):
            sort_res = sort_res[:10]
            res_num=10
        res_body = [res_body[i]["_source"]["origin"] for i in sort_res]
        # print("res_num={}".format(res_num))
        # print(res_body)
        # for i,j in enumerate(res_body):
        #     print("{} {}".format(i+1,j))
        return render_template('search.html', res_body=res_body, is_strict=is_strict, query_str=old_query_str, res_num=res_num, is_tf_idf=is_tf_idf)
    return render_template('search.html')

if __name__ == '__main__':
    # wv = load_wordvector('wordvec')
    app.run()
