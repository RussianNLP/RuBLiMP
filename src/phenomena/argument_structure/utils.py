import conllu
import pymorphy2
import pandas as pd

from utils.utils import capitalize_word as simple_capitalization
from utils.utils import get_pymorphy_parse
from utils.constants import GRAMEVAL2PYMORPHY

from .constants import GRAMEVAL2RNC

from typing import Optional, List, Dict


def get_modifiers(
    token: conllu.models.Token, deprels: Dict[int, List[conllu.models.Token]]
) -> List[conllu.models.Token]:
    """
    Find all the token modifiers that
    agree with it
    """
    if token["id"] not in deprels:
        return

    mods = [
        x
        for x in deprels[token["id"]]
        if (
            (
                x["deprel"] in ["amod", "det", "nmod"]
                and x["feats"] is not None
                and "Case" in x["feats"]
            )
            or (x["deprel"] in ["flat:name"])
            or (
                x["upos"] == 'VERB'
                and x['feats'] is not None
                and x['feats'].get('VerbForm') != 'Part')
        )
    ]
    if len(mods) != 0:
        return mods


def get_verb_infl_feats(verb_parse: pymorphy2.analyzer.Parse) -> frozenset:
    """
    Get verb inflectional features: number, gender, person and tense
    """
    feats = []

    number = verb_parse.tag.number
    tense = verb_parse.tag.tense
    person = verb_parse.tag.person
    gender = verb_parse.tag.gender

    for feat in [number, tense, person, gender]:
        if feat is not None:
            feats.append(feat)
    return frozenset(feats)


def get_noun_inlf_feats(token: conllu.models.Token) -> frozenset:
    """
    Get noun inflectional features: number and case
    """
    feats = []

    number = token["feats"].get("Number")
    case = token["feats"].get("Case")

    for feat in [number, case]:
        if feat is not None:
            feats.append(GRAMEVAL2PYMORPHY.get(feat, feat.lower()))
    return frozenset(feats)


def capitalize_word(
    source_word: conllu.models.Token,
    target_word: str,
    target_upos: Optional[str] = None,
) -> str:
    """
    Capitalize target word while taking into account source word upos
    """
    if target_upos == "PROPN":
        return target_word.title()
    if source_word["upos"] == "PROPN" and source_word["id"] != 1:
        return target_word
    return simple_capitalization(source_word["form"], target_word)


def check_permutaility(
    source_word: conllu.models.Token, target_word: conllu.models.Token
) -> bool:
    """
    Check whether source word can be replaced by target word and vice versa
    without number and/or gender violation
    """
    if (
        "Gender" in source_word["feats"]
        and "Gender" in target_word["feats"]
        and "Number" in source_word["feats"]
        and "Number" in target_word["feats"]
        and source_word["feats"]["Gender"] == target_word["feats"]["Gender"]
        and source_word["feats"]["Number"] == target_word["feats"]["Number"]
    ):
        return True
    return


def inflect_word(
    source_word: pymorphy2.analyzer.Parse, target_features: frozenset
) -> Optional[str]:
    """
    Inflect word with the passed features
    Return str if such form exists else None
    """
    target_word = source_word.inflect(target_features)
    return target_word.word if target_word else None


def find_deprels(
    deprel: str, token_id: int, dependencies: List[conllu.models.Token]
) -> Optional[conllu.models.Token]:
    """
    Find all the token dependencies with a given relation
    """
    if token_id not in dependencies:
        return
    deprels = [t for t in dependencies[token_id] if t["deprel"] == deprel]
    return None if len(deprels) == 0 else deprels[0]


def check_verb(
    token: conllu.models.Token, morph: pymorphy2.MorphAnalyzer, allow_part: bool = False
) -> Optional[pymorphy2.analyzer.Parse]:
    """
    Check that a verb has all the required features for
    minimal pair generation
    """

    if token["upos"] != "VERB":
        return

    if token["feats"] is None:
        return

    if not allow_part and token["feats"].get("VerbForm") not in ["Fin", "Inf"]:
        return

    allowed_pos = ["VERB", "INFN"]
    if allow_part:
        allowed_pos += ["PRTF", "PRTS"]

    parse = get_pymorphy_parse(token, allowed_pos, morph)
    if not parse:
        return

    if not allow_part:
        transitivity = parse.tag.transitivity
        if transitivity != "tran":
            return

    return parse


def get_verbs_rnc(
    vocab: pd.DataFrame, source_word: conllu.models.Token
) -> pd.DataFrame:
    """
    Extract only the nouns with the same gender as a source word from the vocabulary
    """
    filtered_vocab = vocab[
        (vocab["aspect"] == GRAMEVAL2RNC[source_word["feats"]["Aspect"]])
        & (abs(vocab["len"] - len(source_word["lemma"])) < 3)
    ]
    return filtered_vocab


def get_inan_nouns_rnc(
    vocab: pd.DataFrame, source_word: conllu.models.Token
) -> pd.DataFrame:
    """
    Extract only the nouns with the same gender as a source word from the vocabulary
    """
    filtered_vocab = vocab[
        (vocab["gender"] == source_word["feats"]["Gender"][0].lower())
        & (abs(vocab["len"] - len(source_word["lemma"])) < 3)
    ]
    return filtered_vocab
