# from datatool.pipeline import prepare_standard_input as prep_input
# from datatool.pipeline import extract_mention_anchors
# from datatool.pipeline import calculate_entity_embedding

# if __name__ == "__main__":
#     # text = '亚马逊公司是在1995年7月16日由杰夫·贝佐斯（[[bdi5819308|JeffBezos]]）成立的，一开始叫Cadabra。性质是基本的[[bdi8063866|网络书店]]。然而具有远见的贝佐斯看到了网络的潜力和特色，当实 体的大型书店提供20万本书时，网络书店能够提供比20万本书更多的选择给读者。::;贝佐斯将Cadabra以地球上孕育最多种生物的[[bdi1505302|亚马逊河]]重新命名，于1995年7月重新开张。该公司原于1994年在华盛顿州登记，1996年时改到德拉瓦州登记，并在1997年5月15日时股票上市。代码是AMZN，一股为18美元（截止2012年10月12日收市，股价为242.36美元）。'
#     # mention_anchor_list, plain_text = extract_mention_anchors.extract_mention_and_plain_text_from_annotated_doc(text)
#     # print(mention_anchor_list)
#     # print(plain_text)
    
#     # vector_map, num_words, num_dim = calculate_entity_embedding.read_binary_vectors('/mnt/sdd/zfw/xlink2020/bd/emb/result300/vectors_abstract', debug=True)

#     calculate_entity_embedding.calculate_embedding_with_abstract(corpus_path='/mnt/sdd/zfw/xlink2020/bd/standard_abstract.txt',
#                                                                  vector_path='/mnt/sdd/zfw/xlink2020/bd/emb/result300/vectors_word',
#                                                                  out_path='/mnt/sdd/zfw/xlink2020/bd/emb/result300/vectors_abstract')

import re

# 存在以下问题：https://baike.baidu.com/item/“总统”/412 和 https://baike.baidu.com/item/总统/412 是同一个页面
pattern = re.compile(r'item/%[Ee]2%80%9[Cc](.+?)%[Ee]2%80%9[Dd]/')

with open('/data/zfw/xlink/bd/bd_instance_ID.txt', 'r', encoding='utf-8') as fin:
    for line in fin:
        if not(pattern.search(line) is None):
            print(line)
