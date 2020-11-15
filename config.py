maps={
  "mappings": {
    "properties": {
      "origin": {
        "type": "keyword"
      },
      "words": {
        "type": "keyword"
      },
      "words_poses": {
        "type": "keyword"
      }
    }
  }
}

query_template = {
        "query": {
            "bool": {
                "must":[],
                "should":[],
                "filter":[],
                "minimum_should_match" : 0,
            }
        }
    }

files = ['tmp_output.txt'] # 分好词的文件

pose_set=("n","np","ns","ni","nz","m","q","mq","t","f","s","v","a","d","h","k","i","j","r","c","p","u","y","e","o","g","w","x") # 词性集合

index_name="test-index" # 可设置, 索引名

app_index_name="full-index" # 由于build_index可以选择build不同的index, 这里是app中选择使用的index
