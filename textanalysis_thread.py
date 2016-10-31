# -*- coding: UTF-8 -*-
import threading
import json
import jieba.posseg
import datetime
import time
import logging
import sys
from decimal import getcontext, Decimal
from snownlp import SnowNLP

log_console = logging.StreamHandler(sys.stderr)
default_logger = logging.getLogger(__name__)
default_logger.setLevel(logging.DEBUG)
default_logger.addHandler(log_console)

class TextAnalysisThread(threading.Thread):
    def __init__(self, data, data_id, dataid_dict, stopword_set):
        threading.Thread.__init__(self)
        self.data = data
        self.data_id = data_id
        self.word_list = []
        self.dataid_dict = dataid_dict
        self.stopword_set = stopword_set   
 
    def run(self):
        try:
            default_logger.debug("Text analysis thread starts...")
            size = len(self.data)
            num = 0
            for dt in self.data:
                #num += 1
                #status = Decimal(str(float(num)/float(size))).quantize(Decimal('0.00'))*100
                #default_logger.debug("Progress is "+str(status)+"%")
                tid = dt['id']
                text = dt['text']
                #文本的情感分析
                sentiment = SnowNLP(text).sentiments
                #文本的分词
                cut_list = jieba.posseg.cut(text)
                word_cate_list = []
                for c in cut_list:
                    if c.word in self.stopword_set:
                        continue
                    word_cate_list.append({"word":c.word,"category":c.flag})
                self.word_list.append({"id":tid, "text":text, "rating":sentiment, "words":word_cate_list}) 

            result_dict = {"txtId":self.data_id, "analysis":self.word_list}
            result_json = json.dumps(result_dict)
            #default_logger.debug("Add timestamp and json result into dictionary.")
            ts = time.mktime(datetime.datetime.now().timetuple())
            if (len(self.dataid_dict)<100):
                self.dataid_dict[self.data_id] = (ts, result_json)
            else:
                dataid_sort_list = sorted(self.dataid_dict.iteritems(), key=lambda d:float(d[1][0]), reverse = False )
                dataid_min_time = dataid_sort_list[0][0]
                tmp = self.dataid_dict.pop(dataid_min_time)
                self.dataid_dict[self.data_id] = (ts, result_json)
            default_logger.debug("Text analysis thread finish...")
        except:
            self.dataid_dict.pop(self.data_id)
            default_logger.debug("Oh no! Some except occurs in text analysis thread!")
