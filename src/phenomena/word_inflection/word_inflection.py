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
from phenomena.word_inflection.constants import CONJUGATION_ENDINGS, DECLENSION


class WordInflection(MinPairGenerator):
    """
    Word inflection violations

    Perturbs sentences by changing either verb conjugation or noun (with or
    without adjective/participle/determiner dependants) declension ending
    to create word inflection violations.

    Example:
        On chitaet knigu. ('He is reading the book.')
          -> *On chitait knigu. ('He is read the book.')
    """

    def __init__(self):
        super().__init__(name="word_inflection")
        self.wrong_morphs = [
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

    def change_verb_conjugation(
        self, sentence: conllu.models.TokenList
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Finds sentences with verbs and replace the verb's ending
        to the corresponding  (in terms of gender, number, and person)
        ending of the opposite conjugation.

        Example:
        On chitaet knigu. ('He is reading the book.')
          -> *On chitait knigu. ('He is read the book.')
        """
        changed_sentences = []
        for token in sentence:
            if token["upos"] != "VERB":
                continue
            for ending in CONJUGATION_ENDINGS:
                if unify_alphabet(token["form"]).endswith(ending):
                    new_verb = (
                        token["form"][: -len(ending)] + CONJUGATION_ENDINGS[ending]
                    )
                    if self.morph.word_is_known(new_verb):
                        continue
                    changed_sentence = self.get_changed_sentence(
                        sentence,
                        new_verb,
                        token["form"],
                        token["feats"],
                        token["id"] - 1,
                        ending,
                        CONJUGATION_ENDINGS[ending],
                        "change_verb_conjugation",
                        "Conjugation",
                    )
                    changed_sentences.append(changed_sentence)

        return changed_sentences

    def change_declension_ending(
        self, sentence: conllu.models.TokenList
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Find sentences with nouns and replace nouns
        ending to the corresponding endings (in terms of
        case and number) of other declension paradigms.
        The new form is checked to not contain a series
        of letters that are not natural in Russian.
        If the target noun has a dependant adjective,
        determiner, or participle, the subtype of the
        phenomena will be "change_declension_ending_has_dep".
        Otherwise, "change_declension_ending".

        Example:
           U nego net stola. ('He does not have a table.')
                -> U nego net stoli. ('He does not have a tabl.')
        """
        changed_sentences = []
        for token in sentence:
            if token["upos"] != "NOUN":
                continue
            if token["feats"] is None:
                continue
            if "Number" not in token["feats"] or "Case" not in token["feats"]:
                continue
            declension_endings = DECLENSION.get(token["feats"]["Number"], [])
            if len(declension_endings) == 0:
                continue
            declension_endings = declension_endings.get(token["feats"]["Case"], [])
            if len(declension_endings) == 0:
                continue
            for ending in declension_endings:
                if not token["form"].endswith(ending):
                    continue
                for var in declension_endings[ending]:
                    new_word = token["form"][: -len(ending)] + var
                    if self.check_ending_rules(new_word):
                        continue
                    if self.morph.word_is_known(new_word):
                        continue
                    if self.check_noun_dependency(token, sentence):
                        subtype = "change_declension_ending_has_dep"
                    else:
                        subtype = "change_declension_ending"
                    changed_sentence = self.get_changed_sentence(
                        sentence,
                        new_word,
                        token["form"],
                        token["feats"],
                        token["id"] - 1,
                        ending,
                        var,
                        subtype,
                        "Ending",
                    )
                    changed_sentences.append(changed_sentence)

        return changed_sentences

    def change_sentence(
        self,
        sentence: conllu.models.TokenList,
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
        feats["control_form"] = unify_alphabet(
            sentence[sentence[word_id]["head"] - 1]["form"]
        )
        new_feats = feats.copy()
        new_feats["morpheme"] = list(new_morpheme)

        return new_word, new_sentence, feats, new_feats

    def check_noun_dependency(
        self, token: conllu.models.Token, sentence: conllu.models.TokenList
    ) -> bool:
        """
        Check if the noun token from the sentence
        has a determiner, participle, or adjective-dependant.
        If it has, returns True. Otherwise, returns False.
        """
        for potential_dep in sentence:
            if potential_dep["feats"] is None:
                continue
            if potential_dep["head"] == token["id"] and (
                potential_dep["upos"] == "ADJ"
                or potential_dep["upos"] == "DET"
                or (
                    potential_dep["upos"] == "VERB"
                    and "VerbForm" in potential_dep["feats"]
                    and potential_dep["feats"]["VerbForm"] == "Part"
                )
            ):
                return True
        return False

    def check_ending_rules(self, word: str) -> bool:
        """
        Check if the word contains a series of letters
        unnatural for the Russian language. The series of
        letters is contained in the self.wrong_morphs
        variable.
        """
        for var in self.wrong_morphs:
            if var in word:
                return True
        return False

    def get_changed_sentence(
        self,
        sentence: conllu.models.TokenList,
        new_word: str,
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
            token_form,
            new_word,
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

    def get_minimal_pairs(
        self, sentence: conllu.models.TokenList, return_df: bool
    ) -> List[Dict[str, Any]]:
        """
        Receives a conllu.models.TokenList and outputs
        all possible minimal pairs for the phenomena.
        """
        altered_sentences = []

        for generation_func in [
            self.change_verb_conjugation,
            self.change_declension_ending,
        ]:
            generated = generation_func(sentence)
            if generated is not None:
                altered_sentences.extend(generated)

        if return_df:
            altered_sentences = pd.DataFrame(altered_sentences)

        return altered_sentences
