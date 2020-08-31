import datetime
import time

from utils.dictionary import EntityDictionary


def extract_mention_and_plain_text_from_annotated_doc(document):
    """
    从标准标注数据得到 mention_anchor 列表和 plain_text, for example:

    document = "《海鸥》是网剧《[[bdi1697355|南北兄弟]]》插曲，由[[bdi7840364|顾峰]]、清源作词，顾峰作曲，[[bdi2647186|孟瑞]]演唱"

    mention_anchor = [['南北兄弟', 'bdi1697355', 8],
                      ['顾峰', 'bdi7840364', 17],
                      ['孟瑞', 'bdi2647186', 30]],
    plain_text = "《海鸥》是网剧《南北兄弟》插曲，由顾峰、清源作词，顾峰作曲，孟瑞演唱"

    :param document: string
    :return: list(), string
    """
    plain_text = ""
    mention_anchor_list = []

    split_segs = document.split("[[")
    if len(split_segs) < 2:
        return mention_anchor_list, document

    plain_text += split_segs[0]

    for seg_index in range(1, len(split_segs)):
        seg = split_segs[seg_index]
        seg_segs = seg.split("]]")
        instance_id, mention = seg_segs[0].split("|")

        mention_anchor_list.append([mention, instance_id, len(plain_text)])
        plain_text += mention

        if len(seg_segs) > 1:
            plain_text += seg_segs[1]

    return mention_anchor_list, plain_text


def extract_mention_and_out_links_from_corpus(corpus_path):
    """
        只得到 mention_anchors 和 out_links，不需要同步生成 train_text
        由于中文 train_text 的生成需要分词，分词很耗时，可以先用这个函数生成一份 mention_anchors 和 out_links

    :param corpus_path:
    :return:
    """
    mention_anchors = dict()
    out_links = dict()

    counter, mode_cnt = 0, 1000000
    start_time = int(time.time())
    last_update = start_time
    print("Extracting mention anchors and out links from corpus: \n\t{}".format(corpus_path))
    with open(corpus_path, "r", encoding="utf-8") as rf:
        for line in rf:
            counter += 1
            if counter % mode_cnt == 0:
                curr_update = int(time.time())
                print("\t#{}, batch_time: {}, total_time: {}".format(
                    counter,
                    str(datetime.timedelta(seconds=curr_update-last_update)),
                    str(datetime.timedelta(seconds=curr_update-start_time))
                ))
                last_update = curr_update
            try:
                instance_id, document = line.strip().split("\t\t")
                mention_anchor_list, _ = extract_mention_and_plain_text_from_annotated_doc(document)
                if out_links.get(instance_id) is None:
                    out_links[instance_id] = set()
                for mention, anchor, offset in mention_anchor_list:
                    mention = mention.lower()
                    if mention_anchors.get(mention) is None:
                        mention_anchors[mention] = dict()
                    if mention_anchors[mention].get(anchor) is None:
                        mention_anchors[mention][anchor] = 0
                    mention_anchors[mention][anchor] += 1
                    out_links[instance_id].add(anchor)
            except Exception as e:
                print(counter, e)
    ol = dict()
    for i in out_links:
        if len(out_links[i]) > 0:
            ol[i] = list(out_links[i])
    print("Extracted, total mentions: #{}, total time: {}".format(
        len(mention_anchors), str(datetime.timedelta(seconds=int(time.time())-start_time))))
    return mention_anchors, ol

def merge_mention_anchors(mention_anchors_list):
    """
        把多源的 mention_anchors 合并起来，例如合并分别从 abstract, article, infobox 中抽取的 mention_anchors

    :param mention_anchors_list:
    :return:
    """
    print("\nMerging mention anchors from {} sources".format(len(mention_anchors_list)))
    start_at = int(time.time())
    ma = dict()
    for mention_anchors in mention_anchors_list:
        for mention in mention_anchors:
            if len(mention) <= 1: continue
            if ma.get(mention) is None:
                ma[mention] = dict()
            for anchor in mention_anchors[mention]:
                if ma[mention].get(anchor) is None:
                    ma[mention][anchor] = 0
                ma[mention][anchor] += mention_anchors[mention][anchor]
    print("Merged, mentions: #{}, time: {}".format(
        len(ma), str(datetime.timedelta(seconds=int(time.time())-start_at))))
    return ma

def merge_out_links(out_links_list):
    """
        把多源的 out_links 合并起来，例如合并分别从 abstract, article, infobox 中抽取的 out_links

    :param out_links_list:
    :return:
    """
    print("\nMerging out links from {} sources".format(len(out_links_list)))
    start_at = int(time.time())
    ol = dict()
    for out_links in out_links_list:
        for inst in out_links:
            if len(out_links[inst]) > 0:
                if ol.get(inst) is None:
                    ol[inst] = set()
                for out_inst in out_links[inst]:
                    ol[inst].add(out_inst)
    for i in ol:
        if len(ol[i]) > 0:
            ol[i] = list(ol[i])
    print("Merged, out_links: #{}, time: {}".format(
        len(ol), str(datetime.timedelta(seconds=int(time.time()) - start_at))))
    return ol

def expand_mention_anchors(source, mention_anchors):
    """
    从 mention_anchor.json 扩充词典
        a. 将满足以下条件的实体加入到全文统计的实体中，出现次数记为 1
            - 其 title 与 mention-anchor 字典中的某一 mention 相同
            - 该实体从未在语料中以 title 作为 mention 出现过
        b. 对于 title 没有作为 mention 出现过的实体
            - 以 title 作为 mention 构造 title-entity 字典

    :param source: string
    :param mention_anchors: dict
    :return: (dict, dict)
    """
    entity_dict = EntityDictionary.get_instance(source)

    title_entities = dict()

    print("\nExpanding mention anchors from entity dictionary...")
    start_at = int(time.time())
    for instance_id in entity_dict.entity_dict:
        mention = entity_dict.get_entity_by_id(instance_id).get_mention()
        if mention_anchors.get(mention) is not None:
            if mention_anchors[mention].get(instance_id) is None:
                mention_anchors[mention][instance_id] = 1
        else:
            title_entities[mention] = instance_id
    print("Expanded, title entities: #{}, mentions: #{}, time: {}".format(
        len(title_entities), len(mention_anchors), str(datetime.timedelta(seconds=int(time.time())-start_at))))
    return title_entities


def filter_mention_anchors(mention_anchors, link_m, freq_m, link_prob_th) -> dict:
    """
    1. filter out len(m) < 1
    2. expand mention_anchors from entity dictionary
    3. filter out link(m) < 2
    4. filter out link_prob(m) < 0.0001
    :param mention_anchors:
    :return:
    """
    ma = dict()
    for m in mention_anchors:
        if len(m) > 1:
            ma[m] = mention_anchors[m]
    nma = dict()
    for m in ma:
        if m == '__all__': continue
        if link_m.get(m) is None or freq_m.get(m) is None or link_m[m] < 2: continue
        if (float)(link_m[m]/freq_m[m]) < link_prob_th: continue
        nma[m] = ma[m]
    return nma