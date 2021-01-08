from flask import Flask
from flask import render_template
from flask import request
from build_index import SearchEngine
from config import app_index_name

se = SearchEngine(index_name='embedding-index-0')
app = Flask(__name__)

def transfer_checkbox(value):
    return value is not None

@app.route('/', methods=['GET', 'POST'])
@app.route('/search', methods=['GET', 'POST'])
def index():
    if request.method =='POST':
        # 获得获取的数据, 有3个, 查询字符串, 是否严格模式, 是否使用tf-idf(默认不实用)
        query_str = request.form['keyword']
        old_query_str=query_str
        is_embedding=transfer_checkbox(request.form.get('is_embedding'))
        is_strict = transfer_checkbox(request.form.get('is_strict'))
        is_tf_idf=transfer_checkbox(request.form.get('is_tf_idf'))
        if is_embedding:
            res_obj = se.get_embedding_query_res(query_str, max_num=10)
            res_body = [item["_source"]["origin"] for item in res_obj]
            score = [item["_score"] for item in res_obj]
            no_result = len(res_obj)==0
            return render_template('search.html', res_body=res_body, is_strict=is_strict, query_str=old_query_str, res_num=len(res_obj), is_tf_idf=is_tf_idf,no_result=no_result,score=score)
        else:
            query_str, res_body = se.get_filter_query_res(query_str, is_strict)
            res_num = len(res_body)
            no_result = res_num == 0
            score=None

            if not no_result: # 如果有搜索结果, 才需要排序
                sort_res,score = se.sort_query(res_body, query_str, is_tf_idf=is_tf_idf)
                if (res_num > 10):
                    sort_res = sort_res[:10]
                    res_num=10
                res_body = [res_body[i]["_source"]["origin"] for i in sort_res] # res_body是显示的字符串列表
            return render_template('search.html', res_body=res_body, is_strict=is_strict, query_str=old_query_str, res_num=res_num, is_tf_idf=is_tf_idf,no_result=no_result,score=score)
    return render_template('search.html')


if __name__ == '__main__':
    app.run()
