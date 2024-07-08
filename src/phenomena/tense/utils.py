import conllu
import random
import numpy as np
from copy import deepcopy
from phenomena.min_pair_generator import MinPairGenerator
from utils.constants import GRAMEVAL2PYMORPHY

from typing import List, Dict, Any, Optional
from utils.utils import get_subject


UD2PYMORPHY = {
    # tense
    "Fut": "futr",
    "Past": "past",
    "Masc": "masc",
    # gender
    "Fem": "femn",
    "Neut": "neut",
    # number
    "Sing": "sing",
    "Plur": "plur",
    # person
    "1": "1per",
    "2": "2per",
    "3": "3per",
    # mood
    "Imp": "impr",
    "Ind": "indc",
    # aspect
    "Perf": "perf",
    "Imp": "impf",
    # animacy
    "Anim": "anim",
    "Inan": "inan",
}
UD2PYMORPHY.update(GRAMEVAL2PYMORPHY)


def ud2pymorphy(features: Dict[str, str]) -> Dict[str, str]:
    """
    Convert UD annotation to pymorphy
    """
    new_features = deepcopy(features)
    for feat, val in features.items():
        new_features[feat] = UD2PYMORPHY[val]

    return new_features


def get_verb_features(
    token: conllu.models.Token,
    deprels: Dict[str, List[conllu.models.Token]],
    conj: List[conllu.models.Token],
) -> Dict[str, str]:
    """
    Extract main verb features for agreement
    Check the subject for those features that are not
    present in the current verb form (e.g. gender in future tense)
    """
    feature_names = ["Person", "Number", "Gender"]

    # get verb features
    feats = deepcopy(token.get("feats"))
    if not feats:
        feats = {}
    else:
        feats = {
            key: feats.get(key, None) for key in feature_names if feats.get(key, None)
        }

    # check if all required features are found
    not_known = [x for x in feature_names if x not in feats]
    if len(not_known) == 0:
        return

    # find the closest subject
    subj = get_subject(token, deprels, conj)

    if len(subj) != 0:
        # check subject for the remaining features
        feats = get_subj_feats(subj[0], feats, not_known, conj, deprels) if subj else {}

    not_known = [x for x in feature_names if x not in feats]

    if len(subj) == 0 or len(not_known) > 0:
        return

    return feats


def get_subj_feats(
    subj: conllu.models.Token,
    verb_feats: Dict[str, str],
    unk_feature_keys: List[str],
    conj: List[conllu.models.Token],
    deprels: Dict[str, List[conllu.models.Token]],
) -> Dict[str, str]:
    """
    Extract subject features from its dependants if there are any
    """

    subj_features = subj.get("feats")
    if subj_features is None:
        subj_features = {}

    # check modifiers for gender features
    if "Gender" in unk_feature_keys:
        modifiers = [
            x for x in deprels.get(subj["id"], []) if x.get("deprel") == "amod"
        ]

        # # check verb modifiers if no subject ones are present
        if len(modifiers) == 0:
            conj = [c["id"] for c in conj]
            deps = sum([x for x in [deprels.get(c, []) for c in conj]], [])
            modifiers = [
                x
                for x in deps
                if x["head"] in conj and x.get("deprel", "").startswith("acl")
            ]

        if len(modifiers) != 0:
            mod_feats = modifiers[0].get("feats")
            if mod_feats is not None:
                for key in unk_feature_keys:
                    if key in mod_feats:
                        verb_feats[key] = mod_feats[key]

    # add the remaining features
    unk_feature_keys = [x for x in unk_feature_keys if x not in verb_feats]
    for key in unk_feature_keys:
        if key in subj_features:
            verb_feats[key] = subj_features[key]

    return verb_feats


def get_new_features(
    features: Dict[str, str], subj: conllu.models.Token
) -> Dict[str, str]:
    """
    Change verb tense and other features according to the wordform
    """
    new_features = {}
    for feat, val in features.items():
        if feat == "Person":
            # do not modify if no gender info is found for 1.sg form
            if val == "1" and features["Tense"] == "Fut":
                if "Gender" not in features and (
                    "Number" not in features or features["Number"] == "Sing"
                ):
                    return
            else:
                new_features[feat] = val
        elif feat == "Tense":
            new_features[feat] = "Fut" if val == "Past" else "Past"
        else:
            new_features[feat] = val

    # delete and update contradicting features

    if new_features.get("Tense") == "Fut" or new_features.get("Number") == "Plur":
        # delete gender feature if the verb is changed to future tense form or is plural
        if "Gender" in new_features:
            del new_features["Gender"]

        # if new tense is future and no person value is set - drop
        if "Person" not in new_features and new_features.get("Tense") == "Fut":
            if subj:
                new_features["Person"] = "3"
            else:
                return

    # delete person feature for verbs in past tense
    if new_features.get("Tense") == "Past":
        if "Person" in new_features:
            del new_features["Person"]

    return new_features


def update_feats(
    features: Dict[str, str], new_features: Dict[str, str]
) -> Dict[str, str]:
    """
    Update token features
    """
    features = deepcopy(features)
    features.update(new_features)
    if "Person" in features and "Person" not in new_features:
        del features["Person"]
    return features