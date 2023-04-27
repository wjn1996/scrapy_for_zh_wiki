# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

# 定义实体类
class ContentItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    # 内容主题实体
    content_entity = scrapy.Field()
    # 分类
    category = scrapy.Field()
    # 获取时间
    time = scrapy.Field()
    # 链接地址
    url = scrapy.Field()
    # 百科内容页面（含有html标签）
    content = scrapy.Field()

