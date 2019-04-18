import json
import re
import codecs

PATH_TO_COREF = "../../rucoref/"
PATH_TO_TEXTS = "rucoref_texts/"
DOCS = "Documents.txt"
GROUPS = "Groups.txt"
TOKENS = "Tokens.txt"
GROUPS_XML = "groups.xml"
NOUN_STRING = "str:noun"

class Word:

    def __init__(self, ind, val):
        self.Value = val
        self.Index = ind


class Sign:

    def __init__(self, ind, val):
        self.Value = val
        self.Index = ind


class Sentence:

    def __init__(self, id_num, ind, sign, wds, sn):
        self.Id = id_num
        self.Index = ind
        self.Sign = sign
        self.Words = wds
        self.Signs = sn


class RelWord:

    def __init__(self, sId, wId):
        self.SentIndex = sId
        self.WordIndex = wId


class RelationPart:

    def __init__(self, iwg, wds, ids, ia):
        self.IdWordGroup = iwg
        self.Words = wds
        self.IsDirectSpeech = ids
        self.IsAnaphor = ia


class Relation:

    def __init__(self, head, ps):
        self.RelationHead = head
        self.RelationParts = ps


def toJSON(obj):
    return obj.__dict__


if __name__ == '__main__':
    # 1. read documents.txt with doc_ids and relative paths to texts
    # 2. read tokens and get information: sentences -> words and signs
    # 3. read groups.txt and fill another gaps (references)

    f = open(PATH_TO_COREF + DOCS, 'r', encoding='utf-8')
    documents_info = f.readlines()

    list_of_texts = []
    first = 1
    for x in documents_info:
        if first == 1:
            first = 0
        else:
            content = x.split()
            # important to us for now: text id (and relative path to it)
            list_of_texts.append(content[:2])

    text_id_map = {}
    num = 0
    for x in list_of_texts:
        int_index = 0
        text_id_map[x[0]] = num
        num = num + 1

    text_and_sentences = {}
    word_in_documents = {}
    shift_to_word = {}
    first = 1
    doc_id = -1
    word_index = 1
    sent_index = 1
    sentences = []
    words = []
    signs = []
    with open(PATH_TO_COREF + TOKENS, 'r', encoding='utf-8') as f:
        for line in f:
            if first == 1:
                first = 0
            else:
                tmp = line.split()
                cur_doc_id = tmp[0]
                cur_token_shift = tmp[1]  #
                cur_token_len = tmp[2]  # NOT USED, shift is enough
                cur_token_value = tmp[3]
                cur_token_gram = tmp[5]  # lemma skipped, gram -> for SENT check
                if cur_doc_id != doc_id:
                    word_index = 1
                    sent_index = 1
                    text_and_sentences[doc_id] = sentences
                    sentences = []
                    word_in_documents[doc_id] = shift_to_word
                    shift_to_word = {}

                doc_id = cur_doc_id
                if cur_token_gram == 'SENT':
                    signs.append(Sign(word_index, cur_token_value))
                    shift_to_word[cur_token_shift] = Word(sent_index, word_index)  # kostyli!!!
                    sentences.append(Sentence(0, sent_index, cur_token_value, words, signs))
                    words = []
                    signs = []
                    sent_index = sent_index + 1
                    word_index = 1
                else:
                    reg_a = u'[a-zA-Zа-яА-Я0-9]'  # use regexp to find signs
                    if not re.search(reg_a, cur_token_value):
                        signs.append(Sign(word_index, cur_token_value))
                        shift_to_word[cur_token_shift] = Word(sent_index, word_index)  # kostyli!!!
                    else:
                        words.append(Word(word_index, cur_token_value))
                        shift_to_word[cur_token_shift] = Word(sent_index, word_index)
                        word_index = word_index + 1

    anaphora_info = {}
    relation_parts = {}
    relation_heads = {}
    head_to_document = {}
    group_head = {}
    group_queue = []
    first = 1

    with open(PATH_TO_COREF + GROUPS, 'r', encoding='utf-8') as f:
        for line in f:
            if first == 1:  # skip the line with description
                first = 0
            else:
                tmp = line.split('	')
                cur_doc_id = tmp[0]
                cur_group_id = tmp[2]
                cur_chain_id = tmp[3]  # NOT USED
                cur_link = tmp[4]
                cur_shift = tmp[5]
                cur_length = tmp[6]  # NOT USED
                cur_content = tmp[7]  # NOT USED
                cur_tk_shifts = tmp[8]  # shifts of all words in anaphora
                if tmp.__len__() > 9:  # because group can include only one word (bug?)
                    cur_attributes = tmp[9]  # NOT USED
                if tmp.__len__() > 10:
                    cur_head = tmp[10]  # head of group (value) NOT USED
                if tmp.__len__() > 11:
                    cur_hd_shifts = tmp[11]  # shift of head of group NOT USED

                anaphora_info[cur_group_id] = tmp
                if cur_attributes:
                    if cur_link == '0':  # relation head
                        relation_parts[cur_group_id] = []
                        group_head[cur_group_id] = cur_group_id
                        ws = []  # words in head
                        words_shifts = cur_tk_shifts.split(',')
                        for sh in words_shifts:
                            ws.append(word_in_documents[cur_doc_id][sh])

                        relation_heads[cur_group_id] = RelationPart(0, ws, 'false', 'false')  # todo
                        head_to_document[cur_group_id] = cur_doc_id
                    else:
                        for q in group_queue:  # bug in Groups.txt: reference head can be defined later than ref part
                            if group_head.get(q[4]):
                                head_id = group_head[q[4]]
                                ws = []  # words in relation part
                                words_shifts = q[8].split(',')
                                for sh in words_shifts:
                                    ws.append(word_in_documents[q[0]][sh])

                                isAnaphoraFlag = 'false'
                                if NOUN_STRING not in cur_attributes and NOUN_STRING not in anaphora_info[head_id][9]:
                                    isAnaphoraFlag = 'true'
                                relation_parts[head_id].append(RelationPart(0, ws, 'false', isAnaphoraFlag))  # todo isDirectSpeechFlag
                                group_head[q[2]] = head_id
                                group_queue.remove(q)

                        if not group_head.get(cur_link):
                            group_queue.append(tmp)
                        else:
                            head_id = group_head[cur_link]
                            ws = []  # words in relation part
                            words_shifts = cur_tk_shifts.split(',')
                            for sh in words_shifts:
                                ws.append(word_in_documents[cur_doc_id][sh])

                            isAnaphoraFlag = 'false'
                            if NOUN_STRING not in cur_attributes and NOUN_STRING not in anaphora_info[head_id][9]:
                                isAnaphoraFlag = 'true'
                            relation_parts[head_id].append(RelationPart(0, ws, 'false', isAnaphoraFlag))  # todo isDirectSpeechFlag
                            group_head[cur_group_id] = head_id

    relation_info = {}  # doc_id -> relation_info
    for doc in list_of_texts:
        relation_info[doc[0]] = []

    for head, doc_id in head_to_document.items():
        relation_info[doc_id].append(Relation(relation_heads[head], relation_parts[head]))

    #  todo visualization

    for doc in list_of_texts:
        with codecs.open('_{}'.format(doc[0] + '.json'), 'w', encoding="utf-8") as fp:
            print("try to make json for file " + doc[0])
            fp.write('"docInfo:"')
            json.dump(text_and_sentences[doc[0]], default=toJSON, fp=fp, ensure_ascii=False)
            fp.write(',"relInfo:"')
            json.dump(relation_info[doc[0]], default=toJSON, fp=fp, ensure_ascii=False)
