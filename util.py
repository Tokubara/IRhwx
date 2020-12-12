import numpy as np
import re

def get_within_fixed(query_str):
    '''解析用户输入的字符串, 返回三部分, 关键词(不是列表, 是字符串), 以及两个bool值, within和fixed'''
    within=False
    fixed=False
    find_within=query_str.find("within")
    if find_within>0:
        keyword=query_str[:find_within-1]
        match_obj = re.search(r'within=(\d+)', query_str)
        within=int(match_obj.group(1))
        find_fixed = query_str.find("fixed")
        if(find_fixed>0):
            fixed=True
    else:
        find_fixed=query_str.find("fixed=T")
        if(find_fixed>0):
            keyword = query_str[:find_fixed - 1]
            fixed=True
        else:
            keyword=query_str
    return keyword, within, fixed
