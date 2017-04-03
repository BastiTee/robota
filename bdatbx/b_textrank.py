#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
#trump-sample-article.bdatbx
# http://bdewilde.github.io/blog/2014/09/23/intro-to-automatic-keyphrase-extraction/
#

def get_stopwords_for_language(language):
    from bdatbx import b_util
    from bptbx import b_iotools
    import nltk
    stop_words = nltk.corpus.stopwords.words(language)
    path = b_util.load_resource_file('stopwords_{}_add.txt'.format(language))
    new_stopwords = b_iotools.read_file_to_list(path)
    b_util.log('Will add {} stopwords from {} to {} stopword list'.format(
        len(new_stopwords), path, language))
    stop_words = set(stop_words + new_stopwords)
    return stop_words


def score_terms_by_textrank(text, n_keywords=0.05):
    from itertools import takewhile, tee
    import nltk
    import itertools, networkx, nltk, string
    from re import match
    from nltk.stem.snowball import SnowballStemmer

    stop_words = get_stopwords_for_language('german')
    stemmer = SnowballStemmer('german', ignore_stopwords=False)
    stop_words = set([stemmer.stem(stop_word) for stop_word in stop_words])

    good_tags=set(['JJ','JJR','JJS','NN','NNP','NNS','NNPS'])
    base2org = {}

    print('tokenize')
    words = []
    inwords = []
    for sentence in nltk.sent_tokenize(text):
        pps = []
        for word in nltk.tokenize.WordPunctTokenizer().tokenize(sentence):
            regex = '[a-zA-ZäöüÄÖÜß0-9]+'  # at least one of those must appear
            if not match(regex, word):
                continue
            org_word = word
            word = stemmer.stem(word)
            try:
                base2org[word]
            except KeyError:
                base2org[word] = {}
            try:
                base2org[word][org_word] += 1
            except KeyError:
                base2org[word][org_word] = 1
            pps.append(word)
            words.append(word)
        inwords.append(pps)
    print('tag words')

    # tokenize and POS-tag words
    tagged_words = itertools.chain.from_iterable(
        nltk.pos_tag_sents(inwords))
    # filter on certain POS tags and lowercase all words
    # candidates = [word.lower() for word, tag in tagged_words
    #               if tag in good_tags and word.lower() not in stop_words
    #               and not all(char in punct for char in word)]

    candidates = [word for word, tag in tagged_words
                  if tag in good_tags and word not in stop_words]

    print('calc keywords')

    # build graph, each node is a unique candidate
    graph = networkx.Graph()
    graph.add_nodes_from(set(candidates))
    # iterate over word-pairs, add unweighted edges into graph
    def pairwise(iterable):
        """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)
    for w1, w2 in pairwise(candidates):
        if w2:
            graph.add_edge(*sorted([w1, w2]))
    # score nodes using default pagerank algorithm, sort by score, keep top n_keywords
    ranks = networkx.pagerank(graph)
    if 0 < n_keywords < 1:
        n_keywords = int(round(len(candidates) * n_keywords))
    word_ranks = {word_rank[0]: word_rank[1]
                  for word_rank in sorted(ranks.items(), key=lambda x: x[1], reverse=True)[:n_keywords]}
    keywords = set(word_ranks.keys())
    # merge keywords into keyphrases
    keyphrases = {}
    j = 0
    for i, word in enumerate(words):
        if i < j:
            continue
        if word in keywords:
            kp_words = list(takewhile(lambda x: x in keywords, words[i:i+10]))
            avg_pagerank = sum(word_ranks[w] for w in kp_words) / float(len(kp_words))
            keyphrases[' '.join(kp_words)] = avg_pagerank
            # counter as hackish way to ensure merged keyphrases are non-overlapping
            j = i + len(kp_words)

    print('postprocess')

    # replace phrases with most common orgiginal
    keyphrases_original = {}
    for keyphrase in keyphrases:
        import operator
        new_keyphrase = []
        for subphrase in keyphrase.split(' '):
            org_dict = base2org[subphrase]
            org_dict = sorted(
                org_dict.items(), key=operator.itemgetter(1), reverse=True)
            org_subphrase = org_dict[0][0]
            new_keyphrase.append(org_subphrase)
        new_keyphrase = ' '.join(new_keyphrase)
        keyphrases_original[new_keyphrase] = keyphrases[keyphrase]
    # keyphrases_original = keyphrases

    return sorted(keyphrases_original.items(), key=lambda x: x[1], reverse=True)

if __name__ == '__main__':
    import nltk
    from bptbx.b_iotools import read_file_to_list
    from os import path

    nltk.data.path.append('nltk-data')

    text = ' '.join(read_file_to_list(path.join(
    'bdatbx_test/resource/trump-sample-article.bdatbx')))

    terms = score_terms_by_textrank(text)
    i = 0
    for term, rank in terms:
        print('{} >> {}'.format(term, rank))
        i += 1
        if i == 15:
            break
