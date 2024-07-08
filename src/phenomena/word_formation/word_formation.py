import re
import ast
import conllu
import pandas as pd
import pymorphy2
from typing import List, Dict, Optional, Tuple, Any, Union
from phenomena.min_pair_generator import MinPairGenerator
from utils.utils import capitalize_word, unify_alphabet, get_list_safe
from utils.constants import (
    VOWELS,
    MINUS_VOICE,
    PLUS_VOICE,
    FREQ_DICT,
)
from phenomena.word_formation.constants import (
    PREFIXES_OVERLAP,
    LEXICAL_PREFIXES,
    SUPERLEXICAL_PREFIXES,
    DERIVATIONAL_SUFFIXES,
    INFLECTIONAL_SUFFIXES,
)
from itertools import permutations, cycle


class WordFormation(MinPairGenerator):
    """
    Word formation violations

    Perturbs sentences by either changing verb prefixes order, adding
    new prefix to verb or adding new suffix to noun to create word
    formation violations such as the following of external verb prefix
    after internal verb prefix or creating non-existent noun word.

    Example:
        Petya podustal na rabote. ('Petya got slightly tired at work')
            -> *Petya upodstal na rabote. ('Petya slightly got tired at work.')
    """

    def __init__(self):
        """
        Initialize the concordance of prefixes and roots,
        the concordance of suffixes and roots, the concordance
        of suffixes and PoS, dictionary for segmentation initial
        word form into morphemes, PoS to add new suffixes,
        series of characters thad do not occur in Russian
        words, impossible combination of prefixes.
        """
        super().__init__(name="word_formation")
        self.prefix_root_concordance = pd.read_csv(
            "data/prefix_root_concordance.csv",
            index_col="root",
            converters={1: ast.literal_eval},
        )
        self.suffix_root_concordance = pd.read_csv(
            "data/suffix_root_concordance.csv",
            index_col="root",
            converters={1: ast.literal_eval},
        )
        self.suffix_pos_concordance = pd.read_csv(
            "data/suffix_pos_concordance.csv",
            index_col="pos",
            converters={1: ast.literal_eval},
        )
        self.prefix_root_concordance = self.prefix_root_concordance.to_dict()[
            "prefixes"
        ]
        self.suffix_root_concordance = self.suffix_root_concordance.to_dict()[
            "suffixes"
        ]
        self.suffix_pos_concordance = self.suffix_pos_concordance.to_dict()["suffixes"]
        self.segmentation = pd.read_csv("data/segmentation.csv", index_col="word")
        self.segmentation = self.segmentation.to_dict()["segmentation"]
        self.pos_add_suffix = ["ADJ", "NOUN"]
        self.wrong_morphemes = [
            "ьь",
            "стьо",
            "стьа",
            "скств",
            "нькь",
            "ць",
            "кь",
            "ця",
            "сщ",
            "цщ",
            "ци",
            "щы",
            "жы",
            "шы",
            "чя",
            "щя",
            "шя",
            "чю",
            "щю",
            "шю",
            "щч",
            "йек",
        ]
        self.wrong_beginings = ["уот", "уо", "сис", "вв", "ви", "всс"]

    def add_verb_prefix(
        self, sentence: conllu.models.TokenList
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Finds sentences with the verb containing
        only one prefix. Adds new prefixes that co-occur
        with the root after and before the existing one.
        Skips verbs with roots pol, lozh, nya, nim.
        Checks new words to violate prefix stacking rules
        and not to contain a series of letters unnatural
        to Russian. Checks the new word not to be known
        by PyMorphy2. Checks the new word to have IPM less
        than 0.4.

        Example:
            Vasya zabyl zapisat' domashnee zadanie. ('Vasya forgot to write down the homework.')
                -> *Vasya zabyl prozapisat' domashnee zadanie. ('Vasya forgot to repeatedly write down the homework.')
        """
        changed_sentences = []
        for token in sentence:
            if token["upos"] != "VERB":
                continue
            morph_segments = self.get_morph_segmentation(
                token["lemma"], self.segmentation
            )
            if (
                len(morph_segments["ROOT"]) == 0
                or len(morph_segments["PREF"]) != 1
                or len(morph_segments["HYPH"]) > 0
            ):
                continue
            prefixes_word = morph_segments["PREF"]
            root = morph_segments["ROOT"][0]
            if root == "пол":
                continue
            if root == "лож" or root == "ня" or root == "ним":
                continue
            pos_pymorphy = self.morph.parse(token["lemma"])[0].tag.POS
            root_pos = "_".join([root, pos_pymorphy])
            prefixes = [
                pref
                for pref in LEXICAL_PREFIXES
                if pref in self.prefix_root_concordance.get(root_pos, [])
                and pref not in prefixes_word
            ]
            pref_to_remove = []
            for pref in pref_to_remove:
                prefixes.remove(pref)
            for i in range(len(prefixes)):
                for pref in PREFIXES_OVERLAP.get(prefixes[i], []):
                    if pref in prefixes and pref not in pref_to_remove:
                        pref_to_remove.append(pref)
            for pref_original in prefixes_word:
                if pref_original in PREFIXES_OVERLAP:
                    prefixes = [
                        pref
                        for pref in prefixes
                        if pref not in PREFIXES_OVERLAP.get(pref_original, [])
                    ]
            original_prefix = "".join(prefixes_word)
            var = []
            for pref in prefixes:
                if (pref[-1] == prefixes_word[0][0]) and pref[-1] in VOWELS:
                    continue
                if "ъ" not in pref:
                    var.append([pref, prefixes_word[0]])
                if prefixes_word[0] in LEXICAL_PREFIXES and "ъ" not in prefixes_word[0]:
                    if (prefixes_word[0][-1] == pref[0]) and pref[0] in VOWELS:
                        continue
                    var.append([prefixes_word[0], pref])
            for pref in var:
                if (pref[0][-1] in VOWELS and pref[1][0] in VOWELS) or (
                    pref[1][-1] in VOWELS and root[0] in VOWELS
                ):
                    continue
                if not self.check_prefixes(pref):
                    continue
                new_prefix_joined = "".join(pref)
                if not self.check_prefix_rules(new_prefix_joined, root):
                    continue
                new_verb = new_prefix_joined + token["form"][len(original_prefix) :]
                if self.check_wrong_beginings(new_verb):
                    continue
                new_verb_lemma = (
                    new_prefix_joined + token["lemma"][len(original_prefix) :]
                )
                if self.morph.word_is_known(new_verb) or self.morph.word_is_known(
                    new_verb_lemma
                ):
                    continue
                infn_new_verb = (
                    new_prefix_joined + token["lemma"][len(original_prefix) :]
                )
                ipm = FREQ_DICT.get(infn_new_verb, 0)
                if ipm >= 0.4:
                    continue
                changed_sentence = self.get_changed_sentence(
                    sentence,
                    token["lemma"],
                    new_verb_lemma,
                    new_verb,
                    token["form"],
                    token["feats"],
                    token["id"] - 1,
                    prefixes_word,
                    pref,
                    "add_verb_prefix",
                    "Prefix",
                )
                if pref[0] != prefixes_word[0]:
                    changed_sentence["target_word_feats"]["new_prefix_position"] = 0
                else:
                    changed_sentence["target_word_feats"]["new_prefix_position"] = 1
                changed_sentences.append(changed_sentence)

        return changed_sentences

    def change_order_verb_prefix(
        self, sentence: conllu.models.TokenList
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Finds sentences with the verb containing
        two prefixes. Change the order of verb prefixes.
        Skips verbs with roots pol, lozh, nya, nim.
        Checks new words to violate prefix stacking rules
        and not to contain a series of letters unnatural
        to Russian. Checks the new word not to be known
        by PyMorphy2. Check the new word to have IPM less
        than 0.4.

        Example:
            Petya podustal na rabote. ('Petya got slightly tired at work.')
                -> *Petya upodstal na rabote. ('Petya slightly got tired at work.')
        """
        changed_sentences = []
        for token in sentence:
            if token["upos"] != "VERB":
                continue
            morph_segments = self.get_morph_segmentation(
                token["lemma"], self.segmentation
            )
            if (
                len(morph_segments["ROOT"]) == 0
                or len(morph_segments["PREF"]) != 2
                or len(morph_segments["HYPH"]) > 0
            ):
                continue
            prefixes_word = morph_segments["PREF"]
            if prefixes_word[1] not in LEXICAL_PREFIXES:
                continue
            root = morph_segments["ROOT"][0]
            if root == "пол":
                continue
            if root == "лож" or root == "ня" or root == "ним":
                continue
            original_prefix = "".join(prefixes_word)
            var = [prefixes_word[1], prefixes_word[0]]
            if var[0] not in LEXICAL_PREFIXES:
                continue
            if (var[0][-1] in VOWELS and var[1][0] in VOWELS) or (
                var[1][-1] in VOWELS and root[0] in VOWELS
            ):
                continue
            if not self.check_prefix_rules(var[-1], root):
                continue
            if not self.check_prefixes(var):
                continue
            new_prefix = "".join(var)
            if new_prefix == original_prefix:
                continue
            if not self.check_prefix_rules(new_prefix, root[0]):
                continue
            new_verb = new_prefix + token["form"][len(original_prefix) :]
            if self.check_wrong_beginings(new_verb):
                continue
            new_verb_lemma = new_prefix + token["lemma"][len(original_prefix) :]
            if self.morph.word_is_known(new_verb) or self.morph.word_is_known(
                new_verb_lemma
            ):
                continue
            infn_new_verb = new_prefix + token["lemma"][len(original_prefix) :]
            ipm = FREQ_DICT.get(infn_new_verb, 0)
            if ipm >= 0.4:
                continue
            changed_sentence = self.get_changed_sentence(
                sentence,
                token["lemma"],
                new_verb_lemma,
                new_verb,
                token["form"],
                token["feats"],
                token["id"] - 1,
                prefixes_word,
                var,
                "change_verb_prefixes_order",
                "Prefix",
            )
            changed_sentences.append(changed_sentence)

        return changed_sentences

    def add_suffix(
        self, sentence: conllu.models.TokenList
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Finds sentences with nouns without amod
        or with adjectives. Adds new derivational prefixes
        that co-occur with the root to all possible positions in
        the initial form of the word. Checks that derivational
        prefixes are not positioned before inflectional.
        Sometimes, the ending of the initial form is different
        from the word used in the sentence, the function changes
        it back to the one corresponding to the form used in a sentence.
        Checks the new word not to be known by PyMorphy2. Checks the
        a new word to have IPM less than 0.4.

        Example:
            Vodoprovodnaya** voda ispol'zuetsya tol'ko dlya rukomojnikov i v celyah prigotovleniya pishchi. ('Tap water is used only for washing basins and food preparation purposes.')
                -> *Vodoprovodistnaya** voda ispol'zuetsya tol'ko dlya rukomojnikov i v celyah prigotovleniya pishchi. ('Tapous water is used only for washing basins and food preparation purposes.')
        """
        changed_sentences = []
        for token in sentence:
            if token["upos"] not in self.pos_add_suffix:
                continue
            if token["upos"] == "NOUN" and not self.check_noun_amod(token, sentence):
                continue
            morph_segments = self.get_morph_segmentation(
                token["lemma"], self.segmentation
            )
            if len(morph_segments["ROOT"]) == 0 or len(morph_segments["HYPH"]) > 0:
                continue
            suffixes_word = morph_segments["SUFF"]
            if len(suffixes_word) > 0 and not self.check_suffixes(suffixes_word):
                continue
            root = morph_segments["ROOT"][-1]
            ending = get_list_safe(0, morph_segments["END"])
            pos_pymorphy = self.morph.parse(token["form"])[0].tag.POS
            try:
                root_pos = "_".join([root, pos_pymorphy])
            except:
                continue
            suffixes = [
                suff
                for suff in self.suffix_root_concordance.get(root_pos, [])
                if suff not in suffixes_word
                and suff in DERIVATIONAL_SUFFIXES.keys()
                and suff in self.suffix_pos_concordance.get(pos_pymorphy, [])
            ]
            suff_to_remove = []
            for i in range(len(suffixes)):
                for suff in get_list_safe(
                    0, DERIVATIONAL_SUFFIXES.get(suffixes[i], [])
                ):
                    if suff in suffixes and suff not in suff_to_remove:
                        suff_to_remove.append(suff)
            for suff in suff_to_remove:
                suffixes.remove(suff)
            for suff_original in suffixes_word:
                suffixes = [
                    suff
                    for suff in suffixes
                    if suff
                    not in get_list_safe(
                        1, DERIVATIONAL_SUFFIXES.get(suff_original, [])
                    )
                    and suff
                    not in get_list_safe(
                        0, DERIVATIONAL_SUFFIXES.get(suff_original, [])
                    )
                ]
            original_suffix = "".join(suffixes_word)
            for suff in suffixes:
                for i in range(len(suffixes_word) + 1):
                    new_suffix = suffixes_word.copy()
                    if (
                        len(ending) == 0
                        and suff.endswith("ь")
                        and i == len(suffixes_word)
                        and len(token["form"].replace(root, "")) == 0
                    ):
                        new_suffix.insert(i, suff)
                    else:
                        if suff.endswith("ь"):
                            new_suffix.insert(i, suff[:-1])
                        else:
                            new_suffix.insert(i, suff)
                    next_suff = get_list_safe(i + 1, new_suffix)
                    prev_suff = get_list_safe(i - 1, new_suffix)
                    if (
                        len(ending) > 0
                        and i == len(suffixes_word)
                        and suff[-1] == ending[0]
                    ):
                        continue
                    if len(prev_suff) == 0 and root[-1] == suff[0]:
                        continue
                    if token["upos"] == "VERB" and prev_suff == "ть":
                        continue
                    if len(next_suff) > 0 and next_suff not in DERIVATIONAL_SUFFIXES:
                        continue
                    if len(prev_suff) > 0 and (
                        prev_suff not in DERIVATIONAL_SUFFIXES
                        or prev_suff[-1] == suff[0]
                    ):
                        continue
                    if get_list_safe(0, next_suff) in VOWELS and suff[-1] in VOWELS:
                        continue
                    if get_list_safe(-1, prev_suff) in VOWELS and suff[0] in VOWELS:
                        continue
                    if (
                        len(get_list_safe(0, next_suff)) > 0
                        and get_list_safe(0, next_suff) in VOWELS
                    ) and (
                        new_suffix[-1][-1] == "ь"
                        or new_suffix[-1][-1] == get_list_safe(0, next_suff)
                    ):
                        continue
                    if (
                        len(get_list_safe(-1, prev_suff)) > 0
                        and get_list_safe(-1, prev_suff) in VOWELS
                    ) and (
                        new_suffix[0][0] == get_list_safe(-1, prev_suff)
                        or new_suffix[0][0] == "ь"
                    ):
                        continue
                    if (
                        len(ending) == 2
                        and ending[0] in VOWELS
                        and (ending[1] in VOWELS or token["form"][-1] in VOWELS)
                        and new_suffix[-1][-1] in VOWELS
                    ):
                        continue
                    if (
                        (
                            len(ending) == 1
                            or len(token["form"].replace(token["lemma"], "")) == 1
                        )
                        and token["form"][-1] in ["я", "ю", "е"]
                        and (new_suffix[-1][-1] == "ь" or new_suffix[-1][-1] in VOWELS)
                    ):
                        continue
                    if (
                        i == len(suffixes_word)
                        and (
                            len(get_list_safe(0, ending)) > 0
                            and len(get_list_safe(0, next_suff)) == 0
                            and get_list_safe(0, ending) in VOWELS
                        )
                        and (
                            new_suffix[-1][-1] == "ь"
                            or new_suffix[-1][-1] == get_list_safe(0, ending)
                        )
                    ):
                        continue
                    new_suffix_joined = "".join(new_suffix)
                    if new_suffix_joined[0] == root[-1]:
                        continue
                    new_word = token["form"]
                    new_word = new_word.replace(
                        "".join([root, original_suffix]),
                        "".join([root, new_suffix_joined]),
                    )
                    if new_word.endswith("й") and new_word[-2] not in VOWELS:
                        new_word = new_word[:-1] + "ый"
                    if new_word.endswith("и") and new_word[-2] == "ц":
                        new_word = new_word[:-1] + "ы"
                    if self.check_wrong_morphemes(new_word):
                        continue
                    new_word_lemma = token["lemma"]
                    new_word_lemma = new_word_lemma.replace(
                        "".join([root, original_suffix]),
                        "".join([root, new_suffix_joined]),
                    )
                    if new_word == token["form"]:
                        continue
                    if (
                        len(morph_segments["ROOT"]) > 1
                        and len(new_word.split("-")) > 1
                        and self.morph.word_is_known(new_word.split("-")[-1])
                    ):
                        continue
                    if self.morph.word_is_known(new_word) or self.morph.word_is_known(
                        new_word_lemma
                    ):
                        continue
                    changed_sentence = self.get_changed_sentence(
                        sentence,
                        token["lemma"],
                        new_word_lemma,
                        new_word,
                        token["form"],
                        token["feats"],
                        token["id"] - 1,
                        suffixes_word,
                        new_suffix,
                        "add_new_suffix",
                        "Suffix",
                    )
                    changed_sentence["target_word_feats"]["new_suffix_position"] = i
                    changed_sentences.append(changed_sentence)

        return changed_sentences

    def check_suffixes(self, suffixes_word: list) -> bool:
        """
        Checks that the word contains only derivational and
        inflectional suffixes listed in our data. If it
        contains an unknown suffix, returns False. Otherwise,
        returns True.
        """
        for suff in suffixes_word:
            if (
                suff not in DERIVATIONAL_SUFFIXES.keys()
                and suff not in INFLECTIONAL_SUFFIXES
            ):
                return False
        return True

    def change_sentence(
        self,
        sentence: conllu.models.TokenList,
        old_lemma: str,
        new_lemma: str,
        old_word: str,
        new_word: str,
        word_id: str,
        old_morpheme: str,
        new_morpheme: Union[List[str], Tuple[str]],
        token_feats: Dict[str, str],
    ) -> Tuple[Any]:
        """
        Changes sentence and target word.
        Returns new sentence, changed target word,
        old word features and new word features.
        """
        new_word = capitalize_word(old_word, new_word)
        new_sentence = sentence.metadata["text"].split()
        new_sentence[word_id] = new_word
        new_sentence = " ".join(new_sentence)
        try:
            feats = token_feats.copy()
        except AttributeError:
            feats = {}
        feats["morpheme"] = old_morpheme
        feats["lemma"] = old_lemma
        feats["control_form"] = unify_alphabet(
            sentence[sentence[word_id]["head"] - 1]["form"]
        )
        new_feats = feats.copy()
        new_feats["morpheme"] = list(new_morpheme)
        new_feats["lemma"] = new_lemma

        return new_word, new_sentence, feats, new_feats

    def check_prefix_rules(self, prefix: str, root: str) -> bool:
        """
        Checks two string to follow Russian morphological and
        concordance rules: stunning and voicing and compulsory
        vowel after ъ 'solid sign'. If strings follows rules,
        returns True. Otherwise, returns False
        """
        if prefix[-1] == "ъ" and root[0] not in ["е", "ё", "ю", "я"]:
            return False
        if prefix[-1] == "з" and root[0] not in PLUS_VOICE and root[0] not in VOWELS:
            if prefix in ["рас", "раз", "из", "ис"]:
                return False
        if prefix[-1] == "с" and (root[0] not in MINUS_VOICE or root[0] in VOWELS):
            return False
        if prefix[-1] == root[0]:
            return False
        return True

    def check_prefixes(self, prefixes: Union[List[str], Tuple[str]]) -> bool:
        """
        Check the list of consecutive strings to follow the rules from
        `check_prefix_rules` function.
        """
        for idx, pref in enumerate(prefixes):
            try:
                if not self.check_prefix_rules(pref, prefixes[idx + 1]):
                    return False
            except IndexError:
                pass
        return True

    def check_noun_amod(
        self, token: conllu.models.Token, sentence: conllu.models.TokenList
    ) -> bool:
        """
        Checks the word to have amod adjective dependant. If the word
        has it, returns True. Otherwise, returns False.
        """
        for potential_adj in sentence:
            if (
                potential_adj["upos"] == "ADJ"
                and potential_adj["deprel"] == "amod"
                and potential_adj["head"] == token["id"]
            ):
                return True
        return False

    def get_changed_sentence(
        self,
        sentence: conllu.models.TokenList,
        old_lemma: str,
        new_lemma: str,
        new_verb: str,
        token_form: str,
        token_feats: Dict[str, str],
        token_id: int,
        old_morpheme: str,
        new_morpheme: str,
        phenomenon_subtype: str,
        feature: str,
    ) -> Dict[str, Any]:
        """
        Generates a dictionary with changed
        sentence and its' features (such as
        target word, phenomenon subtype, etc).
        """
        (
            new_word,
            new_sentence,
            feats,
            new_feats,
        ) = self.change_sentence(
            sentence,
            old_lemma,
            new_lemma,
            token_form,
            new_verb,
            token_id,
            old_morpheme,
            new_morpheme,
            token_feats,
        )
        changed_sentence = self.generate_dict(
            sentence,
            new_sentence,
            self.name,
            phenomenon_subtype,
            token_form,
            new_word,
            feats,
            new_feats,
            feature,
        )

        return changed_sentence

    def get_morph_segmentation(
        self, word: str, morph_dict: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Receives the initial form of the word and returns
        a dictionary with morphological segmentation of
        the word. If the word is not listed in our data,
        returns a dictionary with empty values.
        """
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
        except KeyError:
            pass

        return segmentation

    def check_wrong_morphemes(self, word: str) -> bool:
        """
        Checks words not to contain a series of letters
        that do not occur in Russian. If the word contains
        such a series of letters, returns True. Otherwise,
        returns False.
        """
        for wrong_morpheme in self.wrong_morphemes:
            if word.__contains__(wrong_morpheme):
                return True
        return False

    def check_wrong_beginings(self, word: str) -> bool:
        """
        Checks words not to begin with a series of letters
        that do not occur in Russian. If the word contains
        such a series of letters, returns True. Otherwise,
        returns False.
        """
        for wrong_morpheme in self.wrong_beginings:
            if word.startswith(wrong_morpheme):
                return True
        return False

    def get_minimal_pairs(
        self, sentence: conllu.models.TokenList, return_df: bool
    ) -> List[Dict[str, Any]]:
        """
        Receives a conllu.models.TokenList and outputs
        all possible minimal pairs for the phenomena.
        """
        altered_sentences = []

        for generation_func in [
            self.add_verb_prefix,
            self.change_order_verb_prefix,
            self.add_suffix,
        ]:
            generated = generation_func(sentence)
            if generated is not None:
                altered_sentences.extend(generated)

        if return_df:
            altered_sentences = pd.DataFrame(altered_sentences)

        return altered_sentences
