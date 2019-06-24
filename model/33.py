#!/usr/bin/env python
# coding: utf-8

from tqdm import *
import numpy as np
import time, jieba, os, json, csv, re

from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer

from gensim import corpora
from gensim.models import Phrases
from gensim.models import Word2Vec

from scipy.sparse import csr_matrix

from bm25 import BM25Transformer
from logger import EpochLogger

queryFile = os.path.join('..', 'data', 'QS_1.csv')
stopwordFile = os.path.join('..', 'data', "StopWord.txt")
outputFile = os.path.join('..', 'submit', 'current.csv')
titleJson = os.path.join('..', 'data', "title.json")

cut_method = jieba.cut_for_search
tokenFile = os.path.join('..', 'tokens', 'search_dict_token.txt')
tokeyFile = os.path.join('..', 'tokens', 'search_dict_tokey.txt')

bitokenFile = os.path.join('..', 'tokens', 'bigram_token.txt')
bitokeyFile = os.path.join('..', 'tokens', 'bigram_tokey.txt')
tritokenFile = os.path.join('..', 'tokens', 'trigram_token.txt')
tritokeyFile = os.path.join('..', 'tokens', 'trigram_tokey.txt')

queryDictFile = os.path.join('..', 'data', 'dict.txt')

jieba.load_userdict(queryDictFile)

def retain_chinese(line):
    return re.compile(r"[^\u4e00-\u9fa5]").sub('', line).replace('臺', '台')

def get_screen_len(line):
    chlen = len(retain_chinese(line))
    return (len(line) - chlen) + chlen * 2

if __name__ == '__main__':

    stopwords = open(stopwordFile, 'r').read().split()
    queries = dict([row for row in csv.reader(open(queryFile, 'r'))][1:])
    titles = json.load(open(titleJson, "r"))

    trim = lambda f: [t.strip() for t in f if t.strip()]
    token = trim(open(tokenFile).read().split('\n'))#[:5000]#[:301]
    tokey = trim(open(tokeyFile).read().split('\n'))#[:5000]#[:301]
    bitoken = trim(open(bitokenFile).read().split('\n'))#[:5000]#[:301]
    #bitokey = trim(open(bitokeyFile).read().split('\n'))#[:5000]#[:301]
    tritoken = trim(open(tritokenFile).read().split('\n'))#[:5000]#[:301]
    #tritokey = trim(open(tritokeyFile).read().split('\n'))#[:5000]#[:301]

    # append title to doc
    print("""
appending title to document...
""")

    title_weight = 2

    for i, key in enumerate(tqdm(tokey)):
        title = retain_chinese(titles.get(key, '')).strip()
        if title and title != "Non":
            title_token = ' {}'.format(' '.join([w for w
                in cut_method(title) if w not in stopwords])) * title_weight
            token[i] += title_token
            #print('+= ' + title_token)

    # add n gram
    for i, bitok in enumerate(bitoken):
        token[i] += ' ' + bitok

    for i, tritok in enumerate(tritoken):
        token[i] += ' ' + tritok

    if len(token) != len(tokey):
        print('token len sould eq to tokey len')
        exit(0)

    bm25 = BM25Transformer()
    vectorizer = TfidfVectorizer()
    print("""
    building corpus vector space...
        """)

    doc_tf = vectorizer.fit_transform(tqdm(token))

    bm25.fit(doc_tf)
    doc_bm25 = bm25.transform(doc_tf)

    print('\ncorpus vector space - ok\n')

    docsTokens = [t.split() for t in token]

    print("loading model")
    model = Word2Vec.load(os.path.join("..", "train", "news_d200_e100.w2v"))
    print("loading model done")

    print("making document word vector")

    docWv = np.array([np.sum(model.wv[[t for t in docsTokens[i] if t in model.wv]], axis=0) \
                        for i in tqdm(range(len(docsTokens)))])

    scores = np.zeros((len(queries),len(docsTokens)))

    with open(outputFile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        headers = ['Query_Index'] + ['Rank_{:03d}'.format(i) for i in range(1, 301)]
        writer.writerow(headers)

        for idx, q_id in enumerate(tqdm(queries)):


            query = ' '.join([w for w in cut_method(queries[q_id].replace('臺', '台'))
                                if w not in stopwords])

            if '中國學生' in queries[q_id]:
                query += ' 陸生 中生 大陸 學生'
            if '證所' in queries[q_id]:
                query += ' 證交稅 證交'

            qryTokens = [tok for tok in query.split() if tok in model.wv]
            qryWv = np.sum(model.wv[qryTokens], axis=0)

            scores[idx] = model.wv.cosine_similarities(qryWv, docWv)

            stages = [20, 40, 60, 80, 100]

            init_bar = '[ stage 0/{} ] Query{}: {}'.format(len(stages), idx + 1, query)
            print(init_bar)
            qry_tf = vectorizer.transform([query])
            qry_bm25 = bm25.transform(qry_tf)

            sims = cosine_similarity(qry_bm25, doc_bm25)[0]
            sims += scores[idx]
            ranks = [(t, v) for (v, t) in zip(sims, tokey)]
            ranks.sort(key=lambda e: e[-1], reverse=True)

            for stage, fb_n in enumerate(stages):

                print("\033[F[ stage {}/{} ]".format(stage + 1, len(stages)))

                # relavance feedback stage 1
                qry_bm25 = qry_bm25 + \
                        np.sum(doc_bm25[tokey.index(ranks[i][0])] * 0.5 for i in range(fb_n))


                sims = cosine_similarity(qry_bm25, doc_bm25)[0]
                sims += scores[idx]
                ranks = [(t, v) for (v, t) in zip(sims, tokey)]
                ranks.sort(key=lambda e: e[-1], reverse=True)

            entry = [q_id] + [e[0] for e in ranks[:300]]
            writer.writerow(entry)

            print("\033[F" + ' ' * get_screen_len(init_bar))
            print("\033[F" * 3)
