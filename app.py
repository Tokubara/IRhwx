from flask import Flask
from flask import render_template
from flask import request
from build_index import SearchEngine
from config import files_to_handle
from util import get_within_fixed
from word2vec import get_similar_word, load_wordvector
# import re

se = SearchEngine(index_name='search-index')
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
    pos_search = True # 控制是否控制位置搜索
    if request.method =='POST': # 这个函数几乎全部都是这里了, 可见主要是如何处理表单
        query_str = request.form['keyword'] # 第一个输入框, 也就是要查询的
        old_query_str=query_str
        pos_search = transfer_checkbox(request.form.get('pos_search')) #? 是不是这样的, 意味着, 如果checkbox不勾选, 那么返回是None, 否则返回不是None

        # se = SearchEngine(sentence_log='sentence_id', index_name="full-index")
        # pos_search = True
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
        render_template('search.html', res_body=res_body, pos_search=pos_search,query_str=old_query_str)


        # to_show = count_words(results, keywords_list, windowsize=windowSize, poses_set=set(poses))
        # for item in to_show:
        #     try:
        #         item['pos'] = pos2chin[item['pos']] # 本来to_show中也有pos属性, 但是是n,x这样, 这个循环的目的是把它转换为'名词'之类的
        #     except KeyError as e:
        #         item['pos'] = item['pos']
        # initial_info = {'query': query_str, 'window': request.form['window'], 'poses': poses} # poses也就是, 用户勾选的那些词性
        # if pos_search:
        #     if len(words) == 0:
        #         sim_words = "没有找到意思相近的词语"
        #     else:
        #         sim_words = '关联的词语：{}'.format(' '.join(words))
        #     return render_template('search.html', info=initial_info, ans=to_show, pos_info=pos_info, \
        #                             pos_search=pos_search, sim_words=sim_words)
        # else:
        #     return render_template('search.html', info=initial_info, ans=to_show, pos_info=pos_info, \
        #                             pos_search=pos_search)

    return render_template('search.html')

if __name__ == '__main__':
    wv = load_wordvector('wordvec')
    app.run()
