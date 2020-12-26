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

# a=[1,2,3]
a=open('/etc/passwd')
try:
    while True:
        print(next(a))
except StopIteration:
    pass

a=open('/etc/passwd')
while True:
    line = next(a)
    if(line is None):
        break
    print(line)

with open('/etc/passwd') as f:
    while True:
        line = next(f, None)
        if line is None:
            break
        print(line, end='')

def g():
    print('1')
    x= yield "hello"
    print("2","x=",x)
    y=5+(yield x)
    print("3", "y=", y)

f=g()
next(f) # 似乎相当于f.next()
f.send(5)
f.send(2)


class Node:
    def __init__(self, value):
        self._value = value
        self._children = []
    def __repr__(self):
        return 'Node({!r})'.format(self._value)
    def add_child(self, node):
        self._children.append(node)
    def __iter__(self):
        return iter(self._children)
    def depth_first(self):
        yield self
        for c in self:
            yield from c.depth_first()
# Example
if __name__ == '__main__':
    root = Node(0)
    child1 = Node(1)
    child2 = Node(2)
    root.add_child(child1)
    root.add_child(child2)
    child1.add_child(Node(3))
    child1.add_child(Node(4))
    child2.add_child(Node(5))
    for ch in root.depth_first():
        print(ch)     # Outputs Node(0), Node(1), Node(3), Node(4), Node(2), Node(5)

from collections import namedtuple
Point=namedtuple("Point",["x","y"],defaults=[0,0])
point(2,3)
