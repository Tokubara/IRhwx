#%% 头部
from elasticsearch import Elasticsearch
from elasticsearch import helpers

es=Elasticsearch()
#%% 验证must字段的例子
query={
    "query":{
        "bool":{
            "must":[{
                "term":{
                    "title":"紫"
                }},
                {
                "term":{
                    "body":"大"
                }
}]
            }
        }
    }

es.search(index="news",body=query)

#%% 验证term是否可以是列表
query={
    "query":{
        "bool":{
            "must":[
                {
                "terms":{
                    "body":["不","喜欢"]
                }
}]
            }
        }
    }

es.search(index="news",body=query)
#%% boosting query, 结果想不到
query={
    "query":{
"match":{
                    "title":"紫操"
                }
    }
}

es.search(index="news",body=query)
