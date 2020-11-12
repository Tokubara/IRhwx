from flask import Flask
from flask import render_template
from flask import request
from build_index import SearchEngine
from config import files_to_handle
from util import count_words, get_pos_explain
from word2vec import get_similar_word, load_wordvector

se = SearchEngine(index_name='search-index')
app = Flask(__name__)
pos2chin, pos2show, pos_list = get_pos_explain()
pos2show['w'] = False # w对应的是标点
pos2show['x'] = False # x对应的是其它
pos_info = {'pos2chin': pos2chin, 'pos2show': pos2show, 'pos': pos_list, 'length': len(pos_list)} # 把有关词性的信息打包到字典中,pos_info
fuzzy_search = True
wv = None

def transfer_checkbox(value):
    return value is not None

def get_more_query(wv, keyWords, results, keywords_list):
    similar_words = get_similar_word(keyWords[0], wv)
    print(similar_words)
    words = []
    sims = []
    number = 0
    for word, score in similar_words:
        if score > 0.64:
            words.append(word)
            sims.append(score)
    for sim_word in words:
        temp_keywords = keyWords.copy()
        temp_keywords[0] = sim_word
        temp_num, temp_result = se.query(temp_keywords, size=5000)
        results.append(temp_result)
        keywords_list.append(temp_keywords)
        number += temp_num
    return words, sims, number

@app.route('/', methods=['GET', 'POST'])
@app.route('/search', methods=['GET', 'POST'])
def index(name=None): #? 奇怪的是, 这里不是dynamic pattern,为什么有name参数, 猜测是多余的
    # keyWord = None
    # pageNum = 0
    # KeyWord与KeyWords两个变量的关系是, 前者是输入的字符串, 后者是前者split的结果
    fuzzy_search = True # 控制是否是关联搜索, 可以设置
    if request.method =='POST': # 这个函数几乎全部都是这里了, 可见主要是如何处理表单

        keyWord = request.form['keyword'] # 第一个输入框, 也就是要查询的

        poses = request.form.getlist('poses') # 之所以用getlist, 是循环 # 勾选了哪些, 得到就是相应的词性, 比如['n','v','x']等
        fuzzy_search = transfer_checkbox(request.form.get('fuzzy')) #? 是不是这样的, 意味着, 如果checkbox不勾选, 那么返回是None, 否则返回不是None
        for key in pos2show:
            pos2show[key] = False # 似乎是初始化, 全部不要勾选
        for select_pos in poses: # 开始检查, select_pos处要勾选
            pos2show[select_pos] = True

        try:
            windowSize = int(request.form['window'])
        except ValueError as e:
            windowSize = 5
        keyWords = keyWord.split(' ')
        print("Query: {}".format(keyWord))
        results = []
        keywords_list = []
        number, result = se.query(keyWords, size=5000)
        results.append(result) #? 为什么results是个列表, 为什么一次的结果还不够?
        keywords_list.append(keyWords) #? 为什么需要保存keyWords
        if fuzzy_search:
            words, sims, temp_number = get_more_query(wv, keyWords, results, keywords_list)
            number += temp_number
        print("Got {} Hits.".format(number))
        to_show = count_words(results, keywords_list, windowsize=windowSize, poses_set=set(poses))
        for item in to_show:
            try:
                item['pos'] = pos2chin[item['pos']] # 本来to_show中也有pos属性, 但是是n,x这样, 这个循环的目的是把它转换为'名词'之类的
            except KeyError as e:
                item['pos'] = item['pos']
        initial_info = {'query': keyWord, 'window': request.form['window'], 'poses': poses} # poses也就是, 用户勾选的那些词性
        if fuzzy_search:
            if len(words) == 0:
                sim_words = "没有找到意思相近的词语"
            else:
                sim_words = '关联的词语：{}'.format(' '.join(words))
            return render_template('search.html', info=initial_info, ans=to_show, pos_info=pos_info, \
                                    fuzzy=fuzzy_search, sim_words=sim_words)
        else:
            return render_template('search.html', info=initial_info, ans=to_show, pos_info=pos_info, \
                                    fuzzy=fuzzy_search)
    return render_template('search.html', pos_info=pos_info, fuzzy=fuzzy_search)

if __name__ == '__main__':
    wv = load_wordvector('wordvec')
    app.run()
