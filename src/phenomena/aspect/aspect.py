import conllu
import pandas as pd
import os
import pymorphy2
from typing import List, Dict, Optional, Any, Union
from phenomena.min_pair_generator import MinPairGenerator
from phenomena.aspect.constants import (
    ADVERBS,
    REPETITION,
    TIME_PERIODS,
    SINGLE_REPETITION,
)
from utils.constants import ASPECT_VERBS, FREQ_DICT
from utils.utils import unify_alphabet, capitalize_word


class Aspect(MinPairGenerator):
    """
    Aspect violations

    Perturbs sentences by changing the aspect of the verb in the context of duration or repetition,
    and in cases where the target verb depends on the negated deontic verb.

    Examples:
        Petya dolgo reshal zadachu. ('Petya has been solving the task for a long time.')
            -> *Petya dolgo reshil zadachu. ('Petya has solved the task for a long time.')
        Mame ne stoit myt' ramu. ('Mom shouldn't wash the [window] frame.')
            -> *Mame ne stoit pomyt' ramu. ('Mom shouldn't washed the [window] frame.')
    """

    def __init__(self):
        """
        Initialize deontic verbs for which it is impossible to use perfective of the dependant verb during negation.
        """
        super().__init__(name="aspect")
        self.deontic_verbs = ["стоить", "надо", "следовать", "нужно"]

    def deontic_imp(
        self,
        sentence: conllu.models.TokenList,
    ) -> Optional[List[Dict[str, str]]]:
        """
        Finds deontic verbs from the list. Checks deontic verbs to be negated.
        Checks whether the deontic verb has the dependant infinitive verb in
        imperfective form and changes it to the perfective form. Skips the verb
        prodolzhat' 'to continue' and its forms as an exception. Also skips contexts
        with comparisons.

        Example:
            Mame ne stoit myt' ramu. ('Mom shouldn't wash the [window] frame.')
                -> *Mame ne stoit pomyt' ramu. ('Mom shouldn't washed the [window] frame.')
        """
        changed_sentences = []
        for token in sentence:
            if token["upos"] == "PART" and token["lemma"] == "не":
                verb_id = token["head"] - 1
                if (
                    sentence[verb_id]["upos"] == "VERB"
                    and sentence[verb_id]["feats"] is not None
                    and "VerbForm" in sentence[verb_id]["feats"]
                    and sentence[verb_id]["feats"]["VerbForm"] != "Part"
                    and sentence[verb_id]["lemma"] in self.deontic_verbs
                ):
                    for i in range(0, len(sentence)):
                        if sentence[i]["form"] in [
                            "продолжаться",
                            "продолжить",
                            "продолжиться",
                            "продолжать",
                        ]:
                            continue
                        if (
                            sentence[i]["upos"] == "VERB"
                            and sentence[i]["feats"] is not None
                            and "VerbForm" in sentence[i]["feats"]
                            and "Aspect" in sentence[i]["feats"]
                            and sentence[i]["feats"]["VerbForm"] == "Inf"
                            and sentence[i]["feats"]["Aspect"] == "Imp"
                            and sentence[i]["head"] == verb_id + 1
                        ):
                            change_idx = i
                            word = self.get_best_ipm(sentence[i]["lemma"])
                            if word is None:
                                continue
                            new_sentence = sentence.metadata["text"].split(" ")
                            new_verb = unify_alphabet(word)
                            if not self.check_postfix_verbs(
                                sentence[i]["form"], new_verb
                            ):
                                continue
                            new_sentence[i] = new_verb
                            if (
                                self.check_comparative(sentence[i]["id"], sentence)
                                is not None
                            ):
                                continue
                            new_sentence = " ".join(new_sentence)
                            feats = sentence[i]["feats"].copy()
                            feats["control_form"] = sentence[verb_id]["form"]
                            new_feats = feats.copy()
                            new_feats["Aspect"] = "Perf"
                            if self.has_conj(token["id"], sentence):
                                subtype = "deontic_imp_conj"
                            else:
                                subtype = "deontic_imp"
                            changed_sentence = self.generate_dict(
                                sentence,
                                new_sentence,
                                self.name,
                                subtype,
                                sentence[i]["form"],
                                new_verb,
                                feats,
                                new_feats,
                                "Aspect",
                            )
                            if (
                                changed_sentence["source_sentence"]
                                == changed_sentence["target_sentence"]
                            ):
                                continue
                            changed_sentences.append(changed_sentence)
        return changed_sentences

    def change_duration_aspect(
        self,
        sentence: conllu.models.TokenList,
    ) -> Optional[List[Dict[str, str]]]:
        """
        Finds sentences with duration contexts related to the verb in the
        imperfective form.Duration contexts are spotted by the usage of
        corresponding adverbs. Changes the verb form to the perfective.
        The infinitive of the verb is changed via the dictionary and then
        conjugated across the parameters of the original target verb. Also
        skips contexts with comparisons.

        Example:
            Petya dolgo reshal zadachu. ('Petya has been solving the task for a long time.')
                -> *Petya dolgo reshil zadachu. ('Petya has solved the task for a long time.')
        """
        changed_sentences = []
        for token in sentence:
            if token["form"] in [
                "продолжаться",
                "продолжить",
                "продолжиться",
                "продолжать",
            ]:
                continue
            if token["deprel"] == "xcomp" or token["deprel"] == "csubj":
                continue
            if self.has_xcomp_csubj(token["id"], sentence):
                continue
            if (
                token["upos"] == "VERB"
                and token["feats"] is not None
                and "VerbForm" in token["feats"]
                and token["feats"]["VerbForm"] in ["Fin", "Inf"]
            ):
                if (
                    sentence[token["head"] - 1]["upos"] == "VERB"
                    or self.has_conj(token["id"], sentence)
                    or self.has_verb_dep(token["id"], sentence)
                ):
                    continue
                adverb = self.check_duration_adverbs(token["id"], sentence)
                if not adverb:
                    continue
                if "Aspect" not in token["feats"] or token["feats"]["Aspect"] != "Imp":
                    continue
                new_aspect = "Perf"
                if self.has_verb_perf(token["id"], sentence):
                    continue
                word = self.get_best_ipm(token["lemma"])
                if word is None:
                    continue
                new_sentence = sentence.metadata["text"].split(" ")
                new_verb = unify_alphabet(word)
                new_verb = self.conjugate_new_verb(token["form"], new_verb)
                if not new_verb:
                    continue
                if self.check_comparative(token["id"], sentence) is not None:
                    continue
                new_verb = capitalize_word(token["form"], new_verb)
                if not self.check_postfix_verbs(token["form"], new_verb):
                    continue
                new_sentence[token["id"] - 1] = new_verb
                new_sentence = " ".join(new_sentence)
                feats = token["feats"].copy()
                feats["adverb_lemma"] = adverb
                new_feats = feats.copy()
                new_feats["Aspect"] = new_aspect
                changed_sentence = self.generate_dict(
                    sentence,
                    new_sentence,
                    self.name,
                    "change_duration_aspect",
                    token["form"],
                    new_verb,
                    feats,
                    new_feats,
                    "Aspect",
                )
                if (
                    changed_sentence["source_sentence"]
                    == changed_sentence["target_sentence"]
                ):
                    continue
                changed_sentences.append(changed_sentence)
        return changed_sentences

    def change_repetition_aspect(
        self,
        sentence: conllu.models.TokenList,
    ) -> Optional[List[Dict[str, str]]]:
        """
           Finds sentences with duration contexts related to the verb
           in the imperfective form. Duration contexts are spotted by
           the usage of corresponding phrases or adverbs. Changes the verb
           form to the perfective. The infinitive of the verb is changed via
           the dictionary and then conjugated across the parameters of
           the original target verb. Also skips contexts with comparisons.

        Example:
            On begal (imperfective) kazhdyj den'. ('He was running every day.')
                -> *On pobegal (perfective) kazhdyj den'. ('He has ran every day.')
        """
        changed_sentences = []
        for token in sentence:
            if token["form"] in [
                "продолжаться",
                "продолжить",
                "продолжиться",
                "продолжать",
            ]:
                continue
            if token["deprel"] == "xcomp" or token["deprel"] == "csubj":
                continue
            if self.has_xcomp_csubj(token["id"], sentence):
                continue
            if (
                token["upos"] == "VERB"
                and token["feats"] is not None
                and "VerbForm" in token["feats"]
                and token["feats"]["VerbForm"] in ["Fin", "Inf"]
            ):
                repetition_word = self.has_repitition(token["id"], sentence)
                if not repetition_word:
                    continue
                if (
                    self.has_conj(token["id"], sentence)
                    or self.has_verb_dep(token["id"], sentence)
                    or sentence[token["head"] - 1]["upos"] == "VERB"
                ):
                    continue
                if "Aspect" not in token["feats"] or token["feats"]["Aspect"] != "Imp":
                    continue
                else:
                    new_aspect = "Imp"
                word = self.get_best_ipm(token["lemma"])
                if word is None:
                    continue
                new_sentence = sentence.metadata["text"].split(" ")
                new_verb = unify_alphabet(word)
                new_verb = self.conjugate_new_verb(token["form"], new_verb)
                if not new_verb:
                    continue
                new_verb = capitalize_word(token["form"], new_verb)
                if not self.check_postfix_verbs(token["form"], new_verb):
                    continue
                if self.check_comparative(token["id"], sentence) is not None:
                    continue
                new_sentence[token["id"] - 1] = new_verb
                new_sentence = " ".join(new_sentence)
                feats = token["feats"].copy()
                feats["repetition_adverb"] = repetition_word
                new_feats = feats.copy()
                new_feats["Aspect"] = new_aspect
                changed_sentence = self.generate_dict(
                    sentence,
                    new_sentence,
                    self.name,
                    "change_repetition_aspect",
                    token["form"],
                    new_verb,
                    feats,
                    new_feats,
                    "Aspect",
                )
                if (
                    changed_sentence["source_sentence"]
                    == changed_sentence["target_sentence"]
                ):
                    continue
                changed_sentences.append(changed_sentence)
        return changed_sentences

    def get_best_ipm(self, verb: str) -> Optional[str]:
        """
        Receives verb in imperfective form. Returns the perfective form of the verb.
        If the verb has several perfective forms, returns the form with the highest IPM.
        If the verb is not in our dictionary, returns None.
        """
        candidates = ASPECT_VERBS[ASPECT_VERBS["Imp"] == verb]["Perf"].tolist()
        if len(candidates) == 0:
            return None
        candidates_ipm = [FREQ_DICT.get(candidate) for candidate in candidates]
        candidates_ipm = [
            candidate for candidate in candidates_ipm if candidate is not None
        ]
        if len(candidates_ipm) == 0:
            return None
        best_ipm = candidates_ipm.index(max(candidates_ipm))
        word = candidates[best_ipm]

        return word

    def check_duration_adverbs(
        self, token_id: int, sentence: conllu.models.TokenList
    ) -> Union[bool, str]:
        """
        Receives verb id and sentence. Check if the sentence has duration adverb related to the verb.
        If it has, returns the lemma of the adverb. If not, returns False.
        """
        for word in sentence:
            if (
                word["lemma"] in ADVERBS
                and word["head"] == token_id
                and word["deprel"] == "advmod"
            ):
                return word["lemma"]
        return False

    def check_postfix_verbs(self, new_verb: str, old_verb: str) -> bool:
        """
        Checks new verb forb and old verb form to have corresponding reflexivity.
        If the verbs have the same reflexivity, return True. If not, returns False.
        """
        if new_verb.endswith("ся") and not old_verb.endswith("ся"):
            return False
        if old_verb.endswith("ся") and not new_verb.endswith("ся"):
            return False
        if new_verb.endswith("сь") and not old_verb.endswith("сь"):
            return False
        if old_verb.endswith("сь") and not new_verb.endswith("сь"):
            return False
        return True

    def has_repitition(
        self, token_id: int, sentence: conllu.models.TokenList
    ) -> Union[bool, str]:
        """
        Receives verb id and sentence. Check if the sentence has a repetition of
        a word or phrase related to the verb. If it has, returns phrase or word.
        If not, returns False.
        """
        for word in sentence:
            if word["lemma"] in REPETITION:
                if (
                    sentence[word["head"] - 1]["lemma"] in TIME_PERIODS
                    and sentence[word["head"] - 1]["deprel"] == "obl"
                    and sentence[sentence[word["head"] - 1]["id"]]["id"] == token_id
                ):
                    return " ".join(
                        [word["lemma"], sentence[word["head"] - 1]["lemma"]]
                    )
            elif word["lemma"] in SINGLE_REPETITION and word["head"] == token_id:
                return word["lemma"]
        return False

    def has_conj(self, token_id: int, sentence: conllu.models.TokenList) -> bool:
        """
        Receives verb id and sentence. Check if the verb has other conjugated verbs.
        If it has, returns the lemma of the adverb. If not, returns False.
        """
        for word in sentence:
            if (
                word["upos"] == "VERB"
                and word["head"] == token_id
                and word["deprel"] == "conj"
            ):
                return True
        return False

    def has_xcomp_csubj(self, token_id: int, sentence: conllu.models.TokenList) -> bool:
        """
        Receives word id and sentence. Check if the word has xcomp or
        csubj dependants. If it has, returns True If not, returns False.
        """
        for word in sentence:
            if (
                word["upos"] == "VERB"
                and word["head"] == token_id
                and (word["deprel"] == "xcomp" or word["deprel"] == "csubj")
            ):
                return True
        return False

    def has_verb_perf(self, token_id: int, sentence: conllu.models.TokenList) -> bool:
        """
        Receives word id and sentence. Checks if the word has a dependant
        the verb in perfective form. If it has, returns True. If not, returns False.
        """
        for word in sentence:
            if (
                word["upos"] == "VERB"
                and word["id"] != token_id
                and word["head"] == token_id
                # and word["deprel"] == "conj"
                and word["feats"] is not None
                and "Aspect" in word["feats"]
                and word["feats"]["Aspect"] == "Perf"
            ):
                return True
        return False

    def has_verb_dep(self, token_id: int, sentence: conllu.models.TokenList) -> bool:
        """
        Receives word id and sentence. Checks if the word has a dependant
        verb and deprel between these words if xcomp. If it is so,
        returns True. If not, returns False.
        """
        for word in sentence:
            if (
                word["upos"] == "VERB"
                and word["head"] == token_id
                and word["deprel"] == "xcomp"
            ):
                return True
        return False

    def conjugate_new_verb(self, old_verb: str, new_verb: str) -> Union[bool, str]:
        """
        Receives the word form of the target verb and infinitive of the new verb.
        Extracts verb inflection parameters of the target verb and inflect the
        new verb according to these parameters. If at least one of the parameters
        can not be applied to the new verb, returns False. Otherwise, returns
        inflected new verb.
        """
        grammemes = set()
        old_verb_pymorphy = self.morph.parse(old_verb)[0]
        if old_verb_pymorphy.tag.gender is not None:
            grammemes.add(old_verb_pymorphy.tag.gender)
        if old_verb_pymorphy.tag.number is not None:
            grammemes.add(old_verb_pymorphy.tag.number)
        if old_verb_pymorphy.tag.person is not None:
            grammemes.add(old_verb_pymorphy.tag.person)
        if old_verb_pymorphy.tag.tense is not None:
            grammemes.add(old_verb_pymorphy.tag.tense)
        if old_verb_pymorphy.tag.voice is not None:
            grammemes.add(old_verb_pymorphy.tag.voice)
        if old_verb_pymorphy.tag.mood is not None:
            grammemes.add(old_verb_pymorphy.tag.mood)
        if old_verb_pymorphy.tag.involvement is not None:
            grammemes.add(old_verb_pymorphy.tag.involvement)
        if len(grammemes) > 0:
            new_verb = self.morph.parse(new_verb)[0]
            new_verb = new_verb.inflect(grammemes)
            if new_verb is None:
                return False
            else:
                new_verb = new_verb.word
                return new_verb

    def check_comparative(
        self, token_id: int, sentence: conllu.models.TokenList
    ) -> Optional[bool]:
        """
        Receives verb id and sentence. Check that there are no comparison
        context related to the verb. If there is, returns comparison phrase or word.
        """
        for potential in sentence:
            if (
                potential["lemma"] == "чем"
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
        Receives a conllu.models.TokenList and outputs all possible minimal
        pairs for the phenomena.
        """
        altered_sentences = []

        for generation_func in [
            self.change_repetition_aspect,
            self.deontic_imp,
            self.change_duration_aspect,
        ]:
            generated = generation_func(sentence)
            if generated is not None:
                altered_sentences.extend(generated)

        if return_df:
            altered_sentences = pd.DataFrame(altered_sentences)

        return altered_sentences
