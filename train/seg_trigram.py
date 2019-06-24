# -*- coding: utf-8 -*-

import jieba, os, re
import logging
from tqdm import *

stopwordTxt = os.path.join('..', 'data', "StopWord.txt")
queryDictFile = os.path.join('..', 'data', 'dict.txt')

def trigram(li):
    grams = []
    for s in li:
        if len(s) > 3:
            grams += [s[i:i+3] for i in range(0,len(s), 3)]
            grams += [s[i:i+3] for i in range(1,len(s), 3)]
            grams += [s[i:i+3] for i in range(2,len(s), 3)]

def retain_chinese(line):
    return re.compile(r"[^\u4e00-\u9fa5 ]").sub('',line).replace('臺', '台')

def main():

    stop = open(stopwordTxt,"r")

    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

    # jieba custom setting.
#jieba.set_dictionary('jieba_dict/dict.txt.big')
    jieba.load_userdict(queryDictFile)

    # load stopwords set
    stopword_set = set(stop.read().split())
#    with open('jieba_dict/stopwords.txt','r', encoding='utf-8') as stopwords:
#        for stopword in stopwords:
#            stopword_set.add(stopword.strip('\n'))

    output = open('wiki_trigram_seg.txt', 'w', encoding='utf-8')
    with open('wiki_zh_tw.txt', 'r', encoding='utf-8') as content :
        for texts_num, line in enumerate(tqdm(content, total=341018)):
            sentences = retain_chinese(line.strip()).split()
            words = trigram(sentences)
            for word in words:
                if word not in stopword_set:
                    output.write(word + ' ')
            output.write('\n')

#            if (texts_num + 1) % 10000 == 0:
#                logging.info("已完成前 %d 行的斷詞" % (texts_num + 1))
    output.close()

if __name__ == '__main__':
    main()
