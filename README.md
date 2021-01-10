信息检索(Infomation Retrieval, IR)大作业(之一)

基于elasticsearch和flask(最基础的flask, 因为作者太菜, flask也不怎么会)

支持的功能:
- 给文件, 索引到elasticsearch. 不过由于作业提供的数据, 代码支持的文件是用THULAC分好词且有词性标注的文件, 每一行长这样:
> 0时/t ，/w 青衣/n 男/a 开口/v 打破/v 周围/f 嗳昧/n 的/u 气氛/n ，/w “/w 小/a 弟/n 你/r 叫/v 什么/r 名字/n ？/w
- 搜索支持位置过滤, 包括词性过滤, 打开严格模式(strict), 严格模式就是给的所有关键词全都需要出现. 进一步可以打开位置约束, 语法就是, "fixed=T", 表示位置也要一模一样, 比如搜索"安全 事故", 那么"发生了一起事故, 安全警钟长鸣"是搜不到的. 还可以约束关键词的间隔距离, 语法是"within=2", 表示对这些关键词, 必须存在一个排列(如果没有位置约束), 使得相邻两词之间不得间隔多于2个词.
- 支持对结果根据BM25/TF-IDF排序.
- 搜索支持词性过滤, 比如"青衣/n".
- 关键词和词性可以混合, "男 v fixed=T within=0", 表示男后面必须紧跟一个动词
- 支持bert句向量搜索, 会根据句的相似度排序.
详情可以看实验报告.



怎么跑起来?
- 需要装elasticsearch, 我装的是7.10, 要运行代码, 也需要先在命令行启动elasticsearch服务.
- 如果要使用bert句向量, 需要先装bert. 参考[这个](https://www.codenong.com/cs105671415/).
- 先在config.py中给出THULAC分好词的文件路径, 我给出了tmp_output_1000.txt, 包括1000行, config.py写的也是这个路径. 可以调一调batch和max_line参数, 运行`python build_index.py`
- 构建完索引, 就可以`python app.py`, 打开网页.
