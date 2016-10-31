# -*- coding: UTF-8 -*-
import re
import os
import sys
import time
import json
import jieba
import threading
import hashlib
import logging
import datetime
from flask import Flask,request,abort
from textanalysis_thread import TextAnalysisThread 
from postgres_connection import * 
from multiprocessing import Manager

app = Flask(__name__)
word_list = []
dataid_dict = Manager().dict()

log_console = logging.StreamHandler(sys.stderr)
default_logger = logging.getLogger(__name__)
default_logger.setLevel(logging.DEBUG)
default_logger.addHandler(log_console)

stopword_set = set()
for line in open('stop_words.txt'):
    stopword_set.add(line[:-1].decode('utf8'))

nickname_dict = {}
#nickname_dict = postgres_conn()
#if(len(nickname_dict)<=0):
#    default_logger.debug("Got no nickname!")

for line in open('celebrity_nickname.txt'):
    lines = line.split(',')
    if len(lines) < 2:
       continue
    name = lines[0]
    jieba.add_word(name,100,'nr')
    tmp_nick = lines[1][:-1]
    for i in re.findall('\(.*?\)',tmp_nick):
        tmp_nick = tmp_nick.replace(i,'')
    tmp_nick = tmp_nick.replace(' ','').replace('/','|')
    nick_name = name+"|"+tmp_nick
    nickname_dict[name] = nick_name    

word_category_set = ('v','n','nr','a','d','g','i')

@app.route('/textanalysis/',methods=['POST'])
def index_app():
    #请求实体过大，默认10M
    default_logger.debug("#####################")
    default_logger.debug(request.content_length)
    if (request.content_length > 10*1024*1024):
        abort(413)
    data = request.json
    if not isinstance(data, list):
        abort(400)
    #以数据的md5值作为ID
    data_id = md5_encode(json.dumps(data))
    if (dataid_dict.has_key(data_id)):
        return json.dumps({"meta":{"txtId":data_id}},ensure_ascii=False)
    else:
        dataid_dict[data_id] = ""
        #调用线程异步处理文本 
        t = TextAnalysisThread(data, data_id, dataid_dict, stopword_set)
        t.start()
        return json.dumps({"meta":{"txtId":data_id}},ensure_ascii=False)

@app.route('/textanalysis/<dataid>',methods=['GET'])
def count_senti_app(dataid):
    filters = request.args.get('filter','')
    categories = request.args.get('categories','v,n,nr,a,d,g,i')
    limit = int(request.args.get('limit','30'))
    cate_list = categories.split(',')
    for cate in cate_list:
        if cate not in word_category_set:
            abort(400)
    if (dataid_dict.has_key(dataid)):
        if (dataid_dict.get(dataid) == ''):
            return json.dumps({"isReady":False,"meta":{"txtId":dataid},"sentiments":[],"counts":[]},ensure_ascii=False)
        update_ts(dataid_dict,dataid)
        json_str = dataid_dict.get(dataid)[1]
        json_dict = json.loads(json_str)
        analysis_list = json_dict['analysis']
        word_filter_list = word_filter(analysis_list,filters)
        word_category_list = word_category(word_filter_list,categories)
        word_dict = word_count(word_category_list)
        word_sort_list = word_sort(word_dict)
        word_limit_list = word_limit(word_sort_list, limit)
        senti_list = []
        for w in word_filter_list:
            senti_list.append({"id":w['id'],"rating":w['rating']})
        return json.dumps({"isReady":True,"meta":{"txtId":dataid},"sentiments":senti_list,"counts":word_limit_list},ensure_ascii=False)
    else:
        abort(404)

@app.route('/textanalysis/<dataid>/counts',methods=['GET'])
def count_app(dataid):
    filters = request.args.get('filter','')
    categories = request.args.get('categories','v,n,nr,a,d,g,i')
    limit = int(request.args.get('limit','30'))
    cate_list = categories.split(',')
    for cate in cate_list:
        if cate not in word_category_set:
            abort(400)
    if (dataid_dict.has_key(dataid)):
        if (dataid_dict.get(dataid) == ''):
            return json.dumps({"isReady":False,"meta":{"txtId":dataid},"counts":[]},ensure_ascii=False)
        update_ts(dataid_dict,dataid)
        json_str = dataid_dict.get(dataid)[1]
        json_dict = json.loads(json_str)
        analysis_list = json_dict['analysis']
        word_filter_list = word_filter(analysis_list,filters)
        word_category_list = word_category(word_filter_list,categories)
        word_dict = word_count(word_category_list)
        word_sort_list = word_sort(word_dict)
        word_limit_list = word_limit(word_sort_list, limit)
        return json.dumps({"isReady":True,"meta":{"txtId":dataid},"counts":word_limit_list},ensure_ascii=False)
    else:
        abort(404)

@app.route('/textanalysis/<dataid>/sentiments',methods=['GET'])
def sentiment_app(dataid):
    filters = request.args.get('filter','')
    model = request.args.get('model','commen')
    if (model != 'commen'):
        abort(400)
    if (dataid_dict.has_key(dataid)):
        if (dataid_dict.get(dataid) == ''):
            return json.dumps({"isReady":False,"meta":{"txtId":dataid},"sentiments":[]},ensure_ascii=False)
        update_ts(dataid_dict,dataid)
        json_str = dataid_dict.get(dataid)[1]
        json_dict = json.loads(json_str)
        analysis_list = json_dict['analysis']
        word_filter_list = word_filter(analysis_list,filters)
        senti_list = []
        for w in word_filter_list:
            senti_list.append({"id":w['id'],"rating":w['rating']})
        return json.dumps({"isReady":True,"meta":{"txtId":dataid},"sentiments":senti_list},ensure_ascii=False)
    else:
        abort(404)

def word_count(word_list):
    word_dict = {}
    for a in word_list:
        for w in a['words']:
            word = w['word']
            if word in word_dict:
                word_dict[word] += 1
            else:
                word_dict[word] = 1
    return word_dict

def word_sort(word_dict):
    word_sort_list = []
    sort_list = sorted(word_dict.iteritems(), key=lambda d:float(d[1]), reverse = True )
    for s in sort_list:
        word_sort_list.append({"word":s[0],"count":s[1]})
    return word_sort_list

def word_limit(word_sort_list,limit):
    word_limit_list = []
    num = 0
    for s in word_sort_list:
        num += 1
        if (num > limit):
            break
        word_limit_list.append(s)
    return word_limit_list

def word_filter(analysis_list,filters):
    default_logger.debug(filters)
    if (filters == ''):
        return analysis_list
    word_filter_list = []
    regex = 'search\(\'.*?\',s\)'
    for f in re.findall(regex,filters):
        ff = f[8:-4].encode('utf8')
        if not nickname_dict.has_key(ff):
            continue
        filters = filters.encode('utf8').replace(ff,nickname_dict.get(ff))
    default_logger.debug(filters)
    s = "this is a string to test if filter is correct or not. If not correct, abort 400."
    try:
        eval(filters)
    except:
        abort(400)
    for w in analysis_list:
        s = w['text'].encode('utf8')
        if eval(filters):
            word_filter_list.append(w)
    return word_filter_list

def word_category(word_filter_list,categories):
    if (categories == ''):
        return word_filter_list
    category_set = set(categories.split(","))
    for a in word_filter_list:
        new_list = []
        for w in a['words']:
            if w['category'] in category_set:
                new_list.append(w)
        a['words'] = new_list 
    return word_filter_list

def md5_encode(data):
    m5 = hashlib.md5()
    m5.update(data)
    data_md5 = m5.hexdigest()
    return data_md5

def update_ts(dataid_dict,dataid):
    ts = time.mktime(datetime.datetime.now().timetuple())
    dt = dataid_dict.get(dataid)[1]
    dataid_dict[dataid] = (ts, dt)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
