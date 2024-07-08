import conllu
import pandas as pd
import os
import pymorphy2
from typing import List, Dict, Optional, Any
from phenomena.min_pair_generator import MinPairGenerator
from phenomena.negation.constants import NEGATIVE_PRONOUNS, PRONOUNS_NEGATIVE
from utils.constants import ASPECT_VERBS
from utils.utils import unify_alphabet, capitalize_word
from string import punctuation


class Negation(MinPairGenerator):
    """
    Negation violations

    Perturbs sentences by changing the position of the negative particle ne 'not' in sentences with negative concord
    or by changing indefinite pronouns to negative and vice-versa.

    Examples:
        Mama nikogda ne myla ramu. ('Mom never has not washed the [window] frame.')
            -> *Mama nikogda myla ne ramu. ('Mom never has washed not the [window] frame.')
            -> *Mama kogda-libo ne myla ramu. ('Mom ever has not washed the [window] frame.')
    """

    def __init__(self):
        """
        Initialization of PoS to which the paritcle ne 'not' cannot be moved to
        """
        super().__init__(name="negation")
        self.neg_concord_stop_upos = [
            "VERB",
            "ADJ",
            "PUNCT",
            "SCONJ",
            "CCONJ",
            "SYM",
            "PART",
        ]

    def negative_concord(
        self, sentence: conllu.models.TokenList
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Finds sentences where the particle ne 'not' is used with the verb and negative pronoun.
        Moves the particle to the head of another noun/adjective/preposition/pronoun phrase.
        Checks ne 'not' to be not put before punctuation symbols.

        Example:
            Mama nikogda ne myla ramu. ('Mom never has not washed the [window] frame.')
                -> *Mama nikogda myla ne ramu .('Mom never has washed not the [window] frame.')
        """
        changed_sentences = []
        for token in sentence:
            if token["lemma"] not in PRONOUNS_NEGATIVE:
                continue
            verb_id = token["head"]
            if sentence[verb_id - 1]["upos"] != "VERB":
                continue
            first_verb_ne = self.check_verb_negation(verb_id, sentence)
            second_verb_id = self.check_second_verb(verb_id, sentence)
            if second_verb_id is not None:
                second_verb_ne = self.check_verb_negation(second_verb_id, sentence)
            if (
                first_verb_ne is None
                and second_verb_id is not None
                and second_verb_ne is None
            ):
                continue
            if (
                first_verb_ne is not None
                and second_verb_id is not None
                and second_verb_ne is not None
            ):
                continue
            if first_verb_ne is None and second_verb_id is None:
                continue
            if (
                second_verb_id is not None
                and sentence[second_verb_id - 1]["deprel"] != "xcomp"
            ):
                second_verb_id = None
                second_verb_ne = None
            neg_poses = []
            for word in sentence:
                neg_pos = first_verb_ne
                if word["head"] != verb_id and second_verb_id is None:
                    continue
                if word["upos"] not in ["NOUN", "ADJ", "ADP", "PRON"]:
                    continue
                if second_verb_id is not None and word["head"] != second_verb_id:
                    continue
                if word["upos"] in self.neg_concord_stop_upos:
                    continue
                if word["deprel"] in ["conj", "csubj", "ccomp"]:
                    continue
                if word["id"] == token["id"]:
                    continue
                adp = self.check_adp(word["id"], sentence)
                if self.check_verb_negation(word["id"], sentence) is not None:
                    continue
                if (
                    word["head"] == second_verb_id
                    and second_verb_ne is not None
                    and second_verb_id is not None
                    and sentence[second_verb_id - 1]["feats"] is not None
                    and "VerbForm" in sentence[second_verb_id - 1]["feats"]
                    and sentence[second_verb_id - 1]["feats"]["VerbForm"] == "INF"
                    and sentence[second_verb_id - 1]["deprel"] == "xcomp"
                ):
                    neg_pos = second_verb_ne
                if adp is not None:
                    new_neg_pos = adp - 2
                else:
                    new_neg_pos = word["id"] - 1
                if new_neg_pos in neg_poses:
                    continue
                if neg_pos is None or new_neg_pos is None:
                    continue
                new_sentence = sentence.metadata["text"].split()
                new_sentence.insert(
                    new_neg_pos,
                    new_sentence.pop(neg_pos - 1),
                )
                if new_neg_pos == 0:
                    continue
                if new_neg_pos < neg_pos:
                    continue
                if (
                    sentence[new_neg_pos]["upos"] in self.neg_concord_stop_upos
                    or sentence[new_neg_pos + 1]["upos"] in self.neg_concord_stop_upos
                    or sentence[new_neg_pos]["form"] == token["form"]
                ):
                    continue
                if (
                    new_sentence[new_neg_pos + 1] == token["form"]
                    or new_sentence[new_neg_pos + 1] in ["не", "ни"]
                    or new_sentence[new_neg_pos + 1] in punctuation
                    or new_sentence[new_neg_pos + 1] in PRONOUNS_NEGATIVE
                ):
                    continue
                if (
                    sentence[neg_pos - 1]["form"][0].isupper()
                    and sentence[neg_pos - 1]["upos"] != "PROPN"
                ):
                    new_sentence[new_neg_pos] = new_sentence[new_neg_pos].capitalize()
                    new_sentence[new_neg_pos + 1] = new_sentence[
                        new_neg_pos + 1
                    ].lower()
                new_sentence = " ".join(new_sentence)
                if sentence[neg_pos - 1]["feats"] is not None:
                    feats = sentence[neg_pos - 1]["feats"].copy()
                    new_feats = sentence[neg_pos - 1]["feats"].copy()
                else:
                    feats = {}
                    new_feats = {}
                neg_poses.append(new_neg_pos)
                feats["ne_position"] = neg_pos - 1
                feats["ne_control_form"] = unify_alphabet(sentence[verb_id - 1]["form"])
                new_feats["ne_control_form"] = unify_alphabet(
                    sentence[new_neg_pos - 1]["form"]
                )
                new_feats["ne_position"] = new_neg_pos
                changed_sentence = self.generate_dict(
                    sentence,
                    new_sentence,
                    self.name,
                    "negative_concord",
                    sentence[neg_pos - 1]["form"],
                    sentence[neg_pos - 1]["form"],
                    feats,
                    new_feats,
                    "ne_position",
                )
                changed_sentences.append(changed_sentence)

        return changed_sentences

    def negative_pronouns(
        self,
        sentence: conllu.models.TokenList,
    ) -> Optional[List[Dict[str, str]]]:
        """
        Finds sentences either with indefinite pronouns without negated verbs or
        with negative pronouns with negated verbs. Changes one type of pronoun
        to another based on the constructed dictionary. Checks sentence to
        not contain imperative or conditions. If the sentence contain bez 'without' or
        comparison writes it down as an additional field.

        Examples:
            Mama kogda-to myla ramu. ('Mom somewhen washed the [window] frame.')
                -> *Mama nikogda myla ramu. ('Mom never washed the [window] frame.')
            Mame nikogda ne myla ramu. ('Mom never has not washed the [window] frame.')
                -> *Mama kogda-libo ne myla ramu. ('Mom ever has not washed the [window] frame.')
        """
        changed_sentences = []
        for token in sentence:
            negation = False
            verb_id = None
            if token["lemma"] == "ничто" and token["deprel"] == "advmod":
                continue
            if token["lemma"] == "что-то" and (
                token["deprel"] == "advmod" or token["upos"] == "ADV"
            ):
                continue
            if token["deprel"] == "obj" or token["deprel"] == "nsubj":
                verb_id = token["head"]
            if (
                token["deprel"] == "advmod"
                or token["deprel"] == "nmod"
                or token["deprel"] == "det"
            ):
                verb_id = sentence[token["head"] - 1]["head"]
                if sentence[verb_id - 1]["upos"] != "VERB":
                    verb_id = sentence[verb_id - 1]["head"]
            if verb_id is None:
                continue
            if sentence[verb_id - 1]["upos"] != "VERB":
                continue
            if self.check_verb_negation(verb_id, sentence) is not None:
                negation = True
            if sentence[verb_id - 1]["head"] != 0:
                if sentence[sentence[verb_id - 1]["head"] - 1]["upos"] == "VERB":
                    verb_id = sentence[verb_id - 1]["head"]
                    if self.check_verb_negation(verb_id, sentence) is not None:
                        if negation:
                            continue
                        else:
                            negation = True
            additonal_condition = self.check_compartive_and_without(
                token["id"], sentence
            )
            if negation:
                pronouns = PRONOUNS_NEGATIVE
                subtype = "negative_pronouns_from"
            else:
                pronouns = NEGATIVE_PRONOUNS
                subtype = "negative_pronouns_to"
            for pronoun in pronouns:
                if token["lemma"] != pronoun:
                    continue
                new_pronouns = pronouns[token["lemma"]]
                for new_pronoun in new_pronouns:
                    new_sentence = sentence.metadata["text"].split()
                    new_word = unify_alphabet(new_pronoun)
                    if new_word.endswith("нибудь") or new_word.endswith("то"):
                        if sentence[-1]["lemma"] == "?":
                            continue
                        if self.check_imperative(sentence):
                            continue
                        if self.check_condition(sentence):
                            continue
                    old_pronoun_pymorphy = self.morph.parse(token["form"])
                    if old_pronoun_pymorphy is None:
                        continue
                    if token["form"] == "никто" and token["deprel"] != "nsubj":
                        continue
                    if token["form"] == "что-то":
                        old_pronoun_pymorphy = old_pronoun_pymorphy[1]
                    elif token["lemma"] == "ничто" and token["upos"] == "PRON":
                        if len(old_pronoun_pymorphy) > 2:
                            old_pronoun_pymorphy = old_pronoun_pymorphy[2]
                        else:
                            old_pronoun_pymorphy = old_pronoun_pymorphy[0]
                        if token["deprel"] != "nsubj":
                            continue
                    else:
                        old_pronoun_pymorphy = old_pronoun_pymorphy[0]
                    grammemes = set()
                    if old_pronoun_pymorphy.tag.case is not None:
                        grammemes.add(old_pronoun_pymorphy.tag.case)
                    if old_pronoun_pymorphy.tag.gender is not None:
                        if token["upos"] != "PRON":
                            grammemes.add(old_pronoun_pymorphy.tag.gender)
                    if old_pronoun_pymorphy.tag.number is not None:
                        grammemes.add(old_pronoun_pymorphy.tag.number)
                    if len(grammemes) > 0:
                        new_word = self.morph.parse(new_word)[0]
                        new_word = new_word.inflect(grammemes)
                        if new_word is None:
                            continue
                        else:
                            new_word = new_word.word
                    if token["form"].startswith("что"):
                        new_word = "ничего"
                    new_word = capitalize_word(token["form"], new_word)
                    new_sentence[token["id"] - 1] = new_word
                    new_sentence = " ".join(new_sentence)
                    if token["feats"] is None:
                        token["feats"] = {}
                    new_feats = token["feats"].copy()
                    if subtype == "negative_pronouns_from":
                        token["feats"]["pronoun_type"] = "negative"
                        new_feats["pronoun_type"] = "indefinite"
                    else:
                        token["feats"]["pronoun_type"] = "indefinite"
                        new_feats["pronoun_type"] = "negative"
                    if additonal_condition == "без":
                        token["feats"]["additional_condition"] = "without"
                    elif (
                        additonal_condition != "без" and additonal_condition is not None
                    ):
                        token["feats"]["additional_condition"] = "compatative"
                    changed_sentence = self.generate_dict(
                        sentence,
                        new_sentence,
                        self.name,
                        subtype,
                        token["form"],
                        new_word,
                        token["feats"],
                        new_feats,
                        "pronoun_type",
                    )
                    changed_sentences.append(changed_sentence)
        return changed_sentences

    def check_verb_negation(
        self, token_id: int, sentence: conllu.models.TokenList
    ) -> Optional[int]:
        """
        Receives sentence and token id. Checks if token id has dependant
        the particle ne 'not'. If it has, returns id of the particle. Otherwise,
        returns None.
        """
        for potential_negation in sentence:
            if (
                potential_negation["lemma"] == "не"
                and potential_negation["head"] == token_id
            ):
                return potential_negation["id"]
        return None

    def check_second_verb(
        self, token_id: int, sentence: conllu.models.TokenList
    ) -> Optional[int]:
        """
        Receives sentence and token id. Checks if token id has dependant verb.
        If it has, returns id of the verb. Otherwise, returns False
        """
        for potential_verb in sentence:
            if potential_verb["upos"] == "VERB" and potential_verb["head"] == token_id:
                return potential_verb["id"]
        return None

    def check_adp(
        self, token_id: int, sentence: conllu.models.TokenList
    ) -> Optional[int]:
        """
        Receives sentence and token id. Checks if token or token's head has
        dependant adposition or it's head. If it has, returns True. Otherwise,
        returns False
        """
        for potential_adp in sentence:
            if potential_adp["upos"] == "ADP" and (
                potential_adp["head"] == token_id
                or potential_adp["head"] == sentence[token_id - 1]["head"]
            ):
                return potential_adp["id"]
        return None

    def check_imperative(self, sentence: conllu.models.TokenList) -> Optional[int]:
        """
        Receives sentence. Checks wheter sentence has verb in imperarive mood.
        If it has, returns True. Otherwise, returns False
        """
        for potential_verb in sentence:
            if (
                potential_verb["upos"] == "VERB"
                and potential_verb["feats"] is not None
                and "Mood" in potential_verb["feats"]
                and potential_verb["feats"]["Mood"] == "Imp"
            ):
                return True
        return False

    def check_condition(self, sentence: conllu.models.TokenList) -> Optional[int]:
        """
        Receives sentence. Checks whether it has condition. If sentence
        has words 'если' or 'бы' returns True. Otherwise, returns False
        """
        for word in sentence:
            if word["lemma"] == "если" or word["lemma"] == "бы":
                return True
        return False

    def check_compartive_and_without(
        self, token_id: int, sentence: conllu.models.TokenList
    ) -> Optional[bool]:
        """
        Receives sentence and token_id. Checks if sentence has
        lemmas 'без' or  'чем'' related to token. If it has, returns
        lemma of the related word. Otherwise, returns None
        """
        for potential in sentence:
            if (
                potential["lemma"] == "без"
                or potential["lemma"] == "чем"
                or (
                    potential["feats"] is not None
                    and "Degree" in potential["feats"]
                    and potential["feats"]["Degree"] == "Cmp"
                )
            ) and (
                potential["head"] == token_id
                or potential["head"] == sentence[token_id - 1]["head"]
                or sentence[potential["head"] - 1]["head"] == token_id
            ):
                return potential["lemma"]

    def get_minimal_pairs(
        self, sentence: conllu.models.TokenList, return_df: bool
    ) -> List[Dict[str, Any]]:
        """
        Recieves a conllu.models.TokenList and outputs
        all possible minimal pairs for the phenomena
        """
        altered_sentences = []

        for generation_func in [
            self.negative_concord,
            self.negative_pronouns,
        ]:
            try:
                generated = generation_func(sentence)
                if generated is not None:
                    altered_sentences.extend(generated)
            except:
                continue

        if return_df:
            altered_sentences = pd.DataFrame(altered_sentences)

        return altered_sentences
