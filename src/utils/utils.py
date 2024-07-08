import conllu
import pymorphy2
import numpy as np
from typing import List, Dict, Optional, Union, Callable

from utils.constants import GRAMEVAL2PYMORPHY


def getcapital(s: str) -> List[int]:
    """
    Получение индексов с заглавными буквами
    """
    return [i for i, c in enumerate(s) if c.isupper()]


def capitalize_indexes(s: str, ind: List[int]) -> str:
    """
    Капитализация слова по списку индексов
    """
    split_s = list(s)
    for i in ind:
        if i < len(split_s):
            split_s[i] = split_s[i].upper()

    return "".join(split_s)


def capitalize_word(old_word: str, new_word: str) -> str:
    """
    Капитализация нового слова, основанная на предыдущей форме
    """
    if old_word.isupper():
        new_word = new_word.upper()
    elif old_word.islower():
        new_word = new_word.lower()
    else:
        uppercase_indexes = getcapital(old_word)
        new_word = capitalize_indexes(new_word, uppercase_indexes)

    return new_word


def tree_depth(tree: conllu.models.TokenTree) -> float:
    """
    compute the depth of an input syntax tree
    """
    depth = 0
    stack = [tree]
    while len(stack):
        curr_node = stack[0]
        stack.pop(0)
        if curr_node.children:
            depth += 1
        for node in range(len(curr_node.children) - 1, -1, -1):
            stack.insert(0, curr_node.children[node])
    return depth


def get_ipm_conllu(
    sentence: conllu.models.TokenList, freq_dict: Dict[str, float]
) -> float:
    lemmas = []
    for token in sentence:
        if token["upos"] != "PUNCT":
            lemmas.append(token["lemma"])

    return float(
        sum([True for w in lemmas if w in freq_dict and freq_dict[w] > 1]) / len(lemmas)
        if lemmas
        else 0
    )


def unify_alphabet(sentence: str) -> str:
    translation = sentence.maketrans(dict(zip("Ёё", "Ее")))
    sentence = sentence.translate(translation)
    return sentence


def are_infl_lex_feats_equal(
    tok1: conllu.Token, tok2: conllu.Token,
    feats=("Case", "Number", "Animacy", "Degree")
):
    # are_equal = True
    for feat in feats:
        tok1_feat = (tok1["feats"] or {}).get(feat, -1)
        tok2_feat = (tok2["feats"] or {}).get(feat, -1)

        if not (
            (tok1_feat == -1) or (tok2_feat == -1)
            or tok1_feat == tok2_feat
        ):
            return False
    return True


def get_constituent(
    head: conllu.Token, sentence: conllu.TokenList,
    exclude_this_tok_children: Callable[[conllu.Token], bool] = lambda tok, sent: False
) -> conllu.TokenList:
    """Find all descendants of the current node.

    This is almost (?) equal to constituents of constituency grammar"""
    # if not exclude_this_tok_children and head["deprel"] == "root":
    #     return conllu.TokenList([])

    direct_deps = sentence.filter(head=head["id"])
    constituent_toks = conllu.TokenList([head])

    for dep in direct_deps:
        # failsafe against strange markup
        if dep["deprel"] == "root":
            continue

        if not exclude_this_tok_children(dep, sentence):
            constituent_toks.extend(
                get_constituent(dep, sentence, exclude_this_tok_children))

    constituent_toks.sort(key=lambda token: token["id"])
    return constituent_toks


def make_bigrams(toks: List[conllu.Token]):
    bigrams = [(tok1["form"].lower(), tok2["form"].lower())
               for tok1, tok2 in zip(toks, toks[1:])
               if "PUNCT" not in (tok1["upos"], tok2["upos"])]
    return bigrams


def avg_bigram_freq(bigrams, bigrams_freq_dict):
    total = 0
    for bigram in bigrams:
        freq = bigrams_freq_dict.get(bigram, 0)
        total += freq

    return total / len(bigrams)


def get_dependencies(
    sentence: conllu.models.TokenList,
) -> Dict[str, List[conllu.models.Token]]:
    """
    Extract a list of dependencies for each token
    in the sentence
    """
    deprels = {}
    for i, token in enumerate(sentence, 1):
        if token["head"] not in deprels:
            deprels[token["head"]] = []
        deprels[token["head"]].append(token)
    return deprels


def get_pymorphy_parse(
    token: Union[conllu.models.Token, str],
    pos: Union[str, List[str]],
    morph: pymorphy2.MorphAnalyzer,
) -> Optional[pymorphy2.analyzer.Parse]:
    """
    Find the correct parse of the verb in pymorphy
    parse options
    """
    if isinstance(pos, str):
        pos = [pos]

    if isinstance(token, str):
        lemma = token
        form = token
        case = None

    else:
        lemma = token["lemma"]
        form = token["form"]
        case = token['feats'].get('Case') if token['feats'] is not None else None

    parse = list(
        filter(
            lambda x: x.tag.POS in pos and x.normal_form.lower() == lemma.lower(),
            morph.parse(form),
        )
    )
    if len(parse) == 0:
        return

    if (
        len(parse) > 1
        and any(p in pos for p in ["NOUN", "ADJF", "PRON"])
        and case
    ):
        parse = list(
            filter(
                lambda x: x.tag.case == GRAMEVAL2PYMORPHY[case],
                parse,
            )
        )

    return parse[0] if parse else None


def get_subject(
    token: conllu.models.Token,
    deprels: Dict[str, List[conllu.models.Token]],
    conj: List[conllu.models.Token],
) -> Dict[str, str]:
    # check subject of the verb in question
    subj = [t for t in deprels.get(token["id"], []) if t["deprel"].startswith("nsubj")]

    # check conjuncts
    if len(subj) == 0:
        subj = sum(
            [
                [t for t in deprels.get(c["id"], []) if t["deprel"].startswith("nsubj")]
                for c in conj
            ],
            [],
        )
    return subj


def get_closest(
    token: conllu.models.Token, tokens: List[conllu.models.Token]
) -> List[conllu.models.Token]:
    """
    Find the closest token (before) to a given one
    """
    diffs = []
    for t in tokens:
        diffs.append(token["id"] - t["id"])
    closest = np.argsort(diffs)
    closest = [tokens[i] for i in closest if diffs[i] >= 0]
    closest = closest[0] if len(closest) > 0 else None
    return closest


def get_conjuncts(
    token: conllu.models.Token,
    deprels: Dict[str, List[conllu.models.Token]],
    sentence: conllu.models.TokenList,
) -> List[Optional[conllu.models.Token]]:
    """
    Find token conjuncts with the same
    subject
    """
    conj = [t for t in deprels.get(token["id"], []) if t["deprel"] == "conj"]
    if token["deprel"] == "conj":
        conj += [
            t
            for t in sentence
            if (
                t["id"] == token["head"]
                or (t["head"] == token["head"] and t["deprel"] == "conj")
            )
        ]
    return conj


def filter_conjuncts(
    conj: List[Optional[conllu.models.Token]],
    token: conllu.models.Token,
    deprels: Dict[str, List[conllu.models.Token]],
) -> List[Optional[conllu.models.Token]]:
    """
    Find token conjuncts with the same
    subject
    """
    # check for matching subjects
    token_subj = [
        t["id"] for t in deprels.get(token["id"], []) if t["deprel"].startswith("nsubj")
    ]
    if token_subj:
        token_subj = token_subj[0]
    else:
        token_subj = None

    filtered_conj = []
    for c in conj:
        nsubjs = [
            t["id"] for t in deprels.get(c["id"], []) if t["deprel"].startswith("nsubj")
        ]
        if len(nsubjs) == 0:
            filtered_conj.append((c, None))
            continue
        if not token_subj:
            if any(subj < token["id"] for subj in nsubjs):
                filtered_conj.append((c, nsubjs[0]))
        else:
            if token_subj in nsubjs:
                filtered_conj.append((c, nsubjs[0]))

    with_subj = list(filter(lambda x: x[1] is not None, filtered_conj))
    with_subj = [s[0] for s in with_subj]

    if len(with_subj) > 0:
        closest_id = get_closest(token, with_subj)
        if closest_id is not None:
            closest_id = closest_id["id"]
            conj = [c[0] for c in filtered_conj if c[0]["id"] >= closest_id]
            return conj
    conj = [c[0] for c in filtered_conj]
    return conj

  
def get_morph_segmentation(word: str, morph_dict: Dict[str, str]):
    segmentation = {
        "PREF": [],
        "ROOT": [],
        "LINK": [],
        "HYPH": [],
        "SUFF": [],
        "POSTFIX": [],
        "END": [],
    }
    try:
        word = morph_dict[word]
        segments = re.findall("([а-яё]+:[A-Z]+)", word)
        for segment in segments:
            split_ = segment.split(":")
            segmentation[split_[1]].append(split_[0])
        return segmentation
    except KeyError:
        pass


def get_list_safe(idx: int, list_: list) -> list:
    try:
        return list_[idx]
    except IndexError:
        return []