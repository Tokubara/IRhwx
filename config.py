maps =  {"mappings": {

  "properties": {
    "origin": {
      "type": "keyword"
    },
    "words":{
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

# files_to_handle = ['/Users/huangyf/Dataset/SogouT/Sogou0012_out', '/Users/huangyf/Dataset/SogouT/Sogou0002_out']
files_to_handle = ['/Users/quebec/Downloads/IRHomeWork-master/mini_sougou12_output.txt']
