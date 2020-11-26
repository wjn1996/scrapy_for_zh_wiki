# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import re



class WikiPipeline(object):
    def process_item(self, item, spider):
        data = dict(item)
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