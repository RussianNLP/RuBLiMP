"""Implements generation of sentence pairs with (un)grammatical AGREEMENT

This module allows to find pairs of controller and target of agreement
for agreement phenomena of different kinds, to evaluate pairs and provide
additional information for each pair (like distance in tokens between the
controller and the target, constituent length of controller and target, etc.),
and to make alternations, changing phi-features (agreement features,
like number, gender, person) with the help of Pymorphy.
"""

from copy import deepcopy
from itertools import product, chain
import re
from typing import (
    Iterable,
    Tuple,
    List,
    Dict,
    Union,
    Callable,
    Optional,
    Any,
    TextIO,
)

import conllu
from conllu import (
    parse,
    TokenList,
    Token,
)
import pandas as pd
import pymorphy2

from phenomena.min_pair_generator import (
    MinPairGenerator
)
from utils.utils import (
    capitalize_word,
    unify_alphabet,
    get_constituent,
)
from utils.data_loaders import (
    load_vocab,
    find_nouns_semantically_plural,
    find_nouns_prof_commongender,
)

analyze = pymorphy2.MorphAnalyzer()
nkrya_vocab = load_vocab()
sem_plur = find_nouns_semantically_plural(sem_tags={"t:group"})
dubious_gender = find_nouns_prof_commongender()


ALTERING_PARAMS = ("number", "person", "gender", "case")
MIN_APPOS_HEAD_DIST = 5
MIN_APPOS_CONST_DIST = 2

CONLLU_FEAT2PYMORPHY_FEAT = {
    'form': 'word', 'lemma': 'normal_form'  # , 'upos': 'POS'
}

# Possible values for inflection features
PYMORPHY_FEATS = {
    "case": ("nomn", "gent", "datv", "accs", "ablt", "loct"),  # , "voct"),
    "number": ("sing", "plur"),
    "gender": ("masc", "femn", "neut"),
    "person": ("1per", "2per", "3per"),
}

# Some features coded differently in UD than in Pymorphy
CONLLU_FEAT2PYMORPHY_TAGFEAT = {
    "nom": "nomn", "gen": "gent", "par": "gen2", "dat": "datv", "acc": "accs",
        "ins": "ablt", "loc": "loct", "voc": "voct",
    "fem": "femn",
    "1": "1per", "2": "2per", "3": "3per",
    "fut": "futr",
}
PYMORPHY_TAGFEAT2CONLLU_FEAT = {val: key for key, val in CONLLU_FEAT2PYMORPHY_TAGFEAT.items()}

# these are all POS that COULD inflect for number or gender
#   additional constraints (e.g. gender inflection for verbs is
#   only in the past or in participle form) are to be enforced separately when checking
INFLECT_FOR_NUMBER_POS_PYMORPHY = {"NOUN", "ADJF", "ADJS", "VERB", "PRTF", "PRTS"}
INFLECT_FOR_NUMBER_POS_UD = {"NOUN", "ADJ", "VERB", "AUX", "PRON"}
INFLECT_FOR_GENDER_POS_PYMORPHY = {"ADJF", "ADJS", "PRTF", "PRTS"}
INFLECT_FOR_GENDER_POS_UD = {"ADJ", "VERB", "AUX", "PRON"}
INFLECT_FOR_CASE_POS_PYMORPHY = INFLECT_FOR_NUMBER_POS_PYMORPHY - {"VERB"}

PARTICIPLE_POS = {"PRTF", "PRTS"}
PYMORPHY_VERBAL_POS = {"VERB"} | PARTICIPLE_POS
PYMORPHY_ADJ_POS = {"ADJF", "ADJS"}
PYMORPHY_NOMINAL_POS = {"NOUN", "PRON"}
CONLLU_UPOS2PYMORPHY_POS = {
    "VERB": PYMORPHY_VERBAL_POS | PYMORPHY_ADJ_POS,
    "AUX": PYMORPHY_VERBAL_POS | PYMORPHY_ADJ_POS,
    "ADJ": {"NUMR"} | PYMORPHY_ADJ_POS | PARTICIPLE_POS,
    "NUM": {"NUMR"} | PYMORPHY_ADJ_POS,
    "DET": PYMORPHY_ADJ_POS,
    "PRON": {"NPRO"} | PYMORPHY_ADJ_POS,
    "NOUN": {"NOUN", "NPRO"},
    "PROPN": {"NOUN"},
}

PERSONAL_PRON = {"он", "она", "оно", "они"}
ADJECTIVAL_PRON = {"какой", "который"}

REL2SUBTYPE = {
    "_base_modif": "np-modif",
    "nsubj": "subject-subj_nominal",
    "nsubj:pass": "subject-subj_nominal",
    "gen_nsubj": "subject-subj_negation_gen",  # must NOT be prefixed by `nsubj` type
    "csubj": "subject-subj_clausal",
    "amod": "np-modif_adjectival",
    "amod-floatq": "floating_quantifier-np-modif",
    "floatq": "floating_quantifier-inferred",
    "det": "np-modif_adjectival",
    "amod|det|nummod": "np-modif_adjectival",
    "num": "np-modif_adjectival",
    "acl": "np-appos",
    "acl-part": "np-modif_participle",
    "acl:relcl": "np-relative_clause",
    "_final_npmodif": "np_agreement_{feature}",
    "_final_participle": "np_agreement_{feature}_participle",
    "_final_floatq": "floating_quantifier_agreement_{feature}",
    "_final_appos": "np_agreement_{feature}_remote_modifier",
    "_final_nsubj": "noun_subj_predicate_agreement_{feature}",
    "_final_csubj": "clause_subj_predicate_agreement_{feature}",
    "_final_gen_nsubj": "genitive_subj_predicate_agreement_{feature}",
    "_final_subj_distractors": "subj_predicate_agreement_{feature}",
    "_final_relcl": "anaphor_agreement_{feature}",
}

RelationToCheckingFunc = Dict[
    str, Callable[[TokenList, str, TokenList], Optional[List[Dict]]]
]
FEATS_VALS = Dict[str, Union[int, str]]
PymorphyParse = pymorphy2.analyzer.Parse
Tok = Union[conllu.Token, PymorphyParse]



morph_an = pymorphy2.MorphAnalyzer()


_main = ("id", "form", "lemma", "upos", "head", "deprel")
_feats_nom = ("Animacy", "Case", "Gender")
_feats_verb = ("Aspect", "Mood", "Tense", "VerbForm", "Voice",)
_feats_agr = ("Number", "Person")
_feats = _feats_nom + _feats_verb + _feats_agr

NO_INFL = "not_inflect"


def is_inflectable_number_parse(parse_: PymorphyParse) -> bool:
    return parse_.tag.POS in INFLECT_FOR_NUMBER_POS_PYMORPHY


def is_inflectable_gender_parse(parse_: PymorphyParse) -> bool:
    return (parse_.tag.POS in INFLECT_FOR_GENDER_POS_PYMORPHY
            or {"VERB", "past"} in parse_.tag)


def is_inflectable_person_parse(parse_: PymorphyParse) -> bool:
    p_tag = parse_.tag
    return "VERB" in p_tag and ("pres" in p_tag or "futr" in p_tag)


def is_inflectable_case_parse(parse: PymorphyParse) -> bool:
    return parse.tag.POS in INFLECT_FOR_CASE_POS_PYMORPHY


def is_finite_verb_token(token: conllu.Token) -> bool:
    feats = get_feats_safe(token)
    # if this is a verb form
    return feats.get("VerbForm") == "Fin"


def is_inflectable_number_token(token: conllu.Token) -> bool:
    pos = token["upos"]
    pos_inflects = pos in INFLECT_FOR_NUMBER_POS_UD
    if not pos_inflects:
        return False

    if pos == "PRON":
        return token["lemma"] in ADJECTIVAL_PRON

    # for verbs we need extra checks
    if pos == "VERB":
        return get_feats_safe(token).get("VerbForm") in ("Fin", "Part")

    return True


def is_inflectable_gender_token(token: conllu.Token) -> bool:
    pos = token["upos"]
    pos_inflects = token["upos"] in INFLECT_FOR_GENDER_POS_UD
    if not pos_inflects:
        return False

    if pos == "PRON":
        return token["lemma"] in ADJECTIVAL_PRON

    # for verbs we need extra checks
    if pos in ("VERB", "AUX"):
        verb_form = get_feats_safe(token).get("VerbForm")
        return (verb_form == "Fin" and get_feats_safe(token).get("Tense") == "Past"
                or verb_form == "Part")

    return True


def is_inflectable_person_token(token: conllu.Token) -> bool:
    feats = get_feats_safe(token)
    return (feats and feats.get("VerbForm") == "Fin"
            and feats.get("Tense") in {"Pres", "Fut"})


def is_inflectable_person_dict(tok: Tok) -> bool:
    return (tok["small"].get("verbform") == "Fin"
            and tok["small"].get("tense") == "pres"
    )


feat2pymoprhy_infl_checker = {
    "number": is_inflectable_number_parse,
    "gender": is_inflectable_gender_parse,
    "person": is_inflectable_person_parse,
    "case": is_inflectable_case_parse,
}

feat2token_infl_checker = {
    "number": is_inflectable_number_token,
    "gender": is_inflectable_gender_token,
    "person": is_inflectable_person_token,
}

feat2internal_repr_infl_checker = {
    "person": is_inflectable_person_dict,
}


def get_inflectable_checker(feat: str):
    return feat2pymoprhy_infl_checker[feat]


def is_inflectable(feat: str, tok: Tok) -> bool:
    if isinstance(tok, PymorphyParse):
        return feat2pymoprhy_infl_checker[feat](tok)
    elif isinstance(tok, Token):
        return feat2token_infl_checker[feat](tok)
    else:  # FeatsVals
        return feat2internal_repr_infl_checker[feat](tok)


def are_infl_feats_equal_base(
    # controller: conllu.Token, potential_agreer: conllu.Token,
    contr_feats, agreer_feats, use_lower_case_names=True
):
    # contr_feats = get_feats_safe(controller)
    # agreer_feats = get_feats_safe(potential_agreer)

    contr_has = {}
    contr_feats2vals = {}
    if use_lower_case_names:
        agreer_feats = {feat.lower(): val for feat, val in agreer_feats.items()}

    for feat in ("Number", "Gender", "Person", "Case"):
        if use_lower_case_names:
            feat = feat.lower()

        value = contr_feats.get(feat)
        contr_has_feat = bool(value)
        contr_has[feat] = contr_has_feat
        if contr_has_feat:
            contr_feats2vals[feat] = value

    same_feats_vals = []
    agr_diff_feats = []
    agr_missing_feats = []
    contr_missing_feats = []

    agreer_feats2vals = {}
    for feat, is_valued_contr in contr_has.items():
        agreer_value = agreer_feats.get(feat)
        agr_has_feat = bool(agreer_value)

        if agr_has_feat:
            agreer_feats2vals[feat] = agreer_value

            if is_valued_contr and agreer_value == contr_feats2vals[feat]:
                same_feats_vals.append(feat)
            elif is_valued_contr and agreer_value != contr_feats2vals[feat]:
                agr_diff_feats.append(feat)
            elif not is_valued_contr:
                contr_missing_feats.append(feat)
        else:
            if is_valued_contr:
                agr_missing_feats.append(feat)

    return {"same": same_feats_vals, "diff": agr_diff_feats,
            "agr_missing": agr_missing_feats, "contr_missing": contr_missing_feats}


def are_infl_feats_equal(
    controller: conllu.Token, potential_agreer: conllu.Token,
):
    """Wraps .are_infl_feats_equal_base"""
    contr_feats = get_feats_safe(controller)
    agreer_feats = get_feats_safe(potential_agreer)
    return are_infl_feats_equal_base(contr_feats, agreer_feats,
                                     use_lower_case_names=False)


def find_needed_subject_feats(predicate):
    upos = predicate["upos"]
    feats = get_feats_safe(predicate)

    ADJ_LIKE = {"Gender", "Number", "Case"}

    needed_feats = {}
    if upos in {"VERB", "AUX"}:
        verbform = feats.get("VerbForm")
        if verbform == "Fin":
            tense = feats.get("Tense")
            if tense == "Past":
                needed_feats = {"Gender", "Number"}
            else:  # {"Fut", "Pres"}
                needed_feats = {"Person", "Number"}
        elif verbform == "Part":
            needed_feats = ADJ_LIKE
    elif upos == "ADJ":
        needed_feats = ADJ_LIKE
    elif upos in {"NOUN", "PROPN"}:
        needed_feats = {"Number", "Case"}

    final_feats = set()
    for feat in needed_feats:
        if feats.get(feat):
            final_feats.add(feat)

    return final_feats


def do_agree_subject_predicate(contr, predicate):
    needed_predicate_feats = find_needed_subject_feats(predicate)
    feats_data = are_infl_feats_equal(contr, predicate)
    for feat in needed_predicate_feats:
        if not (feat in feats_data["same"] or feat in feats_data["contr_missing"]):
            return False
    return True


def is_coordinated_basic(tok: Tok, sentence: TokenList) -> bool:
    """Check whether token is a conjunct"""
    dependent_conjuncts = sentence.filter(head=tok["main"]["id"], deprel="conj")
    is_conjunct = tok["main"]["deprel"] == "conj"
    return bool(dependent_conjuncts) or is_conjunct


def in_brackets(
    tok: Dict[str, FEATS_VALS], sentence: TokenList, opening=('"', "'", "«"),
    closing=('"', "'", "»",)
) -> bool:
    tok_id = tok["main"]["id"]
    punct = sentence.filter(upos="PUNCT", head=tok_id)
    if not punct:
        return False

    has_opening_brace, has_closing_brace = False, False

    for _punct in punct:
        if _punct["id"] < tok_id and _punct["form"] in opening:
            has_opening_brace = True
        if _punct["id"] > tok_id and _punct["form"] in closing:
            has_closing_brace = True
    return has_opening_brace and has_closing_brace


def is_uninflectable_numeric_literal(
    string, regex=re.compile(r"\d+[.,]\d+"
                             r"|^(\d+-[ыои]?й)$"
                             r"|\d+")
) -> bool:
    """Check for numeric literal: allow those ending in -ый and ban others

    The latter, like `1981-ый`, `72-ой`, `83-ий` or `14-й`
    can be parsed and inflected by pymorphy"""
    match = regex.match(string)
    if not match:
        return False

    if match and match.group(1):
        return False
    elif match:
        return True


def is_governed_by_nummod(token_id: int, sent: conllu.TokenList):
    return bool(sent.filter(head=token_id, deprel="nummod:gov"))


def has_nummod(token_id: int, sent: conllu.TokenList):
    return bool(sent.filter(head=token_id, deprel="nummod"))


def is_singularia_tantum(form: str):
    parses = morph_an.parse(form)
    # all parses should have this marking, we can take the first one
    parse_ = parses[0]
    return 'Sgtm' in parse_.tag.grammemes


def is_pluralia_tantum(form: str):
    parses = morph_an.parse(form)
    # all parses should have this marking, we can take the first one
    parse_ = parses[0]
    return 'Pltm' in parse_.tag.grammemes


def find_ambigious_nonsubject(
    new_feat_value: str,
    sentence: conllu.TokenList, real_subject_relevant_feats: FEATS_VALS,
    ids_range: Tuple[int, int]
):
    ambigious_maybe_subjs = []

    # print(real_subject_relevant_feats)

    start, stop = ids_range
    candidates = sentence[start-1 : stop-1]
    for cand in candidates:
        # print(f"candidate: {cand}")
        form = cand["form"]
        feats = {feat.lower(): val.lower() for feat, val in (get_feats_safe(cand)).items()
                 if feat.lower() in real_subject_relevant_feats}
        # print(feats)

        if feats:
            parse = Agreement.get_suitable_parse(
                morph_an.parse(form), ref_feats=feats, ref_upos=cand["upos"],
                is_inflectable_=lambda p: True)
            if parse:
                homonyms = find_paradigm_homonyms(parse)
                # print(f"homonyms are: {homonyms}")
                if find_homonyms_potential_agree(new_feat_value, homonyms, {"nomn"}):
                    ambigious_maybe_subjs.append(cand)

    return ambigious_maybe_subjs


def ban_such_inflection_candidate(tok: Tok) -> bool:
    return (tok["main"]["upos"] == "propn"
            or (
                # tok["main"]["upos"] == "num"  # this should be true for UD
                # and
                is_uninflectable_numeric_literal(tok["main"]["lemma"]))
            )


def is_change_feature_ambigous(
    changed: PymorphyParse, homonyms: List[set], intended_feature: str, intended_value: str,
):
    """Find if the change by a certain feature could be intepreted ambigiously

    we check if intended change could be interpreted as a change of other
    (potentially, multiple) features
    """
    if not homonyms:
        return False

    # print(f"checking {intended_feature} {intended_value} {changed}")
    allowed_gender_diff = {"masc", "neut"}

    kept_features2values = {feat: getattr(changed.tag, feat) for feat in PYMORPHY_FEATS
                            if feat != intended_feature}
    # print(kept_features2values)
    orig_gender = kept_features2values.get("gender")

    ambigous_by = {}

    all_other = set()
    for kept_feat, kept_value in kept_features2values.items():
        if kept_value is None or kept_feat == intended_feature:
            continue
        other_vals = set(PYMORPHY_FEATS[kept_feat]) - {kept_value}
        # all_other |= set(PYMORPHY_FEATS[kept_feat]) - {kept_value}
        # print(f"other values for {kept_feat}: {other_vals}")
        for _homonym in homonyms:
            different_feat_val = _homonym & other_vals
            full_diff = changed.tag.grammemes - _homonym
            if (different_feat_val and not (
                    full_diff.issubset(allowed_gender_diff)
                    and orig_gender in allowed_gender_diff)
                and not (
                    changed.tag.grammemes.issuperset({"1per", "plur"})
                    and "impr" in _homonym
                )
            ):
                ambigous_by.setdefault(kept_feat, []).append(different_feat_val)

    return ambigous_by


def ban_such_inflection(
    token_orig: Tok, parse_new: PymorphyParse, homonyms: List[set],
    intended_feature: str, intended_value: str, phenom_subtype: str
) -> bool:
    """Ban improper inflection (differs only orthographically, or homonymous by feats)

    A difference that is only orthographic is the case, for example,
    in the pair `все` all.PL and `всё` all.N"""
    orig_form = unify_alphabet(token_orig["main"]["form"])
    new_form = capitalize_word(orig_form, unify_alphabet(parse_new.word))
    if orig_form == new_form:
        return True

    # another case of orthographic or similar difference is `своею` / `своей` in Fem.Ins.Sg
    #   while it's `своей` in dative and locative singular
    #   Pymorphy also sometimes does strange inflection like `лучший` (Masc.Nom.Sg)
    #   to `наихорошие` (Nom.Pl). Above heuristic doesn't ban those, but this does
    _orig_value = token_orig["small"][intended_feature]
    orig_value = CONLLU_FEAT2PYMORPHY_TAGFEAT.get(_orig_value, _orig_value)

    kept_features2values = {feat: getattr(parse_new.tag, feat)
                            for feat in chain(PYMORPHY_FEATS.keys(), ("animacy",))
                            if feat != intended_feature}
    orig_anim = token_orig["small"]["animacy"]

    for homonym in homonyms:
        orig_vals = chain(kept_features2values.values(), (orig_value,))
        no_difference = all(orig_val in homonym for orig_val in orig_vals
                            if orig_val is not None)
        if (kept_features2values["animacy"] is None
                and ("inan" in homonym or "anim" in homonym)
        ):
            if not orig_anim in homonym and no_difference:
                # print(f"diff animacy")
                no_difference = False

        if no_difference:
            return True

    ambigous_feat2val = is_change_feature_ambigous(
            parse_new, homonyms, intended_feature, intended_value)
    if (ambigous_feat2val
        and not (
            (phenom_subtype and "relative_clause" in phenom_subtype)
            and len(ambigous_feat2val) == 1 and ambigous_feat2val.get("gender") in ("masc", "neut")
        )
    ):
        return True

    return False


def ban_such_agreer_change_in_pair(
    agreer: PymorphyParse, orig_agreer_dict, morph_feature: str, feature_value: str,
    controller: Dict[str, FEATS_VALS], phenomenon_subtype: str, sentence: conllu.TokenList
) -> bool:
    # print(agreer, orig_agreer_dict)
    # print("controller is:", controller)

    # a sentence usually has a nominative subject and we ban change of floating
    #   quantifier to nominative so it is not interpereted as referring to subject
    if agreer.normal_form == "сам" and (
            feature_value == "nomn" or agreer.word == "сам"):
        return True

    if "subject" in phenomenon_subtype:
        if controller["main"]["lemma"] in sem_plur and (feature_value == "plur"):
            return True

        # no change to subject agreer if there are nouns homonymous with nominative close
        if orig_agreer_dict["controller_first"]:
            start = orig_agreer_dict["main"]["id"] + 1
            range_to_check = (start, start + 4)
        else:
            stop = orig_agreer_dict["main"]["id"]
            range_to_check = (stop - 4, stop)

        ambigous_nonsubjects = find_ambigious_nonsubject(
            feature_value, sentence, orig_agreer_dict["agrees"][phenomenon_subtype],
            range_to_check)
        if ambigous_nonsubjects:
            return True

    if (phenomenon_subtype.startswith(REL2SUBTYPE["acl"])
    ):
        return True

    # we don't want Noun agreers here, this is usually dash equational sentences
    # agreers = [agr for agr in agreers if agr["main"]["upos"] != "NOUN"]
    if "subject" in phenomenon_subtype and "clausal" in phenomenon_subtype:
        if orig_agreer_dict["main"]["upos"] == "noun":
            return True

    # no `быть` inflection
    if (orig_agreer_dict["main"]["lemma"] == "быть"
            and orig_agreer_dict["small"]["tense"] == "pres"
            and morph_feature in ("person", "number")
    ):
        return True

    # conjunctions: no change from singular to plural (it is always allowed)
    if controller["is_conjunct"]:
        if feature_value == "plur":
            return True

    # SOME AGREERS could be controllers in other relations
    contr_rels = orig_agreer_dict.get('contr_rel', ())
    if contr_rels:
        # print(f"agreer is also contr: {contr_rels}")
        all_agr_params = set.union(*orig_agreer_dict["agrees"].values())
        all_contr_params = set.union(*orig_agreer_dict["controls"].values())
        agr_not_contr = all_agr_params - all_contr_params

        if not agr_not_contr or not morph_feature in agr_not_contr:
            return True

    other_controlled_rels = [
        rel for rel, controlled in controller["controls"].items()
        if rel != phenomenon_subtype and morph_feature in controlled
    ]

    # agreers with proper nouns are changed only if that feature
    #   (usually gender but also number) is deducible from other agreers
    feats_dubious_for_proper = ("number", "gender")
    if controller["main"]["upos"].lower() == "propn":
        # print(f"Proper noun: {controller['main']['form']} ({agreer})")
        if (not other_controlled_rels and morph_feature in feats_dubious_for_proper
            and (morph_feature != "gender" or feature_value in {"masc", "femn"})
        ):
            return True

    # nouns in brackets are sometimes marked simply `NOUN`, but they are proper names
    #   and gender and number is dubious
    if controller["in_brackets"] and morph_feature in feats_dubious_for_proper:
        return True

    # agreers with profession names (`директор` 'director') and common gender nouns (`судья` 'judge' etc.)
    #   are changed for gender only if it is deducible from other agreers too
    if (morph_feature == "gender" and feature_value in {"masc", "femn"}
            and controller["main"]["lemma"].lower() in dubious_gender):
        if not other_controlled_rels:
            return True

    return False


def filter_such_controller_change_in_pair(
    controller: PymorphyParse, orig_contr_dict, morph_feature: str, feature_value: str,
    agreers: List[Dict[str, FEATS_VALS]], sentence: conllu.TokenList
) -> Optional[List[Dict[str, FEATS_VALS]]]:
    contr_rels = orig_contr_dict["contr_rel"].copy()

    if (is_governed_by_nummod(orig_contr_dict["main"]["id"], sentence)
            or has_nummod(orig_contr_dict["main"]["id"], sentence)):
        return None

    if REL2SUBTYPE["acl:relcl"] in orig_contr_dict.get("agr_rel", []):
        return None

    adjs = {agr_rel for agr_rel in contr_rels
            if agr_rel.startswith(REL2SUBTYPE["_base_modif"])}
    has_adj = len(adjs) > 0
    if has_adj:
        contr_rels -= adjs

    nsubjs = {agr_rel for agr_rel in contr_rels
              if agr_rel.startswith(REL2SUBTYPE["nsubj"])}
    has_nsubj = bool(nsubjs)
    if has_nsubj:
        contr_rels -= nsubjs

    neggen_nsubj_type = REL2SUBTYPE["gen_nsubj"]
    neggen_nsubjs = {agr_rel for agr_rel in contr_rels
                     if agr_rel.startswith(neggen_nsubj_type)}
    has_neggen_subj = neggen_nsubj_type in contr_rels
    if has_neggen_subj:
        contr_rels -= neggen_nsubjs

    appos_type = REL2SUBTYPE["acl"]
    appos = {agr_rel for agr_rel in contr_rels
             if agr_rel.startswith(appos_type)}

    others = contr_rels
    has_others = bool(others)


    # no controller change for distractors
    new_agreers = [agr for agr in agreers
                   if "distractors" not in agr["phenomenon_subtype"]]

    # filter possessive predicative `est'`
    #   `У меня есть мечта` / `У меня есть мечты` are both good regardless of number,
    #   same for person, gender

    if has_nsubj:
        subj_agreers = [agr for agr in agreers
                        if agr["phenomenon_subtype"] in nsubjs]
        if len(subj_agreers) == 1:
            subj_agr = subj_agreers[0]
            if subj_agr["main"]["form"].lower() == "есть":
                # print("filtered predicative possession")
                if has_others:
                    new_agreers = [agr for agr in agreers
                                   if agr["phenomenon_subtype"] in others]
                else:
                    return None

    # homonymity
    controller_feats = {}
    for feat in ("case", "gender", "number", "person"):
        val = getattr(controller.tag, feat)
        if val and feat != morph_feature:
            controller_feats[feat] = val

    _temp_agreers = []
    for agr in new_agreers:
        homonyms = agr.get("paradigm_homonyms", [])
        if len(homonyms) > 0:
            homonyms = find_homonyms_potential_agree(
                feature_value, homonyms, set(controller_feats.values()))
            if not homonyms:
                _temp_agreers.append(agr)

    new_agreers = _temp_agreers

    is_conjunct = orig_contr_dict["is_conjunct"]
    if is_conjunct and feature_value == "plur":
        new_agreers = [agr for agr in new_agreers
                       if agr["small"]["number"] == "sing"]
    elif is_conjunct and feature_value == "sing":
        return None

    # SOME CONTROLLERS could be agreers in other relations
    agr_rels = orig_contr_dict.get('agr_rel', ())
    if agr_rels:
        # print(f"contr is also agreer: {agr_rels}")
        all_agr_params = set.union(*orig_contr_dict["agrees"].values())
        all_contr_params = set.union(*orig_contr_dict["controls"].values())
        contr_not_agr = all_contr_params - all_agr_params

        if not contr_not_agr or not morph_feature in contr_not_agr:
            return None

        new_agreers = [agr for agr in new_agreers
                       if any(morph_feature in agr_feats
                              for rel, agr_feats in agr.get("agrees", {}).items())]

    if has_nsubj:
        final_agreers = [agr for agr in new_agreers
                         if agr["phenomenon_subtype"] in (nsubjs)]
        return final_agreers

    # genitive of negation doesn't meaningfully agree and we don't alter controller
    #  under this label
    #  However an adjective could agree with it and then we do alter both,
    #  but under "modif" labels
    if has_neggen_subj:
        new_agreers = [agr for agr in new_agreers
                       if agr["phenomenon_subtype"] in (adjs | others)]
        # if new_agreers != agreers:
        #     print(f"filtered agreers by neggen:"
        #           f"\nbefore: {agreers}"
        #           f"\nafter : {new_agreers}")

    # ban change for "adjectival-nominal" if controller is also changed for nonmodif
    if adjs:
        if others:
            return None

    # filter out appos
    new_agreers = [agr for agr in new_agreers
                   if (agr["phenomenon_subtype"] not in appos
                       and "appos" not in agr["phenomenon_subtype"])]

    # either `adjs` and no `others` or `others` and no `adjs`
    return new_agreers


def find_paradigm_homonyms(parse: PymorphyParse) -> List[set]:
    """Find if the form has homonyms in other cells of the lexeme paradigm

    "Other cells the of lexeme paradigm" means other inflection features"""
    orig_lexeme = parse.normal_form
    orig_word = parse.word
    orig_tag = parse.tag

    paradigm_homonyms = []
    # this now checks forms disregarding `е` / `ё` distinction
    for _p in morph_an.parse(unify_alphabet(parse.word)):
        if (_p.normal_form == orig_lexeme
                and unify_alphabet(_p.word) == unify_alphabet(orig_word)
                and _p.tag != orig_tag):
            paradigm_homonyms.append(set(_p.tag.grammemes))

    return paradigm_homonyms


def find_homonyms_potential_agree(
    feature_value, homonyms: List[set], other_necessary_feats=set(),
):
    """Find whether after a change of `morph_feature` in agreer to have value `feature_value`,
    it could have potentially agreed not with real controller but with homonymous form

    Example:
        `пробки не потребуется` (orig)
        `пробки не потребуются` (agreer number changed to `plur`)
        here controller `пробки` (gen.sg) is homonymous with (nom.pl)
        and `plur` is exactly the form of the changed agreer
    """

    potential_agreeing_homonyms = []
    for homonym in homonyms:
        if feature_value in homonym and other_necessary_feats.issubset(homonym):
            potential_agreeing_homonyms.append(homonym)

    return potential_agreeing_homonyms


def is_fixed_conj_expression(
    modif: conllu.Token, head: conllu.Token, sentence: conllu.TokenList
):
    if not (is_inflectable_gender_token(modif)):
        return True
    else:
        head_id = head["id"]
        maybe_conj_spots = [(head_id + 2) - 1, (modif["id"] - 1) - 1]  # ids begin from 1
        for maybe_conj_spot in maybe_conj_spots:
            maybe_punct_spot = maybe_conj_spot - 1
            if maybe_conj_spot < len(sentence):
                maybe_conj = sentence[maybe_conj_spot]
                maybe_punc = sentence[maybe_punct_spot]
                if maybe_conj["upos"] == "SCONJ" or maybe_punc["upos"] == "PUNCT":
                    return True

        # there could be other undesirable cases: predicates of clauses
        #   with `то` are marked `acl`. For example:
        #   `из-за того, что петя пришёл, ...`
        maybe_prep_spot = (head_id - 1) - 1
        if maybe_prep_spot >= 0:
            maybe_prep = sentence[maybe_prep_spot]
            if maybe_prep["upos"] == "ADP" and head["lemma"] == "то":
                return True


def get_len(span: TokenList) -> int:
    return len(span)


def get_len_no_punct(span: TokenList) -> int:
    return sum(1 for tok in span if tok["upos"] != "PUNCT")


def get_feats_safe(token: conllu.Token) -> Dict:
    return token["feats"] or {}


def get_distance_stats(
    tok1_id: int, tok2_id: int, tokens: TokenList, skip_punct=False
) -> Tuple[int, bool, bool]:
    """Measures distance between two tokens in terms of (other) tokens"""
    is_1_before_2 = tok1_id < tok2_id
    l_id, r_id = (tok1_id, tok2_id) if is_1_before_2 else (tok2_id, tok1_id)

    distance = get_len_no_punct(tokens[l_id:r_id]) if skip_punct else r_id - l_id - 1
    return distance, skip_punct, is_1_before_2


def filter_not_empty(d: Dict[Any, Any]) -> Dict[Any, Any]:
    return {k: filter_not_empty(v) if isinstance(v, dict) else v
            for k, v in d.items()
            if v}


def flatten_dict(d: Dict, no_flatten=("distractors_ids", "controls", "agrees")) -> Dict:
    res = {}
    for key, val in d.items():
        if isinstance(val, dict):
            if key not in no_flatten:
                res.update(flatten_dict(val))
            else:
                res[key] = val
        else:
            res[key] = val
    return res


class Agreement(MinPairGenerator):
    def __init__(
        self, name="agreement", allowed_cols: Optional[List[str]]=None,
        exclude_dash_nominal_subj=True,
    ):
        super().__init__(name=name)
        self.main_feats = ["id", "form", "lemma",  "upos", "head", "deprel"]
        self.small_feats = ["Case", "Gender", "Person", "Number",
                            "Animacy",
                            "Tense", "VerbForm", "Variant"]

        self.exclude_dash_nominal_subj = exclude_dash_nominal_subj

        def is_np_modif(subtype):
            return isinstance(subtype, str) and "np-modif" in subtype

        self.do_alter_case = is_np_modif

        self.REL2CHECKER = [
            ("nsubj", self.check_nominal_subject),
            ("csubj", self.check_clausal_subject),
            ("amod|det|nummod", self.check_modifier),
            ("acl", self.check_adjectival_clause),
            ("acl:relcl", self.check_relative_clause),
        ]

        self.DISTRACTOR_LABEL = "attractor"

        self.ALLOWED_COLS = allowed_cols or [
            "sentence_id", "source_sentence", "target_sentence", "annotation",
            "phenomenon", "phenomenon_subtype", "source_word", "target_word",
            "source_word_feats", "target_word_feats",
            "feature", "length", "ipm", "tree_length", "sentence_feats"]

    def rename_subtypes(self, orig_subtype, pair):
        feature = pair["feature"]
        has_distractors = "distractors" in orig_subtype

        if "floating" in orig_subtype:
            new_subtype = REL2SUBTYPE["_final_floatq"]
        elif orig_subtype.startswith(REL2SUBTYPE["_base_modif"]):
            if "participle" in orig_subtype:
                has_distractors = False
            new_subtype = REL2SUBTYPE["_final_npmodif"]
        elif "appos" in orig_subtype:
            new_subtype = REL2SUBTYPE["_final_appos"]
        elif orig_subtype.startswith("subject"):
            if has_distractors:
                new_subtype = REL2SUBTYPE["_final_subj_distractors"]
            elif "negation_gen" in orig_subtype:
                new_subtype = REL2SUBTYPE["_final_gen_nsubj"]
            elif "clausal" in orig_subtype:
                new_subtype = REL2SUBTYPE["_final_csubj"]
            else:
                new_subtype = REL2SUBTYPE["_final_nsubj"]
        elif orig_subtype.startswith(REL2SUBTYPE["acl:relcl"]):
            new_subtype = REL2SUBTYPE["_final_relcl"]
        else:
            print(f"unknown subtype: {orig_subtype}")

        new_subtype = new_subtype.format(feature=feature)
        if has_distractors:
            new_subtype += f"_{self.DISTRACTOR_LABEL}"
                
        return new_subtype

    def exclude_subtype(self, subtype):
        if "relative" in subtype and "person" in subtype:
            return True
        if "distractors" in subtype:
            if "participle" in subtype or "person" in subtype:
                return True
        return False

    def get_features(
            self,
            token: Union[Tok, PymorphyParse],
            main_feats: Optional[List[str]] = None,
            small_feats: Optional[List[str]] = None,
            make_lower=True, use_pymorphy=False
    ) -> Dict[str, FEATS_VALS]:
        """Get features from conllu.Token or Pymorphy parse as flat dict"""
        EMPTY_FEAT = ""

        main_feats = main_feats or self.main_feats
        small_feats = small_feats or self.small_feats

        def process(x: str, do=True):
            return x.lower() if isinstance(x, str) and make_lower and do else x

        main, small = {}, {}
        if use_pymorphy:
            try:
                for feature in main_feats:
                    # to keep form case
                    if feature == "form":
                        main[feature] = getattr(token, CONLLU_FEAT2PYMORPHY_FEAT["form"])
                        continue
                    main[process(feature)] = process(
                        getattr(token, CONLLU_FEAT2PYMORPHY_FEAT.get(
                            feature.lower(), feature.lower()), EMPTY_FEAT))

                for feature in small_feats:
                    small[process(feature)] = process(
                        getattr(token.tag, feature.lower(), EMPTY_FEAT))
            except AttributeError:
                pass
        else:
            main = {process(feature): process(token[feature], do=feature != "form")
                    for feature in main_feats}
            small = {process(feature): process(get_feats_safe(token).get(feature))
                     for feature in small_feats}

        return {"main": main, "small": small}

    def convert_feats_to_conllu_names(self, item_feats: Dict[str, str]) -> Dict[str, str]:
        for feat in self.small_feats:
            if feat.lower() in item_feats:
                val = item_feats.pop(feat.lower())
                item_feats[feat] = PYMORPHY_TAGFEAT2CONLLU_FEAT.get(val, val)
        return item_feats

    @staticmethod
    def find_same_featured_toks(
        sentence: conllu.TokenList, feats2values: FEATS_VALS, ids_range: Tuple[int, int],
    ):
        equal_feats_toks = []

        # print(feats2values)

        start, stop = ids_range
        candidates = sentence[start - 1 : stop - 1]
        for cand in candidates:
            # print(cand)
            cand_feats = cand["feats"]
            if not cand_feats:
                continue
            feats_report = are_infl_feats_equal_base(feats2values, cand_feats)
            # print(feats_report)
            if set(feats_report["same"]) == set(feats2values):
                equal_feats_toks.append(cand)

        return equal_feats_toks

    def find_distractors(
        self, controller: Token, agreer: Token,
        controller_constituent: List[conllu.Token], sentence: TokenList,
        prev_feats: Dict[str, Any] = None,
        check_different=True, use_const=False
    ):
        """Find agreement distractors in controller constituent

         Agreement distractors are defined as words in controller constituent
         that occur between controller and agreer and have values for features
         by which agreement takes place with the controller"""
        prev_feats_provided = bool(prev_feats)

        agreer_inflects_for = [
            feat.title() for feat, is_infl_for_feat in feat2token_infl_checker.items()
            if is_infl_for_feat(agreer) and (get_feats_safe(agreer)).get(feat.title())]

        # print(agreer_inflects_for)

        contr_feats2values = {feat: (get_feats_safe(controller)).get(feat)
                              for feat in agreer_inflects_for}
        msg = f"contr: {contr_feats2values} {controller['form']}"
        distractors = {}

        controller_before_agreer = controller["id"] < agreer["id"]
        if controller_before_agreer:
            ids_range = range(controller["id"], agreer["id"])
        else:
            ids_range = range(agreer["id"], controller["id"])
        if use_const:
            search_in = controller_constituent
        else:
            search_in = sentence

        relevant_const_part = [tok for tok in search_in if tok["id"] in ids_range]

        for tok in relevant_const_part:
            for feat in agreer_inflects_for:
                tok_feat_value = (get_feats_safe(tok)).get(feat)
                msg = f"distractors: tok, feat, val: {dict(tok)}, {feat}, {tok_feat_value}"
                # print(msg)

                is_valued = tok_feat_value and contr_feats2values[feat]

                if check_different:
                    feats_check = tok_feat_value != contr_feats2values[feat]
                else:
                    feats_check = tok_feat_value == contr_feats2values[feat]

                if prev_feats_provided:
                    check = (is_valued and prev_feats.get(feat) != tok_feat_value
                             and tok_feat_value == contr_feats2values[feat])
                else:
                    check = is_valued and feats_check

                if check:
                    # print(f"adding distractor by `{feat}`: {tok}")
                    distractors.setdefault(feat.lower(), {}).setdefault(
                        tok["id"], tok_feat_value)
                    break

        return distractors

    def check_predicates_subject_agreers(
        self,
        sentence: TokenList, head: Token, agreer_extra_info: Dict,
        exclude_nominal=False, find_xcomp=True
    ):
        """Checks if auxiulary verb exists for predicate and if predicate really agrees"""
        agreers = []

        aux_deprels = {"aux", "cop"}
        possible_aux = sentence.filter(
            # upos="AUX",
            head=head["id"], form=lambda f: f.lower() != "бы",
            deprel=lambda dr: any(dr.startswith(aux_dr) for aux_dr in aux_deprels)
        )
        if possible_aux:
            agreers += possible_aux
            agreer_extra_info["aux"] = possible_aux[0]

        if find_xcomp:
            possible_pass_xcomp = sentence.filter(deprel="xcomp", head=head["id"])
            if possible_pass_xcomp:
                for _xcomp in possible_pass_xcomp:
                    if (sentence.filter(deprel="aux:pass", head=_xcomp["id"])
                            and (is_inflectable_number_token(_xcomp)
                                 or is_inflectable_gender_token(_xcomp))
                    ):
                        agreers.append(_xcomp)

        # in sents like `Ona byla krasiva` both AUX and predicative ADJ agree
        # This should cover all possible lexical predicates
        #   (adjective, participle, which could be inflected for
        #   number and gender, and nouns -- to be inflected for number)
        if ((is_inflectable_number_token(head)
             or is_inflectable_gender_token(head))
                # nouny predicates shouldn't be part of prepositional phrase,
                #   so that we don't match `флаге` below
                #   `На флаге — фигура медведя — это образ хозяина земли .` (s2301)
                and (not sentence.filter(head=head["id"], upos="ADP")
                     or head["upos"] in ("AUX", "VERB"))
                # the form should either have no case (verbs, etc.) or nominative
                and ((get_feats_safe(head)).get("Case") is None
                     or (get_feats_safe(head)).get("Case") == "Nom")
        ):
            head["nominal"] = True
            agreers += [head]

            if not possible_aux and head["upos"] not in ("AUX", "VERB", "ADJ"):
                # potentially a sentence with a dash like
                # Решето — расположение шашек , при котором между ними имеются свободные поля .
                # where various combinations of number features
                # on subject and predicate are possible
                if exclude_nominal:
                    # print(f"excluding {head}")
                    agreers.remove(head)
                else:
                    agreer_extra_info["maybe_nominal"] = True

        return agreers

    @staticmethod
    def add_agreer_gender_by_cont(
        contr: Dict[str, FEATS_VALS], agreer: Dict[str, FEATS_VALS]
    ):
        contr_gender = contr["small"].get("gender")
        agr_gender = agreer["small"].get("gender")

        if agr_gender is None and contr_gender is not None:
            agreer["small"]["gender"] = contr_gender
        # elif contr_gender is not None and contr_gender != agr_gender:
        #     print(f"alert: different genders: {contr} - {agreer}")

    def check_nominal_subject(
        self, sentence: conllu.TokenList, exclude_dash_nominal_subj=None
    ) -> List[Dict[str, Any]]:
        """Check if subject agreement actually exists in a sentence with `nsubj`"""
        if exclude_dash_nominal_subj is None:
            exclude_dash_nominal_subj = self.exclude_dash_nominal_subj

        controller_targets = []
        subjects = sentence.filter(deprel=lambda dr: dr in {"nsubj", "nsubj:pass"})
        default_subtype = REL2SUBTYPE["nsubj"]

        for subject in subjects:
            if not get_feats_safe(subject):
                continue

            # below `одинок` is nsubj for `становится`
            #   `Только отсюда становится понятным , почему Ядозуб одинок и предпочитает вообще не общаться с людьми .`
            # we don't want such cases
            if ((subject["upos"] == "ADJ"
                 and (get_feats_safe(subject)).get("Variant") == "Short")
                    # TODO: perhaps we should include "obj", "iobj" etc.
                    or bool(sentence.filter(deprel="nsubj", head=subject["id"]))
            ):
                continue

            agreer_extra_info = {"phenomenon_subtype": default_subtype}

            heads = sentence.filter(id=subject["head"])
            if not heads:
                continue
            else:
                head = heads[0]

            agreers = self.check_predicates_subject_agreers(
                sentence, head, agreer_extra_info, exclude_nominal=exclude_dash_nominal_subj
            )
            if not agreers:
                continue

            subject_feats = self.get_features(subject)
            is_neggen = False

            if subject_feats["small"].get("case") == "gen":
                # we ensure that negation is present
                agreer_has_negation = False
                for agreer in agreers:
                    agr_id = agreer["id"]
                    negation = sentence.filter(id=lambda id_: id_ < agr_id,
                                               upos="PART", lemma="не", head=agreer["id"])
                    if negation:
                        agreer_has_negation = True

                if not agreer_has_negation:
                    continue
                is_neggen = True

                agreer_extra_info["phenomenon_subtype"] = REL2SUBTYPE["gen_nsubj"]

            subject_const = get_constituent(subject, sentence)
            subject_const_len = get_len_no_punct(subject_const)

            controller_agreer = {}
            controller_agreer["controller"] = subject_feats
            controller_agreer["controller"]["constituent"] = subject_const
            controller_agreer["controller"]["const_word_len"] = subject_const_len
            controller_agreer["agreers"] = []

            if "aux" in agreer_extra_info:
                aux = agreer_extra_info.pop("aux")
                chosen_head_id = aux["id"]
            else:
                chosen_head_id = head["id"]

            skip_all = False
            for agreer in agreers:
                agreer_feats = self.get_features(
                    agreer,
                )
                tense = agreer_feats["small"]["tense"]
                if not tense or tense not in ("pres", "fut"):
                    self.add_agreer_gender_by_cont(subject_feats, agreer_feats)

                presence2feats = are_infl_feats_equal_base(subject_feats["small"],
                                                           agreer_feats["small"])
                diff = presence2feats["diff"]
                agr_number = agreer_feats["small"]["number"]
                # print(diff, agr_number, is_singularia_tantum(agreer["lemma"]))
                if (diff and not is_neggen
                    and not (diff == ["number"] and agr_number == "plur"
                             and is_singularia_tantum(subject["lemma"]))
                ):
                    # no agreement in the source
                    skip_all = True
                    break

                if agreer["id"] != chosen_head_id:
                    agreer_feats[NO_INFL] = True

                controller_agreer["agreers"].append(agreer_feats)

                is_gen_neg = "negation_gen" in agreer_extra_info["phenomenon_subtype"]

                if not is_gen_neg:
                    distractors = self.find_distractors(subject, agreer, subject_const,
                                                        sentence)
                    agreer_feats.update(
                        has_distractors=bool(distractors),
                        distractors_ids=distractors if distractors else ""
                    )

                agreer_feats.update(**agreer_extra_info)

            if not skip_all:
                controller_targets.append(controller_agreer)

        return controller_targets

    def check_clausal_subject(
        self, sentence: conllu.TokenList
    ) -> List[Dict[str, Any]]:
        """Check if subject agreement actually exists in a sentence with `csubj`"""
        controller_targets = []
        clausal_subjects = sentence.filter(deprel=lambda dr: dr.startswith("csubj"))
        default_subtype = REL2SUBTYPE["csubj"]

        for subject in clausal_subjects:
            subject_feats = self.get_features(subject)
            subject_feats[NO_INFL] = True

            heads = sentence.filter(id=subject["head"])
            if not heads:
                continue
            else:
                head = heads[0]

            controller_agreer = {}

            is_passive = subject["deprel"].endswith(":pass")
            agreer_extra_info = {
                "phenomenon_subtype": default_subtype
                    if not is_passive else "subject-subj_clausal_pass"
            }
            agreers = self.check_predicates_subject_agreers(
                sentence, head, agreer_extra_info
            )
            # # we don't want Noun agreers here, this is usually dash equational sentences
            # agreers = [agr for agr in agreers if agr["main"]["upos"] != "NOUN"]
            if not agreers:
                continue

            subject_const = get_constituent(subject, sentence)
            subject_const_len = get_len_no_punct(subject_const)

            controller_agreer["controller"] = subject_feats
            controller_agreer["controller"]["constituent"] = subject_const
            controller_agreer["controller"]["const_word_len"] = subject_const_len
            controller_agreer["agreers"] = []

            # print(agreer_extra_info)
            if "aux" in agreer_extra_info:
                aux = agreer_extra_info.pop("aux")
                chosen_head_id = aux["id"]
            else:
                chosen_head_id = head["id"]

            for agreer in agreers:
                agreer_feats = self.get_features(
                    agreer,
                )

                if agreer["id"] != chosen_head_id:
                    agreer_feats[NO_INFL] = True

                controller_agreer["agreers"].append(agreer_feats)
                distractors = self.find_distractors(subject, agreer, subject_const,
                                                    sentence)
                agreer_feats.update(
                    has_distractors=bool(distractors),
                    distractors_ids=distractors if distractors else "",
                    **agreer_extra_info
                )

            controller_targets.append(controller_agreer)

        return controller_targets

    @staticmethod
    def add_agreer_animacy_by_cont(
        contr: Dict[str, FEATS_VALS], agreer: Dict[str, FEATS_VALS]
    ):
        contr_animacy = contr["small"].get("animacy")
        agr_animacy = agreer["small"].get("animacy")

        if contr_animacy is not None and agr_animacy is None:
            agreer["small"]["animacy"] = contr_animacy

    def check_modifier(
        self, sentence: conllu.TokenList
    ) -> Optional[List[Dict[str, Any]]]:
        """Check if modifier agreement actually exists in a sentence with deprel"""
        controller_targets = []

        def deprel(dr): return dr in {"amod", "det", "nummod"}
        modifiers = sentence.filter(deprel=deprel)
        default_subtype = REL2SUBTYPE["amod"]

        modif2head_ids: Dict[int, int] = {}  # this prevents duplication
        for modif in modifiers:
            heads = sentence.filter(id=modif["head"])
            if not heads:
                continue
            else:
                head = heads[0]

            if not get_feats_safe(modif):
                continue

            head_upos = head["upos"]
            head_feats = get_feats_safe(head)
            is_participle = head_upos == "Verb" and head_feats.get("VerbForm") == "Part"
            if not (head_upos in {"NOUN", "PRON", "PROPN"} or is_participle):
                continue

            if modif["id"] in modif2head_ids:
                continue

            subtype = REL2SUBTYPE["acl-part"] if is_participle else default_subtype
            modif_feats = {"phenomenon_subtype": subtype}
            controller_agreer = {}
            controller_targets.append(controller_agreer)

            head_modifiers = sentence.filter(head=head["id"], deprel=deprel)
            head_cons = get_constituent(head, sentence)
            head_cons_len = get_len_no_punct(head_cons)

            head_feats = self.get_features(head)
            controller_agreer["controller"] = head_feats
            controller_agreer["controller"]["constituent"] = head_cons
            controller_agreer["controller"]["const_word_len"] = head_cons_len
            controller_agreer["agreers"] = []
            controller_agreer["controller"]["is_subject"] = head["deprel"] == "nsubj"

            for _head_modif in head_modifiers:
                agreer_data = self.get_features(_head_modif)
                agreer_data.update(modif_feats)
                if _head_modif["lemma"] == "сам":
                    agreer_data["phenomenon_subtype"] = REL2SUBTYPE["amod-floatq"]

                self.add_agreer_animacy_by_cont(head_feats, agreer_data)
                self.add_agreer_gender_by_cont(head_feats, agreer_data)
                presence2feats = are_infl_feats_equal_base(head_feats["small"],
                                                           agreer_data["small"])
                diff = presence2feats["diff"]
                agr_number = agreer_data["small"]["number"]
                # print(diff, agr_number, is_governed_by_nummod(head, sentence))
                if (diff
                    and not (diff == ["number"] and agr_number == "plur"
                             and is_governed_by_nummod(head["id"], sentence))
                ):
                    # no agreement in the source
                    continue

                controller_agreer["agreers"].append(agreer_data)

                modif2head_ids[_head_modif["id"]] = head["id"]

        return controller_targets

    def find_possible_antecedent_argument(
        self,
        sentence: TokenList, anaphoric_expr: Token, relative_to_head: Token=None,
        antecedent_deprels={"nsubj", "obj", "iobj", "obl"},
        head_deprels_to_check=("conj", "parataxis"), strictly_same_case=True,
        strictly_same_num_gend=True,
        cur_depth=0, max_depth=1,        # 0 is same-clause, > 0 allows to look
    ):
        """Finds argument of the verb with the same case and similar features

        The argument could be of the same verb as `anaphoric_expr` or
        of a conjucted verb"""

        if cur_depth > max_depth:
            return []

        if relative_to_head is None:
            relative_to_head = sentence[anaphoric_expr["head"] - 1]

        possible_hosts = sentence.filter(
            deprel=lambda rel: rel in antecedent_deprels,
            head=relative_to_head["id"]
        )
        anaphoric_expr_feats = get_feats_safe(anaphoric_expr)
        expr_case = anaphoric_expr_feats.get("Case")
        expr_number = anaphoric_expr_feats.get("Number")
        expr_gender = anaphoric_expr_feats.get("Gender")

        options = []
        if possible_hosts:
            for possible_host in possible_hosts:
                possible_host_feats = get_feats_safe(possible_host)
                if not strictly_same_case or possible_host_feats.get("Case") == expr_case:
                    num_same = (
                            (expr_number == possible_host_feats.get("Number"))
                            + (expr_gender is None and expr_number == "Plur"
                               or expr_gender == possible_host_feats.get("Gender"))
                    )
                    possible_host["num_same"] = num_same
                    if not strictly_same_num_gend or num_same == 2:
                        options.append(possible_host)

        options = sorted(options, key=lambda tok: tok["num_same"], reverse=True)
        # mark these antecedents as belonging to same-clause
        for option in options:
            option["antecedent_kind"] = "same_clause"

        head_deprel = relative_to_head["deprel"]
        head_of_head_id = relative_to_head["head"]
        if (not options and head_deprel in {"conj", "parataxis"}
                and head_deprel in head_deprels_to_check):

            first_conjunct = sentence[head_of_head_id - 1]
            all_conjuncts = [first_conjunct]
            all_conjuncts.extend(sentence.filter(
                head=head_of_head_id, deprel=lambda dr: dr in {"conj", "parataxis"})
            )

            # head itself is not conj, so 1 "conj" already means 2 conjuncts
            if len(all_conjuncts) >= 1:
                left_conjuncts = (conj for conj in all_conjuncts[::-1]
                                  if conj["id"] < relative_to_head["id"])

                for conj in left_conjuncts:
                    conj_options = self.find_possible_antecedent_argument(
                        sentence, anaphoric_expr, conj,
                        cur_depth=cur_depth+1
                    )
                    # mark these antecedents as belonging to conj-clause
                    for option in conj_options:
                        option["antecedent_kind"] = "conj_clause"
                    options.extend(conj_options)

                # sorting by `id` after number of same features allows to choose
                #   closest *left* antecedent
                options = sorted(options, key=lambda tok: (tok["num_same"], tok["id"]),
                                 reverse=True)

        return options

    def find_floating_quantifier_controller(
        self,
        sentence: TokenList, floating_q: Token, relative_to_head: Token=None,
        proper_floating_q_hosts={"nsubj", "obj", "iobj", "obl"}
    ):
        options = self.find_possible_antecedent_argument(sentence, floating_q)

        if options:
            head = options[0]
            q_kind = f"{REL2SUBTYPE['floatq']}_{head['antecedent_kind']}"
        else:
            # keep the head, but mark the subtype as unknown
            head = relative_to_head
            q_kind = "unk"

        return head, q_kind

    def check_adjectival_clause(
        self, sentence: conllu.TokenList
    ) -> Optional[List[Dict[str, Any]]]:
        """Check if clauses marked with `acl` (e.g. depictives) actually agree"""

        controller_targets = []
        deprel = "acl"
        modifiers = sentence.filter(deprel=deprel)
        default_subtype = REL2SUBTYPE["acl"]

        for modif in modifiers:
            heads = sentence.filter(id=modif["head"])
            if not heads:
                continue
            else:
                head = heads[0]

            if not get_feats_safe(modif):
                continue

            adjectival_clause = get_constituent(head, sentence)

            modif_feats = {"phenomenon_subtype": default_subtype}
            is_participle = False
            if modif["upos"] == "VERB" and (get_feats_safe(modif)).get("VerbForm") == "Part":
                is_participle = True
                modif_feats["phenomenon_subtype"] = REL2SUBTYPE["acl-part"]

            modif_id = modif["id"]
            # often floating quantifier is marked as dependent on verb
            #   this makes it difficult to find real agreement
            #   here we restore controller-agreer pairs
            is_floating_q = False
            is_np_like = False
            if modif["lemma"] == "сам":
                # we don't want fixed expressions like `само собой`
                if sentence.filter(head=modif["id"], deprel="fixed"):
                    continue

                proper_floating_q_hosts = {"nsubj", "obj", "iobj", "obl"}

                if head["deprel"] not in proper_floating_q_hosts:
                    head, q_kind = self.find_floating_quantifier_controller(
                        sentence, modif, head
                    )
                    if q_kind == "unk":
                        continue

                    is_floating_q = True

                    # we relabel the floating quantifier as belonging to np-modif type
                    #  if it is immediately before or after its head constituent
                    left_id = next(tok["id"] for tok in adjectival_clause if tok["id"] != modif_id)
                    right_id = next(tok["id"] for tok in adjectival_clause[::-1] if tok["id"] != modif_id)
                    if modif_id == left_id - 1 or modif_id == right_id + 1:
                        modif_feats["phenomenon_subtype"] = REL2SUBTYPE["amod-floatq"]
                        is_np_like = True
                    else:
                        modif_feats["phenomenon_subtype"] = q_kind

                else:
                    continue

            # there could be a predicate of a `wh-`
            #   (but not `which`, e.g. `chto`, `chtoby`) clause
            #   that we do not need
            if modif["upos"] == "VERB" and (get_feats_safe(modif)).get("VerbForm") != "Part":
                continue

            if head["upos"] == "VERB" and (get_feats_safe(head)).get("VerbForm") != "Part":
                continue

            do_skip = is_fixed_conj_expression(modif, head, sentence)
            if do_skip:
                continue

            controller_agreer = {}

            head_cons_len = get_len_no_punct(adjectival_clause)

            head_feats = self.get_features(head)
            controller_agreer["controller"] = head_feats
            controller_agreer["controller"]["constituent"] = adjectival_clause
            controller_agreer["controller"]["const_word_len"] = head_cons_len
            controller_agreer["agreers"] = []

            modif_feats.update(self.get_features(modif))
            self.add_agreer_animacy_by_cont(head_feats, modif_feats)
            self.add_agreer_gender_by_cont(head_feats, modif_feats)

            adj_const = get_constituent(
                modif, sentence,
                lambda tok, sent: not (is_finite_verb_token(tok))
            )
            adj_const_ids = {tok["id"] for tok in adj_const}
            const_except_adj_const = [tok for tok in adjectival_clause
                                      if tok["id"] not in adj_const]
            m_id = modif["id"]
            if modif["id"] < head["id"]:
                max_adj_const_id = max(adj_const_ids)
                # const_distance = (next(
                #     t["id"] for t in adjectival_clause if t["id"] != m_id) - m_id)
                first_nonadj_tok_id = next((t["id"] for t in const_except_adj_const
                                         if t["id"] > max_adj_const_id), None)
                if first_nonadj_tok_id is not None:
                    const_distance = first_nonadj_tok_id - max_adj_const_id
                else:
                    const_distance = 0
            else:
                min_adj_const_id = min(adj_const_ids)
                # const_distance = (next(
                #     t["id"] for t in adjectival_clause[::-1] if t["id"] != m_id) - m_id)
                const_distance = (const_except_adj_const[-1]["id"] - min_adj_const_id)

            modif_feats["constituent"] = adj_const
            modif_feats["const_distance"] = const_distance = abs(const_distance)
            modif_feats["head_distance"] = head_distance = abs(modif["id"] - head["id"])

            is_breaking = False
            has_punct = False
            sorted_const = sorted(adjectival_clause, key=lambda tok: tok["id"])
            non_breaking_ids_range = range(sorted_const[0]["id"], sorted_const[-1]["id"])
            for tok, i in zip(sorted_const, non_breaking_ids_range):
                if tok["id"] != i:  # and tok["upos"] != "PUNCT":
                    is_breaking = True
                if tok["upos"] == "PUNCT":
                    has_punct = True

            if (not (is_breaking) and not (is_participle or is_floating_q)
                and not (const_distance >= MIN_APPOS_CONST_DIST
                         and head_distance >= MIN_APPOS_HEAD_DIST)
            ):
                is_np_like = True
                modif_feats["phenomenon_subtype"] = REL2SUBTYPE["amod"] #+ "-orig_appos"

            presence2feats = are_infl_feats_equal_base(head_feats["small"],
                                                       modif_feats["small"])
            if presence2feats["diff"]:
                # no agreement in the source (acl)
                continue

            for feat in presence2feats["same"]:
                conllu_feat = feat.title()
                if (not get_feats_safe(modif).get(conllu_feat)
                        and get_feats_safe(head).get(conllu_feat)):
                    modif["feats"][conllu_feat] = head["feats"][conllu_feat]

            if not is_np_like and is_participle:
                # distractors are also relevant here. They are checked
                #   in the part of the controller constituent, minus the relative clause
                #   constituent
                const_part = get_constituent(
                    head, sentence,
                    # same condition as relative clause
                    lambda tok, sent: tok["form"].startswith("котор")
                                      or (tok["deprel"] == deprel and tok["head"] == head["id"])
                )
                distractors = self.find_distractors(head, modif, const_part, sentence)
                modif_feats.update(
                    has_distractors=bool(distractors),
                    distractors_ids=distractors if distractors else ""
                )
                controller_agreer["controller"]["constituent"] = const_part

            controller_agreer["agreers"].append(modif_feats)
            controller_targets.append(controller_agreer)

        return controller_targets

    def check_relative_clause(
        self, sentence: conllu.TokenList
    ) -> Optional[List[Dict[str, Any]]]:
        """Check if relative clause agreement actually exists in a sentence with `acl:relcl`"""

        controller_targets = []
        deprel = "acl:relcl"
        modifiers = sentence.filter(deprel=deprel)
        default_subtype = REL2SUBTYPE[deprel]

        modif2head_ids: Dict[int, int] = {}
        for modif in modifiers:
            heads = sentence.filter(id=modif["head"])
            if not heads:
                continue
            else:
                head = heads[0]

            if modif["id"] in modif2head_ids:
                continue

            if not get_feats_safe(modif):
                continue

            controller_agreer = {}
            modif_feats = {"phenomenon_subtype": default_subtype}

            rel_sent_or_participle_clause = get_constituent(head, sentence)
            head_cons_len = get_len_no_punct(rel_sent_or_participle_clause)

            for tok in rel_sent_or_participle_clause:
                if tok['form'].startswith("котор"):
                    # it was a relative clause
                    modif = tok
                    break
            else:
                # this is either a verb of a `wh-` (but not `which`, e.g. `chto`) clause
                #    that we do not need, or a participle
                # this is participle only in "finite" clauses
                # if not (get_feats_safe(modif)).get("VerbForm") == "Part":
                #     continue
                continue

            # the model sometimes determines modified head noun incorrectly
            #   and even if it was correct, we don't need ambiguity that may make
            #   the modified sentence seem gramatical
            #   we drop sentence if there is same-valued noun between head and modif
            ids_range = (head["id"] + 1, modif["id"])
            head_feats = {feat.lower(): head["feats"][feat] for feat in ("Number", "Gender")
                          if feat in get_feats_safe(head)}
            same_featured_toks = self.find_same_featured_toks(sentence, head_feats, ids_range)
            if same_featured_toks:
                continue

            if modif["deprel"].startswith("nsubj"):
                modif_feats[NO_INFL] = True

            head_feats = self.get_features(head)
            controller_agreer["controller"] = head_feats
            controller_agreer["controller"]["const_word_len"] = head_cons_len
            controller_agreer["agreers"] = []

            modif_feats.update(self.get_features(modif))
            self.add_agreer_animacy_by_cont(head_feats, modif_feats)
            self.add_agreer_gender_by_cont(head_feats, modif_feats)
            presence2feats = are_infl_feats_equal_base(head_feats["small"],
                                                       modif_feats["small"])
            diff = presence2feats["diff"]
            if (diff and diff != ["case"] and set(diff) != {"number", "case"}):
                continue

            # distractors are also relevant here. They are checked
            #   in the part of the controller constituent, minus the relative clause
            #   constituent
            const_part = get_constituent(
                head, sentence,
                lambda tok, sent:
                tok["form"].startswith("котор")
                or (tok["deprel"] == deprel and tok["head"] == head["id"])
            )
            for feat in presence2feats["same"]:
                conllu_feat = feat.title()
                if (not get_feats_safe(modif).get(conllu_feat)
                        and get_feats_safe(head).get(conllu_feat)):
                    modif["feats"][conllu_feat] = head["feats"][conllu_feat]

            distractors = self.find_distractors(head, modif, const_part, sentence)

            modif_feats.update(
                has_distractors=bool(distractors),
                # distractors_ids=repr(distractors) if distractors else ""
                distractors_ids=distractors if distractors else ""
            )

            controller_agreer["controller"]["constituent"] = const_part

            controller_agreer["agreers"].append(modif_feats)
            controller_targets.append(controller_agreer)

            modif2head_ids[modif["id"]] = head["id"]

        return controller_targets

    @staticmethod
    def get_suitable_parse(
        parses: List[PymorphyParse],
        reference: Dict[str, Dict[str, int]] = None, ref_feats: Dict[str, str] = None,
        ref_upos=None,
        is_inflectable_: Callable[[PymorphyParse], bool] = None,
        # additional_checks: List[Callable[[pymorphy2.analyzer.Parse, Dict[str, str]], bool]] = None
    ) -> Optional[pymorphy2.analyzer.Parse]:
        """Finds among pymophy parses the most similar to `reference` and likely to inflect

        Although taking first pymorphy parse is often enough, there are cases where
        such heuristic helps, especially so in agreement.
        Suppose, we want to change gender of the adjective `ярославский` in the
        sentence `Он поступил в Ярославский университет`. First parse is nominative,
        and the second is accusative. Heuristics defined here correctly find second parse.
        """
        # animacy is needed to inflect but not necessary here as we have
        #   token + gender + case, this is enough
        NO_CHECK_FEATS = ("verbform", "variant", "animacy")
        if not ref_feats and not reference:
            return None
        if not ref_feats:
            ref_feats = {feat: val for feat, val in reference.items() if val}
        ref_feats = {feat: val for feat, val in ref_feats.items()
                     if feat not in NO_CHECK_FEATS}
        if not ref_feats:
            return None

        ref_pos = CONLLU_UPOS2PYMORPHY_POS.get(ref_upos.upper())
        if not ref_pos:
            return None

        # maps indices of pymorphy parses to a map describing them:
        #   {feat: whether the parse inflects for it and equals reference}
        parse_i2feats_eval: Dict[int, Dict[str, int]] = {}
        for i, parse in enumerate(parses):
            for feat, ref_val in ref_feats.items():
                parse_val = getattr(parse.tag, feat) or False
                does_val_exist_and_eq = (
                    parse_val
                    and parse_val == CONLLU_FEAT2PYMORPHY_TAGFEAT.get(ref_val, ref_val)
                )
                parse_i2feats_eval.setdefault(i, {})[feat] = does_val_exist_and_eq

            parse_i2feats_eval[i]["is_inflectable"] = is_inflectable_(parse)

        # parses with highest number of existing and same-valued feats that may inflect
        sorted_by_criteria_sum = sorted(
            parse_i2feats_eval,
            key=lambda k: sum(parse_i2feats_eval[k].values()), reverse=True
        )

        best_parse = parses[sorted_by_criteria_sum[0]]
        # TODO:
        best_parses = [i for i in sorted_by_criteria_sum
                       if parses[i].tag.POS in ref_pos]
        if best_parses:
            best_parse = parses[best_parses[0]]
        else:
            return None

        if not parse_i2feats_eval[sorted_by_criteria_sum[0]]["is_inflectable"]:
            return None

        return best_parse

    @staticmethod
    def replace_subtype_part(
        subtype: str, orig: str, replacement: str = None, sep: str = "-"
    ):
        parts = subtype.split(sep)
        if replacement:
            i = parts.index(orig)
            parts.insert(i, replacement)

        parts.remove(orig)
        return sep.join(parts)

    def alternate_agreement(
        self, controllers_targets, sentence: conllu.TokenList,
        use_controller_gender_in_sing=False,
    ):
        """Does separate alternations for controller and each agreer"""
        controllers_targets_altered = {}

        for c_id, agreement_relations in controllers_targets.items():
            for _agree_pair in agreement_relations:
                controller = _agree_pair["controller"]
                agreers = _agree_pair["agreers"]
                extra = {k: v for k, v in _agree_pair.items()
                         if k not in ("controller", "agreers")}

                orig_controller = {"controller": controller}
                orig_agreers = {"agreers": agreers}

                alt_controllers = (("controller", controller, orig_agreers),)
                alt_agreers = product(("agreer",), agreers, (orig_controller,))

                # itertools.product allows to save an indentation level
                # we abstract over controller and agreer
                for (changed_kind, to_alter, orig_to_keep), feature in product(
                    chain(alt_controllers, alt_agreers),
                    ALTERING_PARAMS
                ):
                    orig_to_keep = orig_to_keep.copy()
                    subtype = to_alter.get("phenomenon_subtype") or ''

                    # Case is special in that we only alternate agreer case
                    #   and only for some subtypes
                    if (
                        feature == "case" and not (
                            changed_kind == "agreer"
                            and self.do_alter_case(to_alter.get("phenomenon_subtype"))
                        )
                    ):
                        continue

                    to_alter["kind"] = changed_kind

                    # `rel_member` is an abstract name for any of controller | agreer
                    rel_member_feats = to_alter["small"]
                    if not any(rel_member_feats.values()):  # no inflectable feats
                        continue

                    # we ban e.g. proper noun.
                    #   We don't inflect it, but it could still occur as controller (orig)
                    if ban_such_inflection_candidate(to_alter) or to_alter.get(NO_INFL):
                        continue

                    feature_old_value = to_alter["small"][feature]
                    old_form = to_alter["main"]["form"]

                    options = PYMORPHY_FEATS[feature]
                    rel_member_param_options = [  # possible feature values to change into
                        opt for opt in options
                        if feature_old_value
                           and opt != CONLLU_FEAT2PYMORPHY_TAGFEAT.get(feature_old_value,
                                                                       feature_old_value)
                    ]

                    rel_member_parses = morph_an.parse(old_form)

                    _infl_checker = get_inflectable_checker(feature)
                    if to_alter["small"].get("variant") == "short":
                        # this makes sure parse with proper lemma is chosen
                        #   and inflection is `намерена` -> `намерено`, not -> `намеренно`
                        infl_checker = lambda _parse: _infl_checker(_parse) and "Qual" not in _parse.tag
                    else:
                        infl_checker = _infl_checker

                    parse_ = self.get_suitable_parse(
                        rel_member_parses, ref_feats=filter_not_empty(to_alter["small"]),
                        ref_upos=to_alter["main"]["upos"],
                        is_inflectable_=infl_checker)
                    if parse_ is None:  # this pos doesn't inflect for this feature
                        continue

                    if changed_kind != "controller":
                        contr = orig_to_keep["controller"]

                        contr_parse = self.get_suitable_parse(
                            morph_an.parse(contr["main"]["form"]),
                            ref_feats=filter_not_empty(contr["small"]),
                            ref_upos=contr["main"]["upos"],
                            # whether it's inflectable doesn't matter here,
                            #   we want to check all controllers
                            is_inflectable_=lambda *args, **kwargs: True
                        )

                        contr["paradigm_homonyms"] = homonyms = []
                        if contr_parse:
                            homonyms.extend(find_paradigm_homonyms(contr_parse))
                    else:
                        for agr in orig_to_keep["agreers"]:
                            agr_parse = self.get_suitable_parse(
                                morph_an.parse(agr["main"]["form"]),
                                ref_feats=filter_not_empty(agr["small"]),
                                ref_upos=agr["main"]["upos"],
                                # whether it's inflectable doesn't matter here,
                                #   we want to check all controllers
                                is_inflectable_=lambda *args, **kwargs: True
                            )

                            agr["paradigm_homonyms"] = homonyms = []
                            if agr_parse:
                                homonyms.extend(find_paradigm_homonyms(agr_parse))

                    for value in rel_member_param_options:
                        new_id = f"{c_id}_{changed_kind}_{to_alter['main']['id']}_{feature}_{value}"
                        # print(new_id)
                        sentence_new = list(sentence)

                        # we inflect properly, accounting for animacy and gender
                        #   (animacy: inanimate `вижу **красивую** розу` ->
                        #      `вижу **красивый** розу` as in `вижу красивый дом`
                        #    vs. animate `вижу красивую девушку` ->
                        #      `вижу **красивого** девушку` as in `вижу красивого парня` )
                        #   (gender is kept from the controller when plur -> sing)
                        infl_feats = {value}
                        tense = to_alter["small"].get("tense")
                        if tense:
                            infl_feats.add(CONLLU_FEAT2PYMORPHY_TAGFEAT.get(tense, tense))

                        changed_rel_member = None

                        # preserve case (this fixes animacy inflection leading to wrong case)
                        if feature != "case":
                            case = to_alter["small"].get("case")
                            if case:
                                infl_feats.add(CONLLU_FEAT2PYMORPHY_TAGFEAT.get(case, case))

                        animacy = to_alter["small"].get("animacy")
                        gender = to_alter["small"].get("gender")
                        number = to_alter["small"].get("number")
                        _gender = CONLLU_FEAT2PYMORPHY_TAGFEAT.get(gender, gender)

                        added_contr_gender = False
                        if (changed_kind == "agreer" and gender and value == "sing"
                                and (not tense or tense == "past")):
                            infl_feats.add(_gender)
                        elif (changed_kind == "controller" and gender
                              and value == "plur"):
                            infl_feats.add(_gender)
                            added_contr_gender = True

                        # we don't change gender in the plural, that requires two changes
                        # if number == "plur" and feature == "gender":
                        #     continue
                        if number and feature != "number":
                            infl_feats.add(number)

                        # print(changed_kind, feature, value, parse_)
                        if (changed_kind == "agreer" and (
                                value == "masc" or feature == "number")
                        ):
                            if animacy:
                                infl_feats.add(to_alter["small"]["animacy"])

                        changed_rel_member = parse_.inflect(infl_feats)
                        if not changed_rel_member and animacy in infl_feats:
                            infl_feats.remove(animacy)

                        if (changed_kind == "controller" and not changed_rel_member
                                and added_contr_gender):
                            infl_feats.remove(_gender)

                        if not changed_rel_member:
                            changed_rel_member = parse_.inflect(infl_feats)

                        # Even though we check inflectability above, not all words
                        #   actually inflect: e.g. `большинство` 'majority' doesn't
                        #   inflect for plural (it is singularia tantum).
                        #   Pluralia tantum may also occur, etc.
                        if not changed_rel_member:
                            continue

                        paradigm_homonyms_of_changed = find_paradigm_homonyms(changed_rel_member)

                        # we also ban inflection if it is, for e.g. the same as source form
                        if ban_such_inflection(
                            to_alter, changed_rel_member, paradigm_homonyms_of_changed,
                            feature, value, subtype,
                        ):
                            continue

                        # we ban various changes based on pair as a whole,
                        #   e.g. we ban semantically plural nominals + `plur` on target predicate
                        #   because this is usually grammatical
                        if (changed_kind == "agreer"
                                and ban_such_agreer_change_in_pair(
                                    changed_rel_member, to_alter, feature, value,
                                    orig_to_keep["controller"],
                                    to_alter.get("phenomenon_subtype"),
                                    sentence
                                )
                        ):
                            continue

                        if changed_kind == "controller":
                            filtered_agreers = filter_such_controller_change_in_pair(
                                changed_rel_member, to_alter, feature, value,
                                orig_to_keep["agreers"], sentence
                            )
                            if filtered_agreers is None:
                                continue
                            else:
                                orig_to_keep["agreers"] = filtered_agreers

                            # print(f"keeping contr {to_alter['main']['form']} ({feature, value})")

                        # we leave only those original agreers that could actually agree
                        #   by this feature
                        if changed_kind == "controller":
                            # checking that value of feature isn't empty should be enough
                            agreers = orig_to_keep["agreers"]
                            orig_to_keep["agreers"] = [agreer for agreer in agreers
                                                       if agreer["small"][feature]]

                        # we ban changes in agreer that lead to homonymous readings
                        #   Below subject is in the genitive of negation:
                        #   `Прежде всего не *потребуется пробки* , поскольку...`
                        #   this form is homonymous with `пробка` + nom.pl, so
                        #   here the change of the predicate to plural `потребуются` is banned
                        if changed_kind == "agreer":
                            contr = orig_to_keep.get("controller", {})
                            if "paradigm_homonyms" in contr:
                                if ("subject" in subtype and "nominal" in subtype
                                    and "negation_gen" not in subtype
                                ):
                                    agreer_feats_homonyms = find_homonyms_potential_agree(
                                        value, contr["paradigm_homonyms"], {"nomn"}
                                    )
                                else:
                                    agreer_feats_homonyms = find_homonyms_potential_agree(
                                        value, contr["paradigm_homonyms"]
                                    )
                                contr["agreer_feats_homonyms"] = agreer_feats_homonyms

                                if agreer_feats_homonyms:
                                    continue

                        new_contr_agreer = controllers_targets_altered.setdefault(new_id, {})
                        new_contr_agreer.update(**extra, **orig_to_keep)

                        new_features = self.get_features(changed_rel_member, use_pymorphy=True)
                        orig_rel_member = flatten_dict(deepcopy(to_alter))

                        if changed_kind == "controller":
                            new_rel_member = new_contr_agreer.setdefault(
                                "controller", orig_rel_member)
                            if "constituent" in new_rel_member:
                                new_rel_member.pop("constituent")
                        elif changed_kind == "agreer":
                            agreers_l = new_contr_agreer.setdefault("agreers", [])
                            new_rel_member = orig_rel_member
                            agreers_l.append(new_rel_member)

                        source_word_feats = flatten_dict(deepcopy(to_alter))
                        new_rel_member["source_word_feats"] = source_word_feats
                        if "constituent" in source_word_feats:
                            source_word_feats.pop("constituent")
                        new_rel_member.update(flatten_dict(filter_not_empty(new_features)))

                        contr = orig_to_keep.get("controller")
                        if (changed_kind == "agreer" and contr
                                and new_rel_member.get("distractors_ids")):
                            subtype = new_rel_member["phenomenon_subtype"]
                            this_feat_distractors = new_rel_member["distractors_ids"].get(feature)
                            chosen_distractor = None
                            if this_feat_distractors:
                                for dist_id, _dist_value in this_feat_distractors.items():
                                    dist_value = _dist_value.lower()
                                    if (CONLLU_FEAT2PYMORPHY_TAGFEAT.get(dist_value, dist_value)
                                            == value):
                                        chosen_distractor = dist_id
                                new_rel_member["assumed_distractor_id"] = chosen_distractor

                            if (chosen_distractor is None
                                    and "distractors" in subtype):
                                upd_subtype = self.replace_subtype_part(subtype, "distractors")
                                new_rel_member["phenomenon_subtype"] = upd_subtype

                        new_rel_member.update(
                            form=capitalize_word(old_form, new_rel_member["form"]),
                            paradigm_homonyms=paradigm_homonyms_of_changed,
                            altered=True
                        )

                        sentence_new[to_alter["main"]["id"] - 1] = new_rel_member
                        target_sentence = " ".join(tok["form"] for tok in sentence_new)
                        # print(f"saving {target_sentence}")
                        new_contr_agreer.update({
                            "source_word": old_form,
                            "target_word": new_rel_member["form"],
                            'feature': feature,
                            'feature_old_value': feature_old_value,
                            'feature_new_value': value,
                            "target_sentence": target_sentence,
                        })
                        self.convert_feats_to_conllu_names(new_rel_member)
                        self.convert_feats_to_conllu_names(new_rel_member["source_word_feats"])

        return controllers_targets_altered

    def check_agreement(
        self,
        sentence: conllu.TokenList, rel2checker: RelationToCheckingFunc = None,
    ) -> Union[Dict[str, List[Union[str, int, Tuple]]], Dict]:
        """Check if various types of agreement occur in the sentence"""

        controllers_targets = {}

        if not rel2checker:
            rel2checker = self.REL2CHECKER

        for rel, checker_func in rel2checker:
            all_agreement_by_rel = checker_func(sentence)

            # iteration allows mapping single controller to multiple relations
            #   (which is useful for debugging and learning if controller actually
            #   participates in multiple relationships)
            #   and checking general things relevant for agreement, like distance
            for agreement_relations in all_agreement_by_rel:
                controller = agreement_relations["controller"]
                agreers = agreement_relations["agreers"]

                # remove improper agreers, which couldn't be inflected
                agreers = [agr for agr in agreers
                           if not is_uninflectable_numeric_literal(agr["main"]["lemma"])]
                if not agreers:
                    continue
                agreement_relations["agreers"] = agreers

                c_id = controller["main"]["id"]
                controller["is_conjunct"] = is_coordinated_basic(controller, sentence)
                controller["in_brackets"] = in_brackets(controller, sentence)

                for agreer in agreers:
                    subtype_ = agreer["phenomenon_subtype"]
                    if ("phenomenon_subtype" not in agreer
                        or not agreer["phenomenon_subtype"]
                        or "distractors" not in agreer["phenomenon_subtype"]
                    ):
                        has_distractors = agreer.get("has_distractors")
                        if has_distractors and "-distractors" not in subtype_:
                            subtype_ = f"{subtype_}-distractors"
                        agreer["phenomenon_subtype"] = subtype_

                    dist_stats = get_distance_stats(c_id, agreer["main"]["id"], sentence)
                    # TODO: `controller_first` is deducible from ids of controller and
                    #   agreer, if they are saved.
                    #   `skip_punct` is technical info and `True` is may be the only
                    #   sensible option, so we may not need to save it and waste space
                    agreer.update(dict(zip(
                        ("distance", "skip_punct", "controller_first"), dist_stats
                    )))

                    agreer["is_conjunct"] = is_coordinated_basic(agreer, sentence)

                    presence2feats = are_infl_feats_equal_base(controller["small"],
                                                               agreer["small"])

                controllers_targets.setdefault(c_id, []).append(agreement_relations)

        agreer_to_subtypes = {}
        controller2phenom2samefeats = {}
        agreer2phenom2samefeats = {}
        for controller_id, agreement_relations in controllers_targets.items():
            for agr_rel in agreement_relations:
                controller = agr_rel["controller"]
                agreers = agr_rel["agreers"]

                for agr in agreers:
                    # print(agr["phenomenon_subtype"])
                    agreer_to_subtypes.setdefault(agr["main"]["id"], set()).add(
                        agr["phenomenon_subtype"]
                    )
                    agr["agr_rel"] = agreer_to_subtypes.get(agr["main"]["id"])

                    contr_agr_same_feats = are_infl_feats_equal_base(
                        controller["small"], agr["small"]
                    )["same"]

                    controller2phenom2samefeats.setdefault(controller_id, {}).setdefault(
                        agr["phenomenon_subtype"], set()
                    ).update(contr_agr_same_feats)

                    agreer2phenom2samefeats.setdefault(agr["main"]["id"], {}).setdefault(
                        agr["phenomenon_subtype"], set()
                    ).update(contr_agr_same_feats)

                controller["controls"] = controller2phenom2samefeats[controller_id]

        controller_to_subtypes = {}
        for controller_id, agreement_relations in controllers_targets.items():
            for agr_rel in agreement_relations:
                controller = agr_rel["controller"]
                agreers = agr_rel["agreers"]

                for agr in agreers:
                    # print(agr["phenomenon_subtype"])
                    controller_to_subtypes.setdefault(controller_id, set()).add(
                        agr["phenomenon_subtype"]
                    )
                    agr_id = agr["main"]["id"]

                    agr_same_feats = agreer2phenom2samefeats.get(agr_id)
                    if agr_same_feats:
                        agr["agrees"] = agr_same_feats

                    contr_rel = controller2phenom2samefeats.get(agr_id)
                    if contr_rel:
                        agr["contr_rel"] = set(contr_rel)

                    agr_as_contr_same_feats = controller2phenom2samefeats.get(agr_id)
                    if agr_as_contr_same_feats:
                        agr["controls"] = agr_as_contr_same_feats

                controller["contr_rel"] = controller_to_subtypes[controller_id]

                agr_rel = agreer_to_subtypes.get(controller_id)
                if agr_rel:
                    controller["agr_rel"] = agr_rel

                contr_as_agr_same_feats = agreer2phenom2samefeats.get(controller_id)
                if contr_as_agr_same_feats:
                    controller["agrees"] = contr_as_agr_same_feats

        # after all kinds of agreement are considered we check whether
        #   each controller is part of multiple agreement relations at the same time
        #   (E.g. `пример` in `Мне попался хороший пример` is part of np and subject-verb)
        for controller_id, agreement_relations in controllers_targets.items():
            has_multiple_agreers = len(agreement_relations) > 1
            agreers_ids = sorted([agr["main"]["id"]
                                  for rel in agreement_relations
                                  for agr in rel["agreers"]])
            for rel in agreement_relations:
                rel["controller"].update(dict(
                    has_multiple_agreers=has_multiple_agreers, agreers_ids=agreers_ids
                ))

        return dict(controllers_targets)

    def flatten_agr_res(
        self,
        _agree_pairs: Dict[int, Any], sentence: conllu.TokenList,
        meta_cols_on_agr=("phenomenon_subtype",),
    ) -> List[Dict[str, Dict[str, Union[str, int]]]]:
        """Flatten hierarchial dict for each controller, rename dict keys"""
        all_pairs = []

        for c_id, agree_pair in _agree_pairs.items():
            controller = agree_pair.pop("controller")
            agreers = agree_pair.pop("agreers")

            single_pair_base = dict(agree_pair)

            controller_altered = controller.get("altered")  # controller.pop("altered")
            if controller_altered:
                single_pair_base["source_word_feats"] = controller.pop("source_word_feats")
                single_pair_base["target_word_feats"] = flatten_dict(controller)

            for agreer in agreers:
                single_pair = dict(single_pair_base)

                meta = {col: agreer[col] for col in meta_cols_on_agr if col in agreer}
                single_pair.update(meta)

                if controller_altered:
                    single_pair.setdefault("sentence_feats", {}).update(
                        agreer=flatten_dict(agreer))

                agreer_altered = agreer.get("altered")
                if agreer_altered:
                    single_pair["source_word_feats"] = agreer.pop("source_word_feats")
                    single_pair["target_word_feats"] = flatten_dict(agreer)

                    contr_dict = flatten_dict(controller)

                    single_pair.setdefault("sentence_feats", {}).update(
                        controller=contr_dict)

                source_word_feats = single_pair["source_word_feats"]
                target_word_feats = single_pair["target_word_feats"]
                sent_feats = single_pair["sentence_feats"]
                items = [sent_feats.get("controller"), sent_feats.get("agreer"),
                         source_word_feats, target_word_feats]
                for item in items:
                    if item:
                        const = item.get("constituent")
                        if const:
                            item["constituent"] = " ".join(tok["form"] for tok in const)

                altered = "agreer" if agreer_altered else "controller"

                single_pair["sentence_feats"].update(
                    {col: val for col, val in single_pair.items()
                     if col not in self.ALLOWED_COLS and col != "sentence_feats"}
                )

                subtype = single_pair.pop("phenomenon_subtype")
                orig_subtype = f'{subtype}_{single_pair["feature"]}'
                if self.exclude_subtype(orig_subtype):
                    continue
                single_pair["sentence_feats"]["orig_subtype"] = orig_subtype

                new_subtype = self.rename_subtypes(subtype, single_pair)
                single_pair["phenomenon_subtype"] = new_subtype

                single_pair = self.generate_dict(
                    sentence,
                    **{col: val for col, val in single_pair.items()
                       if col in self.ALLOWED_COLS},
                    phenomenon=self.name
                )

                all_pairs.append(single_pair)

        return all_pairs

    def get_minimal_pairs(
        self, sentence: conllu.models.TokenList, return_df: bool
    ) -> List[Dict[str, Any]]:
        try:
            controllers_targets_orig = self.check_agreement(sentence, self.REL2CHECKER)
            controllers_targets_altered = self.alternate_agreement(controllers_targets_orig, sentence)
            pairs = self.flatten_agr_res(controllers_targets_altered, sentence)
            if return_df:
                pairs = pd.DataFrame(pairs)
        except Exception as e:
            print("Exception: {}".format(e))
            pairs = None
        return pairs


if __name__ == "__main__":
    agreement_checker = Agreement()

    result = agreement_checker.generate_dataset(
        # "../rusenteval_data/rusenteval_data.conllu",
        "../our_data/librusec_FIRST_5M-2.conllu",
        max_samples=50000,
    )

    print("total:", len(result))
    pd.DataFrame(result).to_csv("agreement_test_12_test_43_50k_nonom_floatingq.csv")
