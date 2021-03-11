## 本目录是爬虫的所有文件

[1] 需要安装相关的包，包括：
numpy
scrapy
tqdm
lxml

[2] 在queue.py中的candidates中加入你需要爬取的起始请求

[3] 在pycharm内，直接对main.py执行即可，在控制台则可以执行 python3 main.py。在爬取过程中可自行决定是否终止，也可等待程序自行终止。通常candidates队列很难被全部处理，所以建议不间断的人为监看，不要脱机爬虫；
