import conllu
import pandas as pd
import pymorphy2
from typing import List, Dict, Optional, Tuple, Any
from phenomena.min_pair_generator import MinPairGenerator
from phenomena.government.constants import ADP_CASES, WH_STOP, MODAL_VERBS
from utils.constants import GRAMEVAL2PYMORPHY, PYMORPHY2GRAMEVAL
from utils.utils import capitalize_word, unify_alphabet


class Government(MinPairGenerator):
    """
    Government violations

    Perturbs sentences by changing object's case to create government violations.

    Examples:
        Petya prishel k Mashe (dat). ('Petya came to Masha.')
            -> *Petya prishel k Mashey (ins). ('Petya came via Masha.')
        Odobrenie Vasinoj (gen) raboty ego obradovalo. ('Approval of Vasya's work made him [Vasya] happy.')
            -> *Odobrenie Vasinu(dat) raboty ego obradovalo. ('Approval to Vasya's work made him [Vasya] happy.')
    """

    def __init__(self):
        """
        Initialization of PoS list to violate, PoS list to skip, pronouns to not violate
        when the object is in ins case, deprels to help skip numbers, determiners, etc.
        """
        super().__init__(name="government")
        self.pos_list = ["NOUN", "PRON"]
        self.stop_pos = ["NUM", "ADJ", "DET", "ADP"]
        self.stop_pron_ins = [
            "нею",
            "ею",
            "ей",
            "ней",
            "им",
            "ним",
            "ими",
            "ними",
            "мной",
            "мною",
        ]
        self.deprels_stop = [
            "amod",
            "det",
            "nmod",
            "nummod",
            "nummod:gov",
            "flat:name",
            "appos",
            "acl:relcl",
            "acl",
        ]

    def change_obj_ins_case(
        self,
        sentence: conllu.models.TokenList,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Finds sentences with verbs' direct object in instrumentalis case, changes instrumentalis to
        other cases (except nom, gen, and acc), checks the violated form to not overlap with any plural
        form of the word.

        Example:
            Masha pisala ruchkoy (ins). ('Masha wrote with a pen.')
                -> *Masha pisala ruchke (dat). ('Masha wrote to a pen.')
        """
        stop_cases = ["accs", "ablt", "nomn", "gent", "gen2"]
        changed_sentences = []
        pymorphy_cases = list(GRAMEVAL2PYMORPHY.values())
        pymorphy_cases = [case_ for case_ in pymorphy_cases if case_ not in stop_cases]
        changed_sentences = []
        stop_ids = self.get_stop_ids(sentence)
        for token in sentence:
            if self.check_dependencies(token["id"], sentence, self.stop_pos):
                continue
            if self.has_quotes(token["id"], sentence):
                continue
            if sentence[token["head"] - 1]["upos"] != "VERB":
                continue
            if (
                token["id"] not in stop_ids
                and token["feats"] is not None
                and "Case" in token["feats"]
            ) and (
                token["upos"] in self.pos_list
                or (
                    token["upos"] == "VERB"
                    and "VerbForm" in token["feats"]
                    and token["feats"]["VerbForm"] == "Part"
                )
            ):
                verb_id = token["head"] - 1
                if token["lemma"] in WH_STOP:
                    continue
                if sentence[verb_id]["form"].endswith("ся") or sentence[verb_id][
                    "form"
                ].endswith("сь"):
                    continue
                if (
                    sentence[verb_id]["feats"] is not None
                    and "VerbForm" in sentence[verb_id]["feats"]
                    and sentence[verb_id]["feats"]["VerbForm"] == "Inf"
                ):
                    continue
                if sentence[verb_id]["lemma"] in MODAL_VERBS:
                    continue
                if token["deprel"] == "obj":
                    if (
                        sentence[verb_id]["upos"] == "VERB"
                        and token["feats"]["Case"] == "Ins"
                    ):
                        word_case = "ablt"
                        if self.check_mods(token["id"], sentence, self.deprels_stop):
                            continue
                        parse_word = self.check_pymorphy_variants(token)
                        if parse_word is None:
                            continue
                        stop_forms = self.get_opposite_number_forms(token, parse_word)
                        for case_ in stop_cases:
                            stop_form = parse_word.inflect({case_})
                            if (
                                stop_form is not None
                                and stop_form.word not in stop_forms
                            ):
                                stop_forms.append(stop_form.word)
                        for case_ in pymorphy_cases:
                            if parse_word.inflect({case_}) is not None:
                                new_word = parse_word.inflect({case_}).word
                            else:
                                continue
                            if not self.morph.word_is_known(new_word):
                                continue
                            if new_word in self.stop_pron_ins:
                                continue
                            if (
                                new_word != token["form"].lower()
                                and new_word not in stop_forms
                            ):
                                stop_forms.append(new_word)
                                token["feats"]["upos"] = token["upos"]
                                (
                                    new_word,
                                    new_sentence,
                                    feats,
                                    new_feats,
                                ) = self.change_sentence(
                                    sentence,
                                    token["form"],
                                    new_word,
                                    token["id"] - 1,
                                    verb_id,
                                    token["feats"],
                                    case_,
                                )
                                changed_sentence = self.generate_dict(
                                    sentence,
                                    new_sentence,
                                    self.name,
                                    "verb_ins_object",
                                    token["form"],
                                    new_word,
                                    feats,
                                    new_feats,
                                    "Case",
                                )
                                changed_sentences.append(changed_sentence)
        return changed_sentences

    def change_nominalization_case(
        self, sentence: conllu.models.TokenList
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Finds sentences with nominalized verbs' (with -ние ending), and changes the case of
        the dependant noun or pronoun. If the word is in genetive case check the violated form
        to not overlap with instrumentalis and vice versa. Checks the violated form to not overlap
        with any plural form of the word

        Example:
            Odobrenie Vasinoj (gen) raboty ego obradovalo. ('Approval of Vasya's work made him [Vasya] happy.')
                -> *Odobrenie Vasinu(dat) raboty ego obradovalo. ('Approval to Vasya's work made him [Vasya] happy.')
        """
        endings = "ние"
        changed_sentences = []
        stop_ids = self.get_stop_ids(sentence)
        stop_cases_overlap = {
            "ablt": ["gent", "gen2", "ablt"],
            "gent": ["gen2", "ablt", "ablt"],
            "gen2": ["ablt", "gent", "ablt"],
        }
        for token in sentence:
            if self.check_dependencies(token["id"], sentence, self.stop_pos):
                continue
            pymorphy_cases = list(GRAMEVAL2PYMORPHY.values())
            if (
                token["feats"] is not None
                and token["id"] not in stop_ids
                and token["upos"] in self.pos_list
                and token["deprel"] == "nmod"
                and "Case" in token["feats"]
            ):
                word_id = token["head"] - 1
                deprels = self.get_dependencies(sentence)
                if token["id"] in deprels and any(
                    x["deprel"] == "case" for x in deprels[token["id"]]
                ):
                    continue
                if token["deprel"] == "nsubj":
                    continue
                if self.has_quotes(token["id"], sentence):
                    continue
                if token["lemma"] in WH_STOP:
                    continue
                if self.check_mods(token["id"], sentence, self.deprels_stop):
                    continue
                if (
                    sentence[sentence[word_id]["head"] - 1]["form"].endswith("ся")
                    or sentence[sentence[word_id]["head"] - 1]["form"].endswith("сь")
                ) and (sentence[sentence[word_id]["head"] - 1]["upos"] == "VERB"):
                    continue
                parse_token = self.morph.parse(sentence[word_id]["form"])[0].normal_form
                if parse_token.endswith(endings):
                    word_case = token["feats"]["Case"]
                    word_case = GRAMEVAL2PYMORPHY[word_case]
                    pymorphy_cases.remove(word_case)
                    parse_word = self.check_pymorphy_variants(token)
                    if parse_word is None:
                        continue
                    stop_forms = self.get_opposite_number_forms(token, parse_word)
                    if word_case == "gent" or word_case == "gen2":
                        datv = parse_word.inflect({"datv"})
                        if datv is not None:
                            stop_forms.append(datv.word)
                        if word_case in pymorphy_cases:
                            pymorphy_cases.remove("datv")
                    for case_ in stop_cases_overlap.get(word_case, []):
                        stop_form = parse_word.inflect({case_})
                        if case_ in pymorphy_cases:
                            pymorphy_cases.remove(case_)
                        if stop_form is not None and stop_form.word not in stop_forms:
                            stop_forms.append(stop_form.word)
                    for case_ in pymorphy_cases:
                        if parse_word.inflect({case_}) is not None:
                            new_word = parse_word.inflect({case_}).word
                        else:
                            continue
                        if not self.morph.word_is_known(new_word):
                            continue
                        if (
                            new_word != token["form"].lower()
                            and new_word not in stop_forms
                        ):
                            stop_forms.append(new_word)
                            token["feats"]["upos"] = token["upos"]
                            (
                                new_word,
                                new_sentence,
                                feats,
                                new_feats,
                            ) = self.change_sentence(
                                sentence,
                                token["form"],
                                new_word,
                                token["id"] - 1,
                                token["head"] - 1,
                                token["feats"],
                                case_,
                            )
                            changed_sentence = self.generate_dict(
                                sentence,
                                new_sentence,
                                self.name,
                                "nominalization_case",
                                token["form"],
                                new_word,
                                feats,
                                new_feats,
                                "Case",
                            )
                            changed_sentences.append(changed_sentence)
        return changed_sentences

    def change_prep_case(
        self, sentence: conllu.models.TokenList
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Finds sentences, where the noun or pronoun is the object of the verb and used with the preposition,
        changes the case of the object. If the preposition could be used with several cases, these cases
        are not used to create violated forms. Also, cases are not changed to nominative, genetive, and
        accusative. Checks the violated form to not overlap with any plural form of the word.

        Example:
            Petya prishel k Mashe (dat). ('Petya came to Masha.')
                -> *Petya prishel k Mashey (ins). ('Petya came via Masha.')
        """
        changed_sentences = []
        stop_ids = self.get_stop_ids(sentence)
        stop_cases = ["nomn", "gent", "gen2", "accs"]
        stop_cases_overlap = {
            "gent": ["loct", "gen2"],
            "loct": ["gent", "gen2"],
            "gen2": ["loct", "gent"],
        }
        for token in sentence:
            new_stop_pos = self.stop_pos.copy()
            new_stop_pos.remove("ADP")
            pymorphy_cases = list(GRAMEVAL2PYMORPHY.values())
            if self.check_dependencies_any(token["id"], sentence):
                continue
            if token["lemma"] == "как":
                continue
            if token["upos"] == "ADP" and token["deprel"] == "case":
                word_id = token["head"] - 1
                if token["id"] - 1 > word_id:
                    continue
                if self.check_dependencies_any(token["id"], sentence):
                    continue
                if self.check_dependencies(
                    sentence[word_id]["id"], sentence, new_stop_pos
                ):
                    continue
                if sentence[sentence[word_id]["head"] - 1]["upos"] != "VERB":
                    continue
                if sentence[sentence[word_id]["head"] - 1]["form"].endswith(
                    "ся"
                ) or sentence[sentence[word_id]["head"] - 1]["form"].endswith("сь"):
                    continue
                if (
                    sentence[sentence[word_id]["head"] - 1]["feats"] is not None
                    and "VerbForm" in sentence[sentence[word_id]["head"] - 1]["feats"]
                    and sentence[sentence[word_id]["head"] - 1]["feats"]["VerbForm"]
                    == "Inf"
                ):
                    continue
                if sentence[sentence[word_id]["head"] - 1]["lemma"] in MODAL_VERBS:
                    continue
                if (
                    sentence[word_id]["deprel"] == "nsubj"
                    or sentence[word_id]["deprel"] == "det"
                ):
                    continue
                if sentence[word_id]["lemma"] in WH_STOP:
                    continue
                if self.check_mods(
                    sentence[word_id]["id"], sentence, self.deprels_stop
                ):
                    continue
                if (
                    sentence[word_id]["feats"] is not None
                    and sentence[word_id]["id"] not in stop_ids
                    and "Case" in sentence[word_id]["feats"]
                ) and (
                    sentence[word_id]["upos"] in self.pos_list
                    or (
                        sentence[word_id]["upos"] == "VERB"
                        and sentence[word_id]["feats"] is not None
                        and "VerbForm" in sentence[word_id]["feats"]
                        and sentence[word_id]["feats"]["VerbForm"] == "Part"
                    )
                ):
                    if self.has_quotes(word_id + 1, sentence):
                        continue
                    word_case = sentence[word_id]["feats"]["Case"]
                    word_case = GRAMEVAL2PYMORPHY[word_case]
                    pymorphy_cases.remove(word_case)
                    parse_word = self.check_pymorphy_variants(sentence[word_id])
                    if parse_word is None:
                        continue
                    stop_forms = self.get_opposite_number_forms(
                        sentence[word_id], parse_word
                    )
                    if word_case == "gent" or word_case == "gen2":
                        datv = parse_word.inflect({"datv"})
                        if datv is not None:
                            stop_forms.append(datv.word)
                        if word_case in pymorphy_cases:
                            pymorphy_cases.remove("datv")
                    for case_ in stop_cases:
                        stop_form = parse_word.inflect({case_})
                        if stop_form is not None and stop_form.word not in stop_forms:
                            stop_forms.append(stop_form.word)
                    if token["lemma"] in ADP_CASES:
                        for case_ in ADP_CASES[token["lemma"]]:
                            if case_ in pymorphy_cases:
                                pymorphy_cases.remove(case_)
                            stop_form = parse_word.inflect({case_})
                            if (
                                stop_form is not None
                                and stop_form.word not in stop_forms
                            ):
                                stop_forms.append(parse_word.inflect({case_}).word)
                    for case_ in stop_cases_overlap.get(word_case, []):
                        stop_form = parse_word.inflect({case_})
                        if case_ in pymorphy_cases:
                            pymorphy_cases.remove(case_)
                        if stop_form is not None and stop_form.word not in stop_forms:
                            stop_forms.append(stop_form.word)
                    for case_ in pymorphy_cases:
                        if parse_word.inflect({case_}) is not None:
                            new_word = parse_word.inflect({case_}).word
                        else:
                            continue
                        if not self.morph.word_is_known(new_word):
                            continue
                        if (
                            new_word != sentence[word_id]["form"].lower()
                            and new_word not in stop_forms
                        ):
                            stop_forms.append(new_word)
                            sentence[word_id]["feats"]["upos"] = sentence[word_id][
                                "upos"
                            ]
                            (
                                new_word,
                                new_sentence,
                                feats,
                                new_feats,
                            ) = self.change_sentence(
                                sentence,
                                sentence[word_id]["form"],
                                new_word,
                                word_id,
                                sentence[word_id]["head"] - 1,
                                sentence[word_id]["feats"],
                                case_,
                            )
                            feats["adp_form"] = token["form"]
                            new_feats["adp_form"] = token["form"]
                            changed_sentence = self.generate_dict(
                                sentence,
                                new_sentence,
                                self.name,
                                "adp_government_case",
                                sentence[word_id]["form"],
                                new_word,
                                feats,
                                new_feats,
                                "Case",
                            )
                            changed_sentences.append(changed_sentence)
        return changed_sentences

    def change_obj_acc_case(
        self, sentence: conllu.models.TokenList
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Finds sentences with verbs' direct object in the accusative case, changes accusative to
        other cases (except nom), checks the violated form to not overlap with any plural form
        of the word.

        Example:
            Petya udaril ego (acc). ('Petya hit him.')
                -> *Petya udaril emu (dat). ('Petya hit to him.')
        """
        stop_cases = ["accs", "nomn"]
        changed_sentences = []
        stop_ids = self.get_stop_ids(sentence)
        pymorphy_cases = list(GRAMEVAL2PYMORPHY.values())
        pymorphy_cases = [case_ for case_ in pymorphy_cases if case_ not in stop_cases]
        for token in sentence:
            if self.check_dependencies(token["id"], sentence, self.stop_pos):
                continue
            if sentence[token["head"] - 1]["upos"] != "VERB":
                continue
            if (
                sentence[token["head"] - 1]["feats"] is not None
                and "VerbForm" in sentence[token["head"] - 1]["feats"]
                and sentence[token["head"] - 1]["feats"]["VerbForm"] == "Inf"
            ):
                continue
            if sentence[token["head"] - 1]["lemma"] in MODAL_VERBS:
                continue
            if self.has_quotes(token["id"], sentence):
                continue
            if self.check_mods(token["id"], sentence, self.deprels_stop):
                continue
            if (
                token["id"] not in stop_ids
                and token["feats"] is not None
                and "Case" in token["feats"]
            ) and (
                token["upos"] in self.pos_list
                or (
                    token["upos"] == "VERB"
                    and "VerbForm" in token["feats"]
                    and token["feats"]["VerbForm"] == "Part"
                )
            ):
                verb_id = token["head"] - 1
                if sentence[verb_id]["form"].endswith("ся") or sentence[verb_id][
                    "form"
                ].endswith("сь"):
                    continue
                if token["lemma"] in WH_STOP:
                    continue
                if token["deprel"] == "obj":
                    if (
                        sentence[verb_id]["upos"] == "VERB"
                        and token["feats"]["Case"] == "Acc"
                    ):
                        word_case = "accs"
                        parse_word = self.check_pymorphy_variants(token)
                        if parse_word is None:
                            continue
                        stop_forms = self.get_opposite_number_forms(token, parse_word)
                        for case_ in stop_cases:
                            stop_form = parse_word.inflect({case_})
                            if (
                                stop_form is not None
                                and stop_form.word not in stop_forms
                            ):
                                stop_forms.append(stop_form.word)
                        for case_ in pymorphy_cases:
                            if parse_word.inflect({case_}):
                                new_word = parse_word.inflect({case_}).word
                            else:
                                continue
                            if not self.morph.word_is_known(new_word):
                                continue
                            if (
                                new_word != token["form"].lower()
                                and new_word not in stop_forms
                            ):  # Бывает так, что разные падежи совпадают, исключаем такие варианты (в т.ч омонимию некоторых падежей с мн.ч аккузатива)
                                stop_forms.append(new_word)
                                token["feats"]["upos"] = token["upos"]
                                (
                                    new_word,
                                    new_sentence,
                                    feats,
                                    new_feats,
                                ) = self.change_sentence(
                                    sentence,
                                    token["form"],
                                    new_word,
                                    token["id"] - 1,
                                    verb_id,
                                    token["feats"],
                                    case_,
                                )
                                changed_sentence = self.generate_dict(
                                    sentence,
                                    new_sentence,
                                    self.name,
                                    "verb_acc_object",
                                    token["form"],
                                    new_word,
                                    feats,
                                    new_feats,
                                    "Case",
                                )
                                changed_sentences.append(changed_sentence)
        return changed_sentences

    def change_obj_gen_case(
        self,
        sentence: conllu.models.TokenList,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Finds sentences with verbs' direct object in genetive case, changes genetive to other
        cases (except nom, acc, dat), checks the violated form to not overlap with any plural
        form of the word.

        Example:
            Petya zhdet ispolneniya (gen) zhelanij. ('Petya is waiting for the fulfillment of [his] wishes.')
                -> *Petya zhdet ispolneniem (ins) zhelanij. ('Petya is waiting by the fulfillment of [his] wishes.')
        """
        stop_cases = ["gent", "gen2", "accs", "datv", "nomn"]
        stop_ids = self.get_stop_ids(sentence)
        changed_sentences = []
        changed_sentences = []
        pymorphy_cases = list(GRAMEVAL2PYMORPHY.values())
        pymorphy_cases = [case_ for case_ in pymorphy_cases if case_ not in stop_cases]
        for token in sentence:
            if self.check_dependencies(token["id"], sentence, self.stop_pos):
                continue
            if sentence[token["head"] - 1]["upos"] != "VERB":
                continue
            if (
                sentence[token["head"] - 1]["feats"] is not None
                and "VerbForm" in sentence[token["head"] - 1]["feats"]
                and sentence[token["head"] - 1]["feats"]["VerbForm"] == "Inf"
            ):
                continue
            if sentence[token["head"] - 1]["lemma"] in MODAL_VERBS:
                continue
            if self.has_quotes(token["id"], sentence):
                continue
            if (
                token["id"] not in stop_ids
                and token["feats"] is not None
                and "Case" in token["feats"]
            ) and (
                token["upos"] in self.pos_list
                or (
                    token["upos"] == "VERB"
                    and "VerbForm" in token["feats"]
                    and token["feats"]["VerbForm"] == "Part"
                )
            ):
                verb_id = token["head"] - 1
                if sentence[verb_id]["form"].endswith("ся") or sentence[verb_id][
                    "form"
                ].endswith("сь"):
                    continue
                if token["lemma"] in WH_STOP:
                    continue
                if self.check_mods(token["id"], sentence, self.deprels_stop):
                    continue
                if token["deprel"] == "obj":
                    if (
                        sentence[verb_id]["upos"] == "VERB"
                        and token["feats"]["Case"] == "Gen"
                    ):
                        word_case = "gent"
                        parse_word = self.check_pymorphy_variants(token)
                        if parse_word is None:
                            continue
                        stop_forms = self.get_opposite_number_forms(token, parse_word)
                        for case_ in stop_cases:
                            stop_form = parse_word.inflect({case_})
                            if (
                                stop_form is not None
                                and stop_form.word not in stop_forms
                            ):
                                stop_forms.append(stop_form.word)
                        for case_ in pymorphy_cases:
                            if parse_word.inflect({case_}) is not None:
                                new_word = parse_word.inflect({case_}).word
                            else:
                                continue
                            if not self.morph.word_is_known(new_word):
                                continue
                            if (
                                new_word != token["form"].lower()
                                and new_word not in stop_forms
                            ):
                                stop_forms.append(new_word)
                                token["feats"]["upos"] = token["upos"]
                                (
                                    new_word,
                                    new_sentence,
                                    feats,
                                    new_feats,
                                ) = self.change_sentence(
                                    sentence,
                                    token["form"],
                                    new_word,
                                    token["id"] - 1,
                                    verb_id,
                                    token["feats"],
                                    case_,
                                )
                                changed_sentence = self.generate_dict(
                                    sentence,
                                    new_sentence,
                                    self.name,
                                    "verb_gen_object",
                                    token["form"],
                                    new_word,
                                    feats,
                                    new_feats,
                                    "Case",
                                )
                                changed_sentences.append(changed_sentence)
        return changed_sentences

    def get_opposite_number_forms(
        self, token: conllu.models.Token, parse_word: pymorphy2.analyzer.Parse
    ) -> List[str]:
        """
        Receives conllu token and PyMophy2 parsed word, returns word forms of
        the opposite number in all the cases.
        """
        stop_forms = []
        if "Number" in token["feats"]:
            if token["feats"]["Number"] == "Sing":
                number = "plur"
            elif token["feats"]["Number"] == "Plur":
                number = "sing"
            for case_ in GRAMEVAL2PYMORPHY.values():
                stop_form = parse_word.inflect({case_, number})
                if stop_form is not None and stop_form.word not in stop_forms:
                    stop_forms.append(stop_form.word)
        return stop_forms

    def change_sentence(
        self,
        sentence: str,
        old_word: str,
        new_word: str,
        old_word_id: int,
        verb_id: int,
        token_feats: Dict[str, str],
        new_case: str,
    ) -> Tuple[Any]:
        """
        Changes word in sentence to incorrect.
        Returns changed sentence, old and new word feats.
        """
        new_word = capitalize_word(old_word, new_word)
        new_sentence = sentence.metadata["text"].split()
        new_sentence[old_word_id] = new_word
        new_sentence = " ".join(new_sentence)
        feats = token_feats.copy()
        feats["government_form"] = unify_alphabet(sentence[verb_id]["form"])
        new_feats = feats.copy()
        new_feats["Case"] = PYMORPHY2GRAMEVAL[new_case]
        return new_word, new_sentence, feats, new_feats

    def get_stop_ids(self, sentence: conllu.models.TokenList) -> List[int]:
        """
        Receives sentence and return ids of words
        that have agreement dependencies.
        """
        stop_ids = []
        for token in sentence:
            if (
                token["upos"] in self.pos_list
                and token["feats"] is not None
                and "Case" in token["feats"]
            ):
                head = sentence[token["head"] - 1]
                head_id = head["id"]
                if (
                    head["feats"] is not None
                    and "Case" in head["feats"]
                    and head["upos"] in self.pos_list
                    and head_id not in stop_ids
                ):
                    stop_ids.append(head_id)
        return stop_ids

    def check_number_pymorphy_ud(self, token: conllu.models.Token, new_word) -> bool:
        """
        Checks number from PyMorphy2 to be the same as in GramEval2020.
        """
        new_word = self.morph.parse(new_word)[0]
        if (
            token["feats"] is not None
            and "Number" in token["feats"]
            and new_word is not None
            and new_word.tag.number is not None
            and new_word.tag.number.capitalize() == token["feats"]["Number"]
        ):
            return True
        return False

    def get_dependencies(
        self, sentence: conllu.models.TokenList
    ) -> Dict[str, List[conllu.models.Token]]:
        """
        Extract a list of dependencies for each token in the sentence.
        """
        deprels = {}
        for i, token in enumerate(sentence, 1):
            if token["head"] not in deprels:
                deprels[token["head"]] = []
            deprels[token["head"]].append(token)
        return deprels

    def check_dependencies(
        self, token_id: int, sentence: conllu.models.TokenList, stop_pos: List[str]
    ) -> bool:
        """
        Checks if given token has dependant words, which PoS is not allowed.
        If it has, returns True. Otherwise, returns False.
        """
        for word in sentence:
            if word["upos"] in stop_pos and word["head"] == token_id:
                return True
        return False

    def check_dependencies_any(
        self, token_id: int, sentence: conllu.models.TokenList
    ) -> bool:
        """
        Checks if the given token has any dependant words. If it has, returns True.
        Otherwise, returns False.
        """
        for word in sentence:
            if word["head"] == token_id:
                return True
        return False

    def check_pymorphy_variants(
        self, token: conllu.models.TokenList
    ) -> Optional[pymorphy2.analyzer.Parse]:
        """
        Checks if the PyMorphy2 annotation variants overlap GramEval2020 annotation.
        Returns the annotation variant, which overlaps in number and case.
        """
        parse_word = self.morph.parse(token["form"])
        for p_word in parse_word:
            if (
                p_word.tag.number is not None
                and token["feats"] is not None
                and "Number" in token["feats"]
                and "Case" in token["feats"]
                and p_word.tag.number.capitalize() == token["feats"]["Number"]
                and p_word.normal_form is not None
                and p_word.normal_form == token["lemma"]
                and p_word.tag.case is not None
                and PYMORPHY2GRAMEVAL[p_word.tag.case] == token["feats"]["Case"]
            ):
                return p_word

    def has_quotes(self, token_id: int, sentence: conllu.models.TokenList) -> bool:
        """
        Checks if the word has dependant quote symbols. Returns True if it has.
        Otherwise, returns False.
        """
        for word in sentence:
            if word["head"] == token_id and word["form"] in [
                '"',
                "'",
                "(",
                ")",
                "«",
                "»",
                "“",
                "”",
                "‘",
                "’",
            ]:
                return True
        return False

    def check_mods(
        self, token_id: int, sentence: conllu.models.TokenList, deprels: List[str]
    ) -> bool:
        """
        Checks if the word in sentence has dependant words and connected with
        it via the given list of deprels or the word has participle dependant.
        If it has, returns True. Otherwise, returns False.
        """
        for word in sentence:
            if (word["head"] == token_id) and (
                word["deprel"] in deprels
                or (
                    word["upos"] == "VERB"
                    and word["feats"] is not None
                    and "VerbForm" in word["feats"]
                    and word["feats"]["VerbForm"] == "Part"
                )
            ):
                return True
        return False

    def get_minimal_pairs(
        self, sentence: conllu.models.TokenList, return_df: bool
    ) -> List[Dict[str, Any]]:
        """
        Recieves a conllu.models.TokenList and outputs
        all possible minimal pairs for the phenomena.
        """
        altered_sentences = []

        for generation_func in [
            self.change_obj_gen_case,
            self.change_obj_acc_case,
            self.change_nominalization_case,
            self.change_prep_case,
            self.change_obj_ins_case,
        ]:
            generated = generation_func(sentence)
            if generated is not None:
                altered_sentences.extend(generated)

        if return_df:
            altered_sentences = pd.DataFrame(altered_sentences)

        return altered_sentences
