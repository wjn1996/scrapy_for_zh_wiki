# -*- coding: utf-8 -*-
import scrapy
from scrapy.selector import Selector
from items import ContentItem
from queue import Queue
import time
from langconv import *
from filter_words import filter_url

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
        # candidate_lists_ = search.xpath("//div[@id='bodyContent']//*[@id='mw-content-text' and not(@class='references') and not(@role='presentation')]//a/@href").extract()
        # candidate_lists = []
        # 百科页面有许多超链接是锚链接，需要过滤掉
        # for url in candidate_lists_:
        #     if '/wiki' in url and 'https://zh.wikipedia.org' not in url:
        #         if ':' not in url or (':' in url and 'Category:' in url):
        #             candidate_lists.append('https://zh.wikipedia.org' + url)

        # self.start_urls = self.urlQueue.candidates
        self.urlQueue.add_has_viewd(this_url)
        # self.urlQueue.add_candidates(candidate_lists)
        print('候选请求数=', len(self.urlQueue.candidates))
        print('已处理请求数=', len(self.urlQueue.has_viewd))
        self.urlQueue.save_has_viewd()
        # 将当前页面的信息保存下来
        # print(content_entity)
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

        # dir = '../origin_page/'
        # with open(dir + counselor_item['content_entity'] + '(' + counselor_item['time'] + ')' + '.txt', 'w', encoding='utf-8') as fw:
        #     fw.write('标题：\n' + counselor_item['content_entity'] + '\n')
        #     fw.write('原文地址：' + counselor_item['url'] + '\n')
        #     fw.write('爬取时间：' + counselor_item['time'] + '\n\n')
        #     fw.write(counselor_item['content'])
        #
        # # 处理完分类页面后，将所有可能的内容请求链接直接提交处理队列处理
        # for url in self.urlQueue.candidates:
        #     # print(url)
        #     if 'Category:' in url:
        #         # print(url)
        #         yield scrapy.Request(url, callback=self.parse_category, dont_filter=True)
        #     else:
        #         yield scrapy.Request(url, callback=self.parse_content, dont_filter=True)
