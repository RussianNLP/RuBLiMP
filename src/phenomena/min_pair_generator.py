from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional

import conllu
import pandas as pd
import pymorphy2
from tqdm.auto import tqdm

from utils.constants import FREQ_DICT
from utils.utils import unify_alphabet, get_ipm_conllu, tree_depth


class MinPairGenerator(ABC):
    def __init__(self, name: str):
        self.name = name
        self.morph = pymorphy2.MorphAnalyzer()

    def read_data(self, datapath: str):
        """
        Read conllu file and return a generator object
        """
        data_file = open(datapath, "r", encoding="utf-8")
        return conllu.parse_incr(data_file)

    def generate_dataset(
        self, datapath: str, max_samples: int = float("inf"),
    ) -> pd.DataFrame:
        """
        Process dataset
        Generate all subtypes of minimal pairs
        for each sentence in the datafile
        """
        data = self.read_data(datapath)
        generated_data = []
        for i_checking, sent in enumerate(tqdm(data)):
            if i_checking >= max_samples:
                break
            
            # fallback
            try:
                min_pairs = self.get_minimal_pairs(sent, False)
            except Exception as e:
                print(e)
                min_pairs = None

            if min_pairs is not None:
                generated_data.extend(min_pairs)

        return generated_data

    def generate_dict(
        self,
        sentence: conllu.models.TokenList,
        target_sentence: str,
        phenomenon: str,
        phenomenon_subtype: str,
        source_word: str,
        target_word: str,
        source_word_feats: Dict[str, Any],
        target_word_feats: Dict[str, Any],
        feature: str,
        sentence_feats: Dict[str, Any] = None,
    ):
        """
        Generates annotation dictionary for sentence
        """
        generated_dict = {
            "sentence_id": sentence.metadata["sent_id"],
            "source_sentence": unify_alphabet(sentence.metadata["text"]),
            "target_sentence": unify_alphabet(target_sentence),
            "annotation": sentence.serialize(),
            "phenomenon": phenomenon,
            "phenomenon_subtype": phenomenon_subtype,
            "source_word": unify_alphabet(source_word),
            "target_word": unify_alphabet(target_word),
            "source_word_feats": source_word_feats,
            "target_word_feats": target_word_feats,
            "feature": feature,
            "length": len(sentence),
            "ipm": get_ipm_conllu(sentence, FREQ_DICT),
            "tree_depth": tree_depth(sentence.to_tree())
        }
        return generated_dict

    @abstractmethod
    def get_minimal_pairs(
        self, sentence: conllu.models.TokenList, return_df: bool
    ) -> List[Dict[str, Any]]:
        """
        Recieves a conllu.models.TokenList and outputs
        all possible minimal pairs for the phenomena
        """
        raise NotImplementedError
