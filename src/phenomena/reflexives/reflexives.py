import conllu
import pandas as pd
import os
import pymorphy2
from typing import List, Dict, Optional, Any, Union
from phenomena.min_pair_generator import MinPairGenerator
from utils.utils import unify_alphabet, capitalize_word


class Reflexives(MinPairGenerator):
    """
    Reflexives violations

    Perturbs sentences by replacing a personal pronoun possessor
    with a reflexive pronoun in sentences, where the possessor is a pronoun
    and is encoded as the object of the locative pronoun u 'by',
    to create reflexive violations

    Example:
        U nego byli druz'ya ('He had friends.')
            -> *U sebya bylu druz'ya('Self had friends.')
    """

    def __init__(self):
        """
        Initialize allowed PoS of the possessor
        and allowed verbs
        """
        super().__init__(name="reflexives")
        self.pos = ["NOUN", "PROPN", "PRON"]
        self.verbs = ["быть", "есть"]

    def external_posessor(
        self,
        sentence: conllu.models.TokenList,
    ) -> Optional[List[Dict[str, str]]]:
        """
        Finds sentences where possessor is encoded as
        the object of locative pronoun and changes the possessor
        to a reflexive pronoun. The reflexive must not
        have modifiers, must follow the locative pronoun
        and be in the span between 1 and 10 tokens from it.

        Example:
            U nih est' mashina. ('They have a car (lit. By them is a car).')
                -> *U sebya est' mashina. ('Self have a car (lut. By self is a car).')
        """
        changed_sentences = []
        for token in sentence:
            if token["upos"] not in self.pos:
                continue
            if token["form"] == "себя":
                continue
            if self.has_modifiers(token["id"], sentence):
                continue
            prep_pos = self.has_u(token["id"], sentence)
            if not prep_pos:
                continue
            if (
                token["feats"] is not None
                and "Case" in token["feats"]
                and token["feats"]["Case"] != "Gen"
            ):
                continue
            if token["deprel"] not in ["root", "obl"]:
                continue
            if token["deprel"] == "obl":
                u_diff = sentence[token["head"] - 1]["id"] - prep_pos
                if (
                    sentence[token["head"] - 1]["upos"] != "VERB"
                    or u_diff < 1
                    or u_diff > 10
                ):
                    continue
                if sentence[token["head"] - 1]["lemma"] not in self.verbs:
                    continue
                nsubj = self.has_nsubj(sentence[token["head"] - 1]["id"], sentence)
                if nsubj:
                    if nsubj < prep_pos:
                        continue
            elif token["deprel"] == "root":
                cop_pos = self.has_cop(token["id"], sentence)
                if sentence[cop_pos - 1]["lemma"] not in self.verbs:
                    continue
                if not cop_pos:
                    continue
                u_diff = cop_pos - prep_pos
                if u_diff < 1 or u_diff > 10:
                    continue
                nsubj = self.has_nsubj(token["id"], sentence)
                if nsubj:
                    if nsubj < prep_pos:
                        continue
            new_word = "себя"
            new_sentence = sentence.metadata["text"].split(" ")
            new_word = unify_alphabet(new_word)
            new_sentence[token["id"] - 1] = new_word
            new_sentence = " ".join(new_sentence)
            if token["feats"] is not None:
                feats = token["feats"].copy()
                new_feats = token["feats"].copy()
            else:
                feats = {}
                new_feats = {}
            feats["lemma"] = token["lemma"]
            feats["position"] = token["id"]
            new_feats["lemma"] = new_word
            new_feats["position"] = token["id"]
            changed_sentence = self.generate_dict(
                sentence,
                new_sentence,
                self.name,
                "external_posessor",
                token["form"],
                new_word,
                feats,
                new_feats,
                "lemma",
            )
            changed_sentences.append(changed_sentence)
        return changed_sentences

    def has_u(self, token_id, sentence) -> Union[int, bool]:
        """
        Finds a locative pronoun u 'by' that is dependent on the
        given token. If it is presented in a sentence, returns the
        id of a locative pronoun. Otherwise, returns False.
        """
        for word in sentence:
            if word["head"] == token_id and word["lemma"] == "у":
                return word["id"]
        return False

    def has_nsubj(self, token_id, sentence) -> Union[int, bool]:
        """
        Finds a "subj" dependant of the given token. If it is
        presented in a sentence, returns the id of a "nsubj".
        Otherwise, returns False.
        """
        for word in sentence:
            if word["head"] == token_id and word["deprel"] == "nsubj":
                return word["id"]
        return False

    def has_cop(self, token_id, sentence) -> Union[int, bool]:
        """
        Finds a "cop" dependent on the given token. If it is
        presented in a sentence, returns the id of a "cop".
        Otherwise, returns False.
        """
        for word in sentence:
            if word["head"] == token_id and word["deprel"] == "cop":
                return word["id"]
        return False

    def has_modifiers(self, token_id, sentence) -> bool:
        """
        Finds a "cop" dependant on the given token. If it is
        presented in a sentence, returns the id of a "cop".
        Otherwise, returns False.
        """
        for word in sentence:
            if word["head"] == token_id and word["deprel"] in ["det", "nmod", "amod"]:
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

        for generation_func in [self.external_posessor]:
            generated = generation_func(sentence)
            if generated is not None:
                altered_sentences.extend(generated)

        if return_df:
            altered_sentences = pd.DataFrame(altered_sentences)

        return altered_sentences
