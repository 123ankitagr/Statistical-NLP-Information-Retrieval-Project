__author__ = "Akshay Joshi, Ankit Agrawal"

import math
import sys
import os
import re
import numpy as np
from collections import defaultdict
from functools import reduce
from bm25_ranking import BM25Rank
from regex_tokenize import RegexTokenizer


dictionary = set()
postings = defaultdict(dict)
document_frequency = defaultdict(int)
length = defaultdict(float)

characters = " .,!#$%^&*();:\n\t\\\"?!{}[]<>``'`"

def populateDocumentEvidenceList(directory):
    doc_dictionary = {}
    for path, dirs, files in os.walk(directory):
        folders = path.split(os.sep)

            # Parse all the sub directories in the root directory
        for dir in dirs:
            inner_path = path + '/' + dir
            populateDocumentEvidenceList(inner_path)

            # Parse all the files in the directories list
        for i, file in enumerate(files):
            if file.endswith(".txt"):
                doc_dictionary[i] = path+'/'+file
    return doc_dictionary


def initialize_terms_and_postings(document_filenames):
    global dictionary, postings
    #document_filenames = populateDocumentEvidenceList("test")
    for id in document_filenames:
        f = open(document_filenames[id],'r')
        document = f.read()
        f.close()
        terms = tokenize(document)
        unique_terms = set(terms)
        dictionary = dictionary.union(unique_terms)
        for term in unique_terms:
            postings[term][id] = terms.count(term)

def tokenize(document):
    terms = document.lower().split()
    return [term.strip(characters) for term in terms]

def initialize_document_frequencies():
    global document_frequency
    for term in dictionary:
        document_frequency[term] = len(postings[term])

def initialize_lengths(document_filenames):
    global length
    #document_filenames = populateDocumentEvidenceList("test")
    for id in document_filenames:
        l = 0
        for term in dictionary:
            l += imp(term,id, N)**2
        length[id] = math.sqrt(l)

def imp(term,id, N):
    if id in postings[term]:
        return postings[term][id]*inverse_document_frequency(term, N)
    else:
        return 0.0

def inverse_document_frequency(term, N):
    if term in dictionary:
        return math.log(N/document_frequency[term],2)
    else:
        return 0.0

def intersection(sets):
    return reduce(set.union, [s for s in sets])

def similarity(query,id, N):
    similarity = 0.0
    for term in query:
        if term in dictionary:
            similarity += inverse_document_frequency(term, N) * imp(term, id, N)
    similarity = similarity / length[id]
    return similarity


def precisionAtK(document_filename, query_to_pattern_map):
    input_document = open(document_filename, "r")
    for line in input_document:
        for pattern in query_to_pattern_map:
            result = bool(re.findall(pattern, line, flags = re.IGNORECASE))
            if result == True:
                return True
    input_document.close()
    return False

def precisionAtK_BM25_sent(sent, query_to_pattern_map):
    for pattern in query_to_pattern_map:
        result = bool(re.findall(pattern, sent, flags=re.IGNORECASE))
        if result:
            return True
    return False

def patternExtraction(path):
    patterns = {}
    with open(path, "r") as file:
        content = file.readlines()
        for line in content:    
            tokens = line.split(' ', 1)
            if tokens[0] not in patterns:
                key = tokens[0]
                pattern = []
                pattern.append(tokens[1].replace('\n', ''))
                patterns[key] = pattern
            else:  
                (patterns[tokens[0]]).append(tokens[1].replace('\n', ''))
        #print(patterns)
    file.close()
    return patterns


def get_precision(scores, patterns_query, precise_docs_bm25):
    for (id, score) in scores:
        result = precisionAtK(id, patterns_query)
        if result == True:
            precise_docs_bm25.append(1)
    return precise_docs_bm25

def get_precision_sentences(top50_sents, patterns_query, rank_for_queries):
    i = 0
    for sent in top50_sents:
        i+=1
        result = precisionAtK_BM25_sent(sent, patterns_query)
        if result == True:
            rank_for_queries.append(i)
            break

    return rank_for_queries

def do_search(document_filenames, N, patterns):
    query_file = open("extracted_test_questions.txt", "r")
    mean_precision_results_list = []
    mean_precision_results_list_bm25 = []
    query_to_pattern = {}
    j = 1
    rank_for_queries = []
    for i, query in enumerate(query_file):
        precise_docs = []
        precise_docs_bm25 = []
        if not (i % 2) == 0:
            query_to_pattern[query] = patterns[str(j)]
            obj = RegexTokenizer()
            query2 = obj.get_tokens(query)
            j += 1
            relevant_document_ids = intersection([set(postings[term].keys()) for term in query2])
            scores = sorted([(id,similarity(query2, id, N)) for id in relevant_document_ids], key=lambda x: x[1],
                            reverse=True)[:50]
            scores_bm25 = sorted([(id, similarity(query2, id, N)) for id in relevant_document_ids], key=lambda x: x[1],
                            reverse=True)[:1000]

            top1000_filenames = []
            for id, score in scores_bm25:
                top1000_filenames.append(document_filenames[id])
            obj = BM25Rank()
            top50_docs = obj.get_doc_rank(query2, top1000_filenames)
            top50_sents = obj.get_sentence_rank(query2, top50_docs)

            precise_docs_bm25 = get_precision(top50_docs, query_to_pattern[query], precise_docs_bm25)
            rank_for_queries = get_precision_sentences(top50_sents, query_to_pattern[query], rank_for_queries)

            for (id, score) in scores:
                result = precisionAtK(document_filenames[id], query_to_pattern[query])
                if result == True:
                    precise_docs.append(1)
        mean_precision_results_list.append(len(precise_docs) / 50)
        mean_precision_results_list_bm25.append(len(precise_docs_bm25) / 50)
    mean_precision_results = (sum(mean_precision_results_list) / 100)
    mean_precision_results_bm25 = (sum(mean_precision_results_list_bm25) / 100)
    print(f"The Mean Precicion @ 50 is: {mean_precision_results}")
    print(f"The Mean Precicion @ 50 for BM25 is: {mean_precision_results_bm25}")
    query_file.close()
    mrr = 0
    for rank in rank_for_queries:
        mrr += float(1/rank)
    final_mrr = float(mrr/100)
    print(f"MRR for BM25 is: {final_mrr}")


# Driver code 
if __name__ == "__main__":
    document_evidence_path = "Extracted Docs"
    # document_evidence_path = "test"
    patterns_path = "patterns.txt"
    print("\n[INFO] Please be patient, building a massive postings list!")
    document_filenames = populateDocumentEvidenceList(document_evidence_path)
    N = len(document_filenames)
    initialize_terms_and_postings(document_filenames)
    initialize_document_frequencies()
    initialize_lengths(document_filenames)
    patterns = patternExtraction(patterns_path)
    do_search(document_filenames, N, patterns)
    