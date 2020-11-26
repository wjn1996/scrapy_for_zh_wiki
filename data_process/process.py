import numpy as np
import os
import random as rd
import json
from tqdm import tqdm
from lxml import etree
from langconv import *
from filter_words import filter_url

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