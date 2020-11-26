# 中文维基百科数据获取与预处理
&emsp;&emsp;**前言**：阅读本篇博文，您将学会如何**使用scrapy框架并基于层次优先队列的网页爬虫**以及**维基页面的结构与半结构数据自动抽取**，同时将可以**获得以计算机IT为主的超过9000个实体的中文结构化和半结构化文本语料**。项目已经开源于GitHub地址，欢迎Star或提出PR。

&emsp;&emsp;运行爬虫，可前往counselor目录查看“启动爬虫.md”文件；爬虫后运行预处理，前往data_process目录查看“数据抽取.md”

---

&emsp;&emsp;**维基百科（wikipedia）** 是目前最大的开放式开放领域百科网站之一，包含包括英文、中文等多种语言。现如今在众多人工智能自然语言处理任务中均取自于维基百科，例如斯坦福大学开源的机器阅读理解评测数据集SQuAD1.1和SQuAD2.0的问答语料直接取自于维基百科；FreeBase世界知识库也直接由维基百科构建而成。维基百科之所以能够收到自然语言处理研究者们的关注，主要得益于维基百科的知识的齐全、丰富，且其来自于世界的各个专家、大众一同编辑而成，知识的准确率和细粒度得到一致的认可。

&emsp;&emsp;现阶段绝大多数的语料构建均为英文维基百科，而在英文语料上实现的功能或算法通常并不能完全兼容中文，同时调研了当前的已有方法也没有系统地同时对维基百科的页面**爬取**和**处理**两个关键步骤，**本篇文章将提供一个中文维基百科的数据获取和预处理**。

&emsp;&emsp;本文的主要有以下四个部分

 - 中文维基百科网页分析
 - 基于scrapy框架和层次优先队列的维基百科数据爬取
 - 维基页面的结构与半结构数据自动抽取
 - 中文结构化和半结构化语料

&emsp;&emsp;完成整个过程你需要拥有的配置包括：

 - 编译环境需要有：python3+scrapy+numpy+tqdm+lxml
 - 需要能够访问中文维基百科（[zh.wikipedia.org](https://zh.wikipedia.org)），如果无法完成访问的可以使用VPN或SSR工具；
 - 中文繁简转化包langconv

---

###  1、中文维基百科网页分析
&emsp;&emsp;维基百科网站页面除了一些网站必有的功能外，百科类的界面主要有两种，分别是：

 - **分类页面：** 对应的URL请求则属于**分类请求**；
 - **内容页面：** 对应的URL请求则属于**内容请求**；

&emsp;&emsp;以计算机科学为例，其分类页面如图所示：

![在这里插入图片描述](https://img-blog.csdnimg.cn/20201126205521653.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3FxXzM2NDI2NjUw,size_16,color_FFFFFF,t_70#pic_center)
&emsp;&emsp;分类页面只会存在与该分类相关的关键词实体（下统一称作实体）的超链接URL请求，这些请求也主要分为分类请求和内容请求。对于分类请求则是下一个子类，而内容请求则是该对应实体的详细讲解页面。
&emsp;&emsp;分类请求的URL格式为

```python
https://zh.wikipedia.org/wiki/Category:xxx
```
例如实体“计算机学科”的分类请求URL为：

```python
https://zh.wikipedia.org/wiki/Category:计算机学科
```
可以发现，其请求链接中包含“Category:”子串，则在后期可以通过该子串来判断请求类型是否是分类请求；

&emsp;&emsp;内容请求则是显示实体的具体内容的页面，其URL请求格式为：

```python
https://zh.wikipedia.org/wiki/xxx
```
例如实体“计算机学科”的内容请求URL为：

```python
https://zh.wikipedia.org/wiki/计算机学科
```

如图所示，此时不是显示分类目录，而是具体的内容。

![在这里插入图片描述](https://img-blog.csdnimg.cn/20201126210155394.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3FxXzM2NDI2NjUw,size_16,color_FFFFFF,t_70#pic_center)
因此，本文主要以这两种请求，来实现对中文维基百科的爬取


###  2、基于scrapy框架和层次优先队列的维基百科数据爬取
&emsp;&emsp;维基百科收录的实体数量是百万千万级别的，我们不可能也无须全部爬取，因此如何从维基百科中爬取我们所需要的内容？现阶段有的GitHub提供的维基百科爬虫存在一些问题：
（1）**爬虫完全开放式无约束**：我们希望爬虫能够爬取我们需要的内容，而不是乱爬。例如如果我们爬取与计算机学科有关的内容，则爬虫不应该去花费时间和资源去爬取其他学科或领域的内容；
（2）**大多数是基于深度优先搜素**：深搜往往存在一个问题就是容易使得爬虫爬取到无关的页面，而且深搜往往是到终点（相当于树中的叶子结点）后才回溯，一旦错爬则越陷越深；
（3）在实际爬取中我们会发现爬虫很容易爬取到一些包括游戏、娱乐，或者是维基百科自带的一些用户中心、使用文档指南等等我们不希望获取的内容；
（4）有些没有优化的爬虫程序，可能忽略了同一请求的重复爬取问题。对于一些使用外网收费的渠道来访问维基百科的，是需要耗费大量的流量资金；


&emsp;&emsp;本文则从上面提到的分类请求和内容请求两个请求为切入点进行，通过维基百科天然的分类索引来约束我们目标爬取的内容；为了避免请求的重复爬取，以及传统深搜面临的问题，本文使用scrapy框架自主实现了层次优先队列的爬虫方法。也许有的读者会想scrapy或其他框架可能提供了自带的队列机制，为什么要自己实现？因为在具体爬取时，我们更希望能够随时初始化队列，且能够保存到本地，在下次爬取时则直接将保存的队列再次初始化，避免再次爬取已爬取的页面。

####  2.1 创建队列
&emsp;&emsp;python创建一个Queue类，该类用于**保存候选请求队列（candidates）**、**已爬取的请求队列（has_viewd）**，

 - **候选队列（candidates）**：爬虫程序运行初期，需要手动在里面添加一个爬虫入口请求（建议只放一个）。如果放置的请求时分类请求，则爬虫会根据子分类依次进行层次遍历；如果放置的是内容请求，则程序只爬取该内容页面后自动终止；本文的scrapy程序中设定对candidates队列的检测，如果为空则停止爬虫程序；
 - **已爬取队列（has_viewd）**：每次处理一个请求后（不论是分类请求还是内容请求），都会将这个请求加入到已爬取队列中，每次在处理一个请求时都会判断当前的请求是否在这个队列中，如果已存在则不再执行爬取，减少重复的流量资源和时间消耗；

&emsp;&emsp;队列类的源程序如下：

```python
import numpy as np
import os
# made by wjn
# homepage:www.wjn1996.cn

class Queue():
    candidates = [] # 保存候选的请求列表
    has_viewd = [] # 保存已经被处理过的请求
    save_every = 100 # has_viewd每100次执行一次保存
    # 初始化时需要添加若干个入口请求
    candidates.append('https://zh.wikipedia.org/wiki/Category:%E8%AE%A1%E7%AE%97%E6%9C%BA%E7%BC%96%E7%A8%8B')

    def load_npy(self): # 用于加载保存在本地的已爬取请求队列
        if os.path.exists('../orgin_page/has_viewd.npy'):
            self.has_viewd = np.load('../orgin_page/has_viewd.npy').tolist()

    def save_has_viewd(self): # 保存已经访问过的请求队列
        np.save('../orgin_page/has_viewd.npy',self.has_viewd)

    def add_candidate(self, url):
        # 注意，执行该函数说明获得了一个新的请求，需要待处理（从分类或内容页面解析得到的链接）
        if url not in self.candidates and url not in self.has_viewd:
            self.candidates.append(url)

    def add_candidates(self, url_list):
        # 批量添加注意，执行该函数说明获得了一个新的请求，需要待处理（从分类或内容页面解析得到的链接）
        for url in url_list:
            self.add_candidate(url)

    def delete_candidate(self, url):
        # 注意，执行该函数时，说明有进程已经收到该请求，在处理前需要将候选列表中该请求删除，表示已有进程已经拿到该请求
        if url in self.candidates:
            self.candidates.remove(url)

    def add_has_viewd(self, url):
        # 注意，执行该函数时，说明有进程已经收到请求，并进行了相关处理，现需要更新队列状态
        if url not in self.candidates and url not in self.has_viewd:
            # 如果当前请求既不在候选列表，也不在已爬列表，则加入
            self.has_viewd.append(url)
        elif url in self.candidates and url not in self.has_viewd:
            # 如果当前请求在候选列表中，且不在已爬列表，则说明有进程提前读取该页面，但候选列表还没更新，则加入
            # 并将候选列表对应的请求删除
            self.has_viewd.append(url)
            self.delete_candidate(url)
        elif url in self.candidates and url in self.has_viewd:
            # 如果当前请求在候选列表中，也在已爬列表中，则说明有进程已经完成了爬取，但候选列表没更新，则直接
            # 删掉候选列表中指定的请求
            self.delete_candidate(url)
            # 最后一种情况是当前请求不在候选列表，但在已爬列表，而还能遇到该请求，说明该请求属于滞后请求，无视即可

```

####  2.2 Scrapy爬虫
&emsp;&emsp;scrapy是基于python语言设计的可支持并行分布式的爬虫框架，本文并不适用爬虫框架自带的访问队列机制，而结合上面给出的Queue类来实现爬取，主要思路是：

 1. 定义一个WikiSpider类并继承scrapy.Spider，初始化Queue类对象，并将其candidates请求队列初始化到scrapy默认的启动列表（start_urls），注意scrapy框架的start_urls只会被处理一次，即便在程序运行中动态更新也不会影响爬虫的爬取，因此我们只使用start_urls作为启动的请求队列，后期爬虫获取的新请求全部来自于Queue类中的candidates；
 2. 重写sparse方法，该方法只会被执行一次，因此主要用于对start_urls的请求进行处理：如果当前请求URL包含“Category:”，则认为是分类请求，其将被转发至分类请求的处理函数；否则将视为内容请求，并转发至内容请求处理函数；
 3. 创建分类请求处理函数parse_category和内容请求处理函数parse_content。对于parse_category方法中，爬取该分类页面，并获取对应的子分类请求和内容请求，加入到candidates中；对于parse_content，则只有内容，返回给pipelines执行页面数据的保存工作；所有处理的页面后都将加入到has_viewd已爬取队列中；

&emsp;&emsp;下面给出scrapy关键的两个代码：

（1）**wiki.py（主要为爬虫类文件）**

```python
# -*- coding: utf-8 -*-
import scrapy
from scrapy.selector import Selector
from items import ContentItem
from queue import Queue
import time
from langconv import *
from filter_words import filter_url
# made by wjn
# homepage:www.wjn1996.cn

def Traditional2Simplified(sentence):
    '''
    将sentence中的繁体字转为简体字
    :param sentence: 待转换的句子
    :return: 将句子中繁体字转换为简体字之后的句子
    '''
    sentence = Converter('zh-hans').convert(sentence)
    return sentence

def split(url_list):
    '''
    分离两种不同的请求类型（分类/内容）
    :return:
    '''
    cates_url, content_url = [], []
    for url in url_list:
        if 'Category:' in url:
            cates_url.append(url)
        else:
            content_url.append(url)
    return cates_url, content_url

def filter(url):
    # 如果字符串url中包含要过滤的词，则为True
    # filter_url = ['游戏', '%E6%B8%B8%E6%88%8F', '维基', '%E7%BB%B4%E5%9F%BA', '幻想', '我的世界', '魔兽']
    for i in filter_url:
        if i in url:
            return True
    return False

class WiKiSpider(scrapy.Spider):
    urlQueue = Queue()
    name = 'wikipieda_spider'
    allowed_domains = ['zh.wikipedia.org']
    start_urls = ['https://zh.wikipedia.org/wiki/Category:%E8%AE%A1%E7%AE%97%E6%9C%BA%E7%BC%96%E7%A8%8B']
    custom_settings = {
        'ITEM_PIPELINES': {'counselor.pipelines.WikiPipeline': 800}
    }
    # scrapy默认启动的用于处理start_urls的方法
    def parse(self, response):
        '''
        在维基百科中，页面有两种类型，分别是分类页面，链接中包含Category，否则是百科页面，例如：
        分类页面：https://zh.wikipedia.org/wiki/Category:计算机科学
        百科页面：https://zh.wikipedia.org/wiki/计算机科学
        本方法用于对请求的链接进行处理，如果是分类型的请求，则交给函数1处理，否则交给函数2处理
        :param response: 候选列表中的某个请求
        :return:
        '''
        # 获得一个新请求
        this_url = response.url
        # self.urlQueue.delete_candidate(this_url)
        # self.start_urls = self.urlQueue.candidates
        # 说明该请求时一个分类
        print('this_url=', this_url)
        self.urlQueue.load_npy()
        if 'Category:' in this_url:
            yield scrapy.Request(this_url, callback=self.parse_category, dont_filter=True)
        else:
            yield scrapy.Request(this_url, callback=self.parse_content, dont_filter=True)

    def parse_category(self, response):
        '''
        处理分类页面的请求
        :param response:
        :return:
        '''
        counselor_item = ContentItem()
        sel = Selector(response)
        this_url = response.url
        self.urlQueue.delete_candidate(this_url)
        search = sel.xpath("//div[@id='content']")
        category_entity = search.xpath("//h1[@id='firstHeading']/text()").extract_first()
        candidate_lists_ = search.xpath("//div[@class='mw-category-generated']//a/@href").extract()
        candidate_lists = []
        # 百科页面有许多超链接是锚链接，需要过滤掉
        for url in candidate_lists_:
            if filter(url): # 分类请求中过滤掉一些不符合的请求（例如明显包含游戏的关键词都不要爬取）
                continue
            if '/wiki' in url and 'https://zh.wikipedia.org' not in url:
                if ':' not in url or (':' in url and 'Category:' in url):
                    candidate_lists.append('https://zh.wikipedia.org' + url)
        # self.start_urls = self.urlQueue.candidates
        cates_url, content_url = split(candidate_lists)
        self.urlQueue.add_has_viewd(this_url)
        self.urlQueue.add_candidates(content_url)
        self.urlQueue.add_candidates(cates_url)
        print('候选请求数=', len(self.urlQueue.candidates))
        print('已处理请求数=', len(self.urlQueue.has_viewd))
        # 处理完分类页面后，将所有可能的内容请求链接直接提交处理队列处理
        if len(self.urlQueue.candidates) == 0:
            # print(111111)
            self.crawler.engine.close_spider(self)
        for url in self.urlQueue.candidates:
            if url in self.urlQueue.has_viewd:
                continue
            if 'Category:' in url:
                # print(url)
                yield scrapy.Request(url, callback=self.parse_category, dont_filter=True)
                # pass
            else:
                yield scrapy.Request(url, callback=self.parse_content, dont_filter=True)

    def parse_content(self, response):
        '''
        处理百科页面请求
        :param response:
        :return:
        '''
        counselor_item = ContentItem()
        sel = Selector(response)
        this_url = response.url
        self.urlQueue.delete_candidate(this_url)
        # print('this_url=', this_url)
        search = sel.xpath("//div[@id='content']")
        content_entity = search.xpath("//h1[@id='firstHeading']/text()").extract_first()
        content_entity = Traditional2Simplified(content_entity)
        content_page = search.xpath("//div[@id='bodyContent']//div[@id='mw-content-text']//div[@class='mw-parser-output']").extract_first()# 将带有html的标签的整个数据拿下，后期做处理
        cates = search.xpath("//div[@id='catlinks']//ul//a/text()").extract()
        self.urlQueue.add_has_viewd(this_url)
        print('候选请求数=', len(self.urlQueue.candidates))
        print('已处理请求数=', len(self.urlQueue.has_viewd))
        self.urlQueue.save_has_viewd()
        # 将当前页面的信息保存下来
        # 如果当前的content的标题或分类属于需要过滤的词（例如我们不想爬取跟游戏有关的，所以包含游戏的请求或分类都不保存）
        is_url_filter = filter(content_entity)
        is_cates_filter = False
        for cate in cates:
            cate = Traditional2Simplified(cate)
            if filter(cate):
                is_cates_filter = True
                break
        if is_url_filter == False and is_cates_filter == False:
            counselor_item['content_entity'] = content_entity.replace(':Category', '')
            counselor_item['category'] = '\t'.join(cates)
            counselor_item['time'] = str(time.time())
            counselor_item['url'] = this_url
            counselor_item['content'] = str(content_page)
            return counselor_item

```

（2）pipelines.py（对页面内容的保存）

```python
# made by wjn
# homepage:www.wjn1996.cn

class WikiPipeline(object):
    def process_item(self, item, spider):
        data = dict(item)[添加链接描述](langconv.py:https://github.com/skydark/nstools/blob/master/zhtools/langconv.py)
        self.writeFile(data)
        return item
    def writeFile(self, data):
        # print('========',len(data),'=========')
        dir = '../data_process/origin_page/'
        with open(dir + data['content_entity'] + '.txt', 'w', encoding='utf-8') as fw:
            fw.write('标题：' + data['content_entity'] + '\n')
            fw.write('分类：' + data['category'] + '\n')
            fw.write('原文地址：' + data['url'] + '\n')
            fw.write('爬取时间：' + data['time'] + '\n\n')
            fw.write(data['content'])
```

&emsp;&emsp;另外还要使用繁转简的langconv工具，可直接下载，并放入到程序的根目录即可：
[zh_wiki.py:https://github.com/skydark/nstools/blob/master/zhtools/zh_wiki.py](zh_wiki.py:https://github.com/skydark/nstools/blob/master/zhtools/zh_wiki.py)
[langconv.py:https://github.com/skydark/nstools/blob/master/zhtools/langconv.py](langconv.py:https://github.com/skydark/nstools/blob/master/zhtools/langconv.py)

&emsp;&emsp;另外，在爬取时，我们发现爬虫依然会爬取到一些奇怪的页面，比如我们希望爬取“人工智能”分类下的内容，爬虫会爬取到许多游戏的介绍，注意，这并不是因为我们的爬虫方法出了问题，而是因为“人工智能”分类下存在“人工智能游戏”这种类，而游戏又会划分到其他页面上。像这种类似的情况维基百科普遍存在。为了避免这种问题出现，本文在爬虫数据处理中加入了filter_words，其是一个列表，存放一些我们不希望爬取的实体或所属的分类中包含的关键词，这样可以进一步约束爬虫不去爬取那部分的分类页面和内容页面。

###  3、维基页面的结构与半结构数据自动抽取

&emsp;&emsp;我们在爬取过程中，并不花费时间处理维基百科内容页面里的具体内容，以提升爬取的速度和效率，而在爬取结束后统一处理。本文爬取内容页面html的“mw-parser-output”类的div标签，该标签内所有内容均与所爬去的实体有关，其余部分的标签则可以不保存。对应的xpath路径是：

```python
//div[@id='bodyContent']//div[@id='mw-content-text']//div[@class='mw-parser-output']
```
调试的效果如图所示：
![在这里插入图片描述](https://img-blog.csdnimg.cn/20201126215323381.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3FxXzM2NDI2NjUw,size_16,color_FFFFFF,t_70#pic_center)
&emsp;&emsp;对爬取后的数据直接保存在本地，随后使用lxml类库中的etree模块来实现xpath解析。我们从三个方面来提取保存的内容：

 - 结构化的数据：对应于维基百科中class="infobox"的table标签，其直接保存的是与当前实体有关的属性，例如在“快速排序”实体页面中，其结构化信息如下图：
![在这里插入图片描述](https://img-blog.csdnimg.cn/20201126215837298.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3FxXzM2NDI2NjUw,size_16,color_FFFFFF,t_70#pic_center)
这一部分数据则可以直接取来作为“快速排序”的结构知识，可以构建知识图谱的初级版本
 - 相关实体：维基百科的最末尾一般会列出与当前实体有关的其他实体及层次关系，其对应的标签为class="navbox"的table，如图所示：
![在这里插入图片描述](https://img-blog.csdnimg.cn/20201126220055623.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3FxXzM2NDI2NjUw,size_16,color_FFFFFF,t_70#pic_center)
这个表完全可以直接提取作为“算法”和“排序算法”等实体的图谱，是天然的构建知识图谱的结构化资源。当然这个表结构相对比较复杂，本文也只处理存在两层嵌套的表格属性提取，使用字典数据结构来保存；
 - 段落处理：这部分是半结构化数据，依然使用字典数据结构来保存。维基百科的每个段落都会有子标题，使用子标题来作为键，而段落的文字、公式和代码片段作为文本来保存。需要具体说明的是，我们不保存图片（维基百科的图片都存在单独的div标签中，不会完全与文字嵌入在一起，这是维基百科的一个好处）；对于公式，维基百科则在页面上保存了latex字符，本文将公式的latex字符保存下来；对于代码片段其基本保存在pre标签中，因此直接将pre内的代码保存即可；


&emsp;&emsp;具体的处理process.py如下所示，功能细节详见代码注释：

```python
import numpy as np
import os
import random as rd
import json
from tqdm import tqdm
from lxml import etree
from langconv import *
from filter_words import filter_url
# made by wjn
# homepage:www.wjn1996.cn

def Traditional2Simplified(sentence):
    '''
    将sentence中的繁体字转为简体字
    :param sentence: 待转换的句子
    :return: 将句子中繁体字转换为简体字之后的句子
    '''
    if type(sentence) == str or str(type(sentence)) == "<class 'lxml.etree._ElementUnicodeResult'>":
        sentence = Converter('zh-hans').convert(sentence)
    elif type(sentence) == list:
        sentence = [Converter('zh-hans').convert(i) for i in sentence]
    return sentence

def filter(entity_title, category_list):
    # entity_title:string, category_list:list
    # filter_url = ['游戏', '%E6%B8%B8%E6%88%8F', '维基', '%E7%BB%B4%E5%9F%BA', '幻想', '我的世界', '魔兽']
    for i in filter_url:
        if i in entity_title:
            return True
        for j in category_list:
            if i in j:
                return True
    return False

def unified_string(object):
    # 如果是一个列表，则转换为字符串，如果是字符串则直接返回
    if type(object) == list:
        return ''.join(object)
    if type(object) == str:
        return object

def extract_infobox(content):
    '''
    维基百科页面中的侧边栏中有一些结构化的表，table表的class="infobox"，可以直接取来作为结构化的数据，作为当前实体的结构化信息
    :param infobox:
    :return:
    '''
    infobox = content.xpath(".//table[contains(@class,'infobox')]//tr")
    knowledge = dict()
    for ei, i in enumerate(infobox):
        th_text = i.xpath(".//th//text()")  # 在infobox中，属性都是用粗体表示的，对应于th标签，维基百科比较好处理
        if len(th_text) == 0:
            continue
        th_text = th_text[0]
        td_text = '\t'.join([unified_string(tdi.xpath(".//text()")) for tdi in i.xpath(".//td")])
        if th_text is not None and th_text != '' and td_text is not None and td_text != '':  # 说明当前行没有属性值，或者不是属性
            th_text = Traditional2Simplified(th_text)
            td_text = Traditional2Simplified(td_text)
            knowledge[th_text] = td_text.replace(' ', '')
    return knowledge

def extract_navbox(content):
    '''
    维基百科的每个内容最后一栏叫做相关条目（查，论，编）（如果存在的话）一般会列出与当前实体有关的其他实体。表头一般是整个大类，表格
    # 下面每一行左侧浅蓝色为一类，右侧罗列的是属于该类的相关实体，这个结构是天然的结构化图谱资源。
    该表格对应的class="navbox".
    （1）表头class="navbox-title"，且内部信息全部包含超链接（维基百科中包含超链接的一定是一个实体）
    （2）每一行，左边表示一个类组，class="navbox-group"；
    （3）每一行右边表示类组内的内容，class="navbox-list"，所有内容都由超链接组成
    :param navbox:
    :return:
    '''
    navbox = content.xpath(".//table[@class='navbox']")
    knowledge = list()
    for ei, i in enumerate(navbox):
        know = dict()
        groups = []
        if len(i.xpath(".//th[@class='navbox-title']//div")) < 2:
            continue
        navbox_title = (i.xpath(".//th[@class='navbox-title']//div")[1]).xpath(".//a//text()")
        if len(navbox_title) == 0:
            continue
        root = Traditional2Simplified(navbox_title[-1])
        navbox_tr = i.xpath(".//table[contains(@class,'navbox-inner')]/tbody/tr")
        for j in navbox_tr:
            sub_table = j.xpath(".//table//tr")
            if len(sub_table) > 0: # 存在表格嵌套
                for k in sub_table:
                    navbox_group = Traditional2Simplified(''.join(k.xpath(".//th[@class='navbox-group']//text()")))
                    navbox_list = k.xpath(".//td[contains(@class,'navbox-list')]//a//text()")
                    if len(navbox_list) == 0:
                        continue
                    group = dict()
                    group[navbox_group] = Traditional2Simplified(list(set(navbox_list)))
                    groups.append(group)
            else:
                navbox_group = Traditional2Simplified(''.join(j.xpath(".//th[@class='navbox-group']//text()")))
                navbox_list = j.xpath(".//td[contains(@class,'navbox-list')]//a//text()")
                if len(navbox_list) == 0:
                    continue
                group = dict()
                group[navbox_group] = Traditional2Simplified(list(set(navbox_list)))
                groups.append(group)
        know[root] = groups
        knowledge.append(know)
    # print(knowledge)
    return knowledge

def extract_paragraph(content):
    # 抽取段落
    '''
    维基百科页面的主要内容为段落文本（部分会有插图，暂时忽略图片，对存在latex的公式则保存）；
    维基百科一开始是一个摘要，然后是目录，下面则是根据目录中的子标题分别展示相应的文本内容。我们只取标签为<h3>对应为子标题，p等作为文本
    :param paragraph:
    :return:
    '''

    def process_text(text):
        # xpath提取了每个段落中夹在公式的文本，现需要对该文本进行处理
        # text是一个列表，其中字符串类为纯文本，直接添加即可，而对于xpath对象，则需要做处理，并对其后续的一些多余字符进行删除
        # 文本中以超链接为主的词一定是一个实体
        text_process = []
        frag_i = 0
        while frag_i < len(text):
            # print('type=', str(type(text[frag_i])) == "<class 'lxml.etree._ElementUnicodeResult'>")
            if str(type(text[frag_i])) == "<class 'lxml.etree._ElementUnicodeResult'>":
                if text[frag_i].strip() != '':
                    text_process.append(Traditional2Simplified(text[frag_i].strip()))
                frag_i += 1
            else:
                # xpath对象，要抽取公式对应的latex字符串
                latex = text[frag_i].xpath(".//img//@alt")[0]
                text_process.append('_latex_:' + latex)
                frag_i += 1
                while(True):
                    if frag_i >= len(text):
                        break
                    if 'displaystyle' in text[frag_i]:
                        break
                    else:
                        frag_i += 1
                frag_i += 1
        return text_process

    paragraph = content.xpath("./p|./h2|./h3|./ul|./ol|./dl|./pre")
    passage = {'abstract':[]} # 整个文章所有文本，。维基百科的文本部分一开始默认是摘要
    sub_content = dict() # 保存每个子标题下的文本
    entities = [] # 保存所有实体
    sub_title = '' # 保存当前的子标题，一开始先是p标签，则视为摘要，后面出现一次h3则视为子标题，在下一次h3出现之前都视为该子标题下的内容
    for ei, i in enumerate(paragraph):
        tag = i.tag # 获得当前是什么标签
        text_process = []
        if tag in ['h2', 'h3']: # 说明当前是一个子标题
            sub_title = Traditional2Simplified(''.join(i.xpath(".//text()")).strip().replace("[编辑]", ""))
            continue
        if tag in ['p', 'ul', 'ol', 'dl']: # 夹在公式的文本
            text = i.xpath(".//text() | ./span[@class='mwe-math-element']")
            # print(text)
            text_process = process_text(text)
            entities += Traditional2Simplified(i.xpath(".//a/@title"))
            # print(text_process)
        if tag == 'pre': # 包含代码片段
            text_process = ['_code_:' + ''.join(i.xpath(".//text()"))]
        if sub_title == '': # 说明当前抽取的段落都属于摘要
            passage['abstract'].append(text_process)
        else: #说明当前属于某个子标题
            if len(text_process) == 0:
                continue
            if sub_title not in sub_content.keys():
                sub_content[sub_title] = []
            sub_content[sub_title].append(text_process)
    passage['paragraphs'] = sub_content
    passage['entities'] = set(entities)
    return passage

def process_html(content):
    content = etree.HTML(content) # lxml的etree类的HTML可以补全html标签，并生成python对象
    content = content.xpath("//div[@class='mw-parser-output']")[0]
    ##### 维基百科页面中的侧边栏中有一些结构化的表，table表的class="infobox"，可以直接取来作为结构化的数据，用于知识图谱
    infobox_know = extract_infobox(content)
    ##### 维基百科的每个内容最后一栏叫做相关条目（查，论，编）（如果存在的话）一般会列出与当前实体有关的其他实体。表头一般是整个大类，表格
    # 下面每一行左侧浅蓝色为一类，右侧罗列的是属于该类的相关实体，这个结构是天然的结构化图谱资源。
    navbox_know = extract_navbox(content)
    ##### 段落抽取
    passage = extract_paragraph(content)
    # print('infobox_know=', infobox_know)
    # print('navbox_know=', navbox_know)
    # print('passage=', passage)

    return infobox_know, navbox_know, passage

def read_files(orgin_page, save_path):
    # 读取所有处理的数据集
    if not os.path.isdir(orgin_page):
        raise Exception("请给出合法的目录")
    wiki_knowledge = []
    if os.path.exists(save_path + 'wiki_knowledge.npy'):
        # wiki_knowledge = (np.load('wiki_knowledge.npy')[()]).tolist()
        pass
    files = os.listdir(orgin_page)
    # files = ['快速排序.txt']
    num = 0
    for file in tqdm(files):
        if file[-4:] != '.txt':
            continue
        with open(orgin_page + file, 'r', encoding='utf-8') as fr:
            lines = fr.readlines()
        entity_title = Traditional2Simplified(lines[0][3:].replace('\n', ''))
        category_list = Traditional2Simplified(lines[1][3:].replace('\n', '').split('\t'))

        if filter(entity_title, category_list): # 如果实体标题或分类中包含一些过滤词，则不再处理当前文本
            continue
        url = lines[2][5:].replace('\n', '')
        time = lines[3][5:].replace('\n', '')
        content = ''.join(lines[5:]).replace('\n', '')
        infobox_know, navbox_know, passage = process_html(content)
        knowledge = dict()
        knowledge['entity'] = entity_title
        knowledge['category'] = category_list
        knowledge['url'] = url
        knowledge['time'] = time
        knowledge['structure_know'] = infobox_know # 维基百科中的infobox最终定义为该实体的结构化知识
        knowledge['corrseponding_know'] = navbox_know # 维基百科中的navbox最终定义与该实体有关的实体的结构化知识
        knowledge['smi-structure_know'] = passage # 维基百科中的段落被定位为该实体的半结构化知识
        wiki_knowledge.append(knowledge)
        num += 1
        if num%500 == 0: # 每隔一段时间保存一次防止中途报错而导致前面的数据丧失
            np.save(save_path + "wiki_knowledge.npy", wiki_knowledge)
    np.save(save_path + "wiki_knowledge.npy", wiki_knowledge)
    print("已完成处理所有维基百科知识，总数量为{}".format(len(wiki_knowledge)))

if __name__ == '__main__':
    orgin_page = './origin_page/'
    save_path = './process/'
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    read_files(orgin_page, save_path)
```

&emsp;&emsp;整个源程序开源在GitHub上，该源程序可能并非能够完全处理维基百科千变万化的标签结构（例如在后期我们发现爬取结构化的属性表时，当用table[@class="infobox"]）时无法爬取，查看后发现其标签会出现 \<table class="infobox xxx xxx"> （多个类），因此xpath路径应改为 “table[contains(@class, infobox)]” 。但基本可以满足绝大多数页面的处理。

&emsp;&emsp;本文爬取的语料包含结构化和半结构化数据。结构化数据可以直接作为知识图谱，也可以借助定义好的实体进行实体识别和消歧、远程监督关系抽取，同时半结构数据使用其运用到中文自然语言处理任务中，包括中文预训练、信息检索、问答系统、语义推理等。

&emsp;&emsp;
