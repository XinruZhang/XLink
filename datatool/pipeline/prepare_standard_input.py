import datetime
import re
import time
import urllib
import traceback

from utils.entity import EntityHolder
from utils.dictionary import EntityDictionary


def get_id2title_from_ttl(ttl_path):
    inst_id = None
    inst_title = ""
    counter = 0
    id_to_title = dict()
    with open(ttl_path, "r", encoding="utf-8") as rf:
        for line in rf:
            counter += 1
            if counter < 20: continue
            if counter % 1000000 == 0:
                print(counter)
            line_inst_id = line.strip().split(">")[0][1:]
            if line_inst_id != inst_id:
                if inst_id is not None:
                    id_to_title[inst_id] = inst_title
                inst_id = line_inst_id
                inst_title = ""
            else:
                if "property:supplement" in line:
                    inst_title += "（" + line.strip().split("\"")[1].split("\"")[0] + "）"
                elif "rdfs:label" in line:
                    inst_title += line.strip().split("\"")[1].split("\"")[0]
    return id_to_title


def get_title_sub_title_from_full_title(full_title):
    st = re.split("[(（]", full_title)
    if full_title[-1] in [")", "）"] and len(st)>1:
        sub_title = st[-1][:-1]
        title = ""
        for t in st[:-1]:
            tmp_st = re.split("[）)]", t)
            if len(tmp_st) == 1:
                title += tmp_st[0]
            else:
                title += "（" + tmp_st[0] + "）" + tmp_st[-1]
        return title, sub_title
    else:
        return full_title, ""


def generate_standard_entity_id(entity_path, id_holder: EntityHolder, standard_id2title):
    entities_with_sub_title = 0
    with open(entity_path, "w", encoding="utf-8") as wf:
        for id in standard_id2title:
            full_title = standard_id2title.get(id)
            oid = id_holder.inst_label2id.get(full_title)
            if oid is not None:
                title = id_holder.inst_id2label[oid]
                sub_title = full_title[len(title):]
                if len(sub_title)>0:
                    entities_with_sub_title += 1
                    sub_title = sub_title[1:-1]
                else:
                    title, sub_title = get_title_sub_title_from_full_title(full_title)
                uri = id_holder.inst_id2uri[oid]
                wf.write("{}\t\t{}\t\t{}\t\t{}\n".format(title, sub_title, uri, id))


"""
Functions for refine original corpus.

Main Function:
    corpus_refine(source, corpus_path, refined_path)
Tool Functions:
    is_annotation_valid(annotated_text)
    is_corpus_line_valid(source, line)
"""
def is_annotation_valid(annotated_text):
    """
    判断标注的中文/英文百科文本是否有效
        1. `[[` 的数量是否等于 `]]` 的数量
        2. 不可存在嵌套情况，即 [[sasfdsa[[xxx]]asfsa|xxx]] 的情况
    :param annotated_text:
    :return: bool
    """
    text_len = len(annotated_text)
    left_num, index = 0, 0
    while index < text_len:
        if left_num < 0 or left_num > 1:
            return False
        char = annotated_text[index]
        if index+1 < text_len and char == '[' and annotated_text[index+1] == '[':
            index += 2
            left_num += 1
            continue
        if index+1 < text_len and char == ']' and annotated_text[index+1] == ']':
            index += 2
            left_num -= 1
            continue
        index += 1
    return True


def is_corpus_line_valid(source, line):
    line_arr = line.strip().split("\t\t")
    if source == 'bd' and len(line_arr) == 4 and is_annotation_valid(line_arr[3]): return True
    if source == 'wiki' and len(line_arr) == 3 and is_annotation_valid(line_arr[2]): return True


def corpus_refine(source, corpus_path, refined_path):
    """
    得到 corpus_path 中所有的有效数据, 并将其保存到 refined_path 中

    有效数据是指:
        1. 有 abstract/article
        2. abstract/article 的标注合法 (对于中文数据的处理要先把所有的空格去掉)
        3. 有对应的合法 instance id

    :param source: bd|wiki
    :param corpus_path: "./data/bd/raw_abstract.txt"
    :param refined_path: "./data/bd/refined_abstract.txt"
    :return: total, error_no
    """
    total = 0
    error_no = 0
    entity_dict = EntityDictionary.get_instance(source)

    start = int(time.time())
    last_update = start
    with open(corpus_path, "r", encoding='utf-8') as rf:
        with open(refined_path, 'w', encoding='utf-8') as wf:
            for line in rf:
                if source == 'bd':
                    line = ''.join(line.split(" "))
                total += 1
                curr_update = int(time.time())
                # noinspection PyBroadException
                try:
                    if total % 100000 == 0:
                        print("#{}, batch_time: {}, total_time: {}".format(
                            total,
                            str(datetime.timedelta(seconds=curr_update-last_update)),
                            str(datetime.timedelta(seconds=curr_update-start))
                        ))
                        last_update = curr_update

                    if not is_corpus_line_valid(source, line): continue

                    line_arr  = line.strip().split("\t\t")
                    title     = line_arr[0].strip()
                    sub_title = line_arr[1].strip()

                    full_title = title
                    if len(sub_title) > 1:
                        if source == "bd": full_title += "（" + sub_title[1:-1] + "）"
                        elif source == "wiki": full_title += "(" + sub_title[1:-1] + ")"

                    if source == 'bd':
                        url = line_arr[2][23:]
                        if entity_dict.get_entity_by_uri(url) is not None:
                            wf.write("{}\t\t{}\n".format(
                                entity_dict.get_entity_by_uri(url).get_id(),
                                line_arr[3].split('::;', 1)[1]))
                        elif entity_dict.get_entity_by_full_title(full_title) is not None:
                            wf.write("{}\t\t{}\n".format(
                                entity_dict.get_entity_by_full_title(full_title).get_id(),
                                line_arr[3].split('::;', 1)[1]))

                    if source == 'wiki':
                        if entity_dict.get_entity_by_full_title(full_title) is not None:
                            wf.write("{}\t\t{}\n".format(
                                entity_dict.get_entity_by_full_title(full_title).get_id(),
                                line_arr[2].split('::;', 1)[1]))
                except Exception:
                    error_no += 1
                    # print("Exception on line: {}".format(total))
                    # traceback.print_exc()
    print("Total processed: #{}, error lines: #{}, time: {}".format(total, error_no, str(datetime.timedelta(seconds=int(time.time())-start))))
    return total, error_no


"""
Functions for refine corpus annotations.

Main Function: 
    corpus_annotation_refine(source, refined_path, annotation_refined_path)
Tool Functions:
    refine_annotation_by_split(source, annotated_text)
"""
def refine_annotation_by_split(source, annotated_text):
    # id_holder = Entity.get_instance(source)
    entity_dict = EntityDictionary.get_instance(source)

    # "a[[a|b]]s[[d]]v"
    plain_text, refined_annotated_text, mention_list = "", "", list()
    split_segs = annotated_text.split("[[")
    if len(split_segs) < 2: return annotated_text, annotated_text, mention_list

    plain_text += split_segs[0]
    refined_annotated_text += split_segs[0]

    # "a" "a|b]]s" "d]]v"
    for seg_index in range(1, len(split_segs)):
        seg = split_segs[seg_index]
        seg_segs = seg.split("]]")
        annotated_item = seg_segs[0]
        split_annotation = annotated_item.split("|")

        is_plain, mention, instance_id = False, "", None
        if len(split_annotation) == 1:
            mention = annotated_item
            if source == 'bd':
                is_plain = True
            else:
                instance_ids = entity_dict._mention2entities.get(mention)
                if instance_ids is None or len(instance_ids)>1: is_plain = True
                else: instance_id = list(instance_ids.keys())[0]
        else:
            if source == 'wiki':
                title = split_annotation[0]
                mention = split_annotation[1]

                instance_ids = entity_dict._mention2entities.get(title)
                if instance_ids is None or len(instance_ids) > 1:
                    is_plain = True
                else:
                    instance_id = list(instance_ids.keys())[0]
            else:
                url = split_annotation[1]
                mention = split_annotation[0]
                url = urllib.parse.unquote(url)
                url = "/".join(url.split("/")[:3])
                entity = entity_dict.get_entity_by_uri(url)
                if entity is None: is_plain = True
                else:
                    instance_id = entity.get_id()

        if is_plain:
            refined_annotated_text += mention
        else:
            refined_annotated_text += "[[{}|{}]]".format(instance_id, mention)
            mention_list.append([mention, instance_id, len(plain_text)])
        plain_text += mention
        if len(seg_segs) > 1:
            plain_text += seg_segs[1]
            refined_annotated_text += seg_segs[1]

    return plain_text, refined_annotated_text, mention_list

def corpus_annotation_refine(source, refined_path, annotation_refined_path):
    with open(refined_path, 'r', encoding='utf-8') as rf:
        with open(annotation_refined_path, 'w', encoding='utf-8') as wf:
            line_no = 0
            start = int(time.time())
            last_time = start
            for line in rf:
                # noinspection PyBroadException
                try:
                    line_no += 1
                    if line_no % 100000 == 0:
                        curr_time = int(time.time())
                        print("line_num: %d, time_consume: %s, total_time: %s" %
                              (line_no, str(datetime.timedelta(seconds=curr_time-last_time)),
                               str(datetime.timedelta(seconds=curr_time-start))))
                        last_time = curr_time
                    instance_id, annotated_text = line.strip().split("\t\t")
                    plain_text, refined_annotated_text, mention_list = refine_annotation_by_split(source, annotated_text)
                    wf.write(instance_id + "\t\t" + refined_annotated_text.strip() + "\n")
                except Exception:
                    print("Unexpected line: %d" % line_no)
                    traceback.print_exc()
