import psycopg2
import logging
import sys
import re
import jieba

log_console = logging.StreamHandler(sys.stderr)
default_logger = logging.getLogger(__name__)
default_logger.setLevel(logging.DEBUG)
default_logger.addHandler(log_console)

def postgres_conn():
    nickname_dict = {} 
    try:  
        #conn = psycopg2.connect("dbname='program' host='172.16.0.116' user='postgres' password='postgres'")
        conn = psycopg2.connect("dbname='program' host='data.zintow.com' user='postgres' password='postgres'")
        default_logger.debug('Conntect postgre database succeeded!') 
        
        cur = conn.cursor() 
        cur.execute("""select name,chi_name from celebrity where chi_name is not null and name is not null;""")
        rows = cur.fetchall()
        for row in rows:
            name = row[0]
            jieba.add_word(name,100,'nr')
            tmp_nick = row[1]
            for i in re.findall('\(.*?\)',tmp_nick):
                tmp_nick = tmp_nick.replace(i,'')
            tmp_nick = tmp_nick.replace(' ','').replace('/','|')          
            nick_name = name+"|"+tmp_nick
            nickname_dict[name] = nick_name
        default_logger.debug('Got name and nickname of celebrity')
        return nickname_dict
    except Exception, e:  
        default_logger.debug('Failed to read data from postgrea '+e.args[0])
        return nickname_dict

if __name__ == '__main__':
    postgres_conn() 
