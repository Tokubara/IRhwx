from elasticsearch import Elasticsearch
from elasticsearch import helpers

es=Elasticsearch()
es.indices.create(index='news')
es.create()


a=["紫操","西操","东操"]
b=["真的不喜欢","非常喜欢","最讨厌"]
action=({
    # "_index":"news",
    "_source":{"title":a[i],"body":b[i],
               },
"_id":i
} for i in range(3))
helpers.bulk(es,action)

import sys


tmp_foo = []

# 2 references, 1 from the foo var and 1 from getrefcount
print(sys.getrefcount(tmp_foo))


def bar(a):
    # 4 references
    # and
    print(sys.getrefcount(a)) #? 为什么这里是4? Python's function stack?

# 此时是1
bar(tmp_foo) # 由于bar的调用+1, 再由于getrefcount, 再+1
# 2 references, the function scope is destroyed
print(sys.getrefcount(tmp_foo))

import gc
import ctypes

# We use ctypes moule  to access our unreachable objects by memory address.
class PyObject(ctypes.Structure): #? 为什么会有unreachable的objects?
    _fields_ = [("refcnt", ctypes.c_long)]


gc.disable()  # Disable generational gc #? 那么难道是默认启用的?

lst = []
lst.append(lst) # 这是啥情况, 自己加自己?

# Store address of the list
lst_address = id(lst)

# Destroy the lst reference
del lst

object_1 = {'a':1}
object_2 = {'b':2}
object_1['obj2'] = object_2 # 字典相互引用
object_2['obj1'] = object_1

obj_address = id(object_1)

# Destroy references
del object_1, object_2

# Uncomment if you want to manually run garbage collection process
gc.collect()

# Check the reference count
print(PyObject.from_address(obj_address).refcnt)
print(PyObject.from_address(lst_address).refcnt)

from elasticsearch import Elasticsearch
es=Elasticsearch()
es.search(index="news")

for i in range(False|4):
    print(i)

