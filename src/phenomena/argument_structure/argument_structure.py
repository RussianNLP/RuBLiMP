import conllu
import json
import random
import pandas as pd
from copy import deepcopy
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import pytorch_cos_sim

from typing import List, Dict, Any, Optional, Tuple

from phenomena.min_pair_generator import MinPairGenerator
from utils.utils import (
    get_dependencies,
    get_pymorphy_parse,
    get_conjuncts,
    filter_conjuncts,
    get_subject,
)
from .utils import (
    get_modifiers,
    get_verb_infl_feats,
    get_noun_inlf_feats,
    capitalize_word,
    check_permutaility,
    inflect_word,
    find_deprels,
    check_verb,
    get_verbs_rnc,
    get_inan_nouns_rnc,
)


class ArgumentStructure(MinPairGenerator):
    """
    Argument structure violations

    Perturbs sentences by changing transotive vers,
    their subjects and objects

    Examples:
        Девушка читала книгу ('A girl read a book')
          -> Книга читала девушку ('A book read a girl')
          -> Девушка ходила книгу ('A girl went a book')
    """

    def __init__(self, use_similarity=False, num_choices=50):
        super().__init__(name="ArgumentStructure")
        self.use_similarity = use_similarity
        self.num_choices = num_choices

        self.load()

    def load(self):
        """
        Load the vocabulary and similarity model if needed
        """
        vocab = pd.read_csv("./data/vocabulary.csv")
        vocab["lemma_lower"] = vocab["lemma"].str.lower()
        vocab = vocab.drop_duplicates("lemma", keep=False)

        # check -ся/-сь
        self.verbs = vocab[(vocab["pos"] == "V") & (vocab["transitivity"] == "intr")]
        self.verbs = self.verbs[
            ~self.verbs["lemma"].apply(lambda x: x[-2:] in ["сь", "ся"])
        ]
        self.verbs["len"] = self.verbs["lemma"].apply(len)

        self.nouns = vocab[
            (vocab["pos"] == "S")
            & (vocab["animacy"] == "inan")
            & (vocab["t:time"] != 1)
            & (vocab["t:time:season"] != 1)
            & (vocab["sc:hum"] != 1)
            & (vocab["pt:aggr"] != 1)
            & (vocab["t:org"] != 1)
            & (vocab["t:group"] != 1)
            & (vocab["t:inter"] != 1)
            & (vocab["t:tool:weapon"] != 1)
            & (vocab["t:tool"] != 1)
            & (vocab["t:tool:transp"] != 1)
            & (vocab["t:topon"] != 1)
            & (vocab["t:action"] != 1)
            & (vocab["t:org"] != 1)
            & (vocab["pt:set"] != 1)
            & (vocab["t:space"] != 1)
            & (vocab["t:topon"] != 1)
        ]
        self.nouns["len"] = self.nouns["lemma"].apply(len)

        if self.use_similarity:
            self.sim_model = SentenceTransformer("sentence-transformers/LaBSE")

    def calc_similarity(self, choice: str, source: str) -> float:
        """
        Calculate word similarity
        """
        source_emb = self.sim_model.encode(source)
        choice_emb = self.sim_model.encode(choice)

        sims = pytorch_cos_sim(source_emb, choice_emb)

        return sims.item()

    def get_similar_word(
        self, source_word: conllu.models.Token, infl_feats: List[str], tp: str
    ) -> Optional[str]:
        """
        Find the word most similar to the source
        """
        if tp == "verb":
            if source_word['feats'] is None or 'Aspect' not in source_word['feats']:
                return 
            vocab = get_verbs_rnc(self.verbs.copy(), source_word)
            pos = "INFN"
        else:
            if source_word['feats'] is None or 'Gender' not in source_word['feats']:
                return 
            vocab = get_inan_nouns_rnc(self.nouns.copy(), source_word)
            pos = "NOUN"

        if len(vocab) == 0:
            return

        i = 0
        while i < 3:
            if self.use_similarity:
                new_word = vocab.sample(self.num_choices)["lemma"]
                sim_scores = new_word.apply(
                    self.calc_similarity, source=source_word["lemma"]
                )
                new_word = new_word.iloc[sim_scores.argmax()]
            else:
                new_word = vocab.sample(1)["lemma"].iloc[0]
            new_word_parse = get_pymorphy_parse(new_word, pos, self.morph)
            if not new_word_parse:
                i += 1
                continue

            new_word = inflect_word(new_word_parse, infl_feats)
            if not new_word:
                i += 1
                continue

            return new_word

    def transitive_verb(
        self, sentence: conllu.models.TokenList
    ) -> List[Dict[str, Any]]:
        """
        Perturb sentence by changing a transitive verb for an intransitive one

        Example:
        Девушка читала книгу ('A girl read a book')
          -> Девушка ходила книгу ('A girl went a book')
        """
        altered_sents = []

        # a dictionary of all the dependencies
        deprels = get_dependencies(sentence)

        for token in sentence:
            parse = check_verb(token, self.morph)
            if not parse:
                continue

            obj = find_deprels("obj", token["id"], deprels)
            if not obj:
                continue

            subj = find_deprels("nsubj", token["id"], deprels)
            if not subj:
                continue

            infl_feats = get_verb_infl_feats(parse)
            if not infl_feats:
                continue

            new_verb = self.get_similar_word(token, infl_feats=infl_feats, tp="verb")
            if not new_verb:
                continue

            new_sentence = [
                capitalize_word(t, new_verb) if t["id"] == token["id"] else t["form"]
                for t in sentence
            ]
            new_sentence = " ".join(new_sentence)

            source_features = token["feats"].copy()
            source_features["Transitivity"] = "Tran"
            new_features = source_features.copy()
            source_features["Transitivity"] = "Intr"

            # save results
            altered_sents.append(
                self.generate_dict(
                    sentence=sentence,
                    target_sentence=new_sentence,
                    phenomenon=self.name,
                    phenomenon_subtype=f"transitive_verb",
                    source_word=token["form"],
                    target_word=new_verb,
                    source_word_feats=source_features,
                    target_word_feats=new_features,
                    feature="Transitivity",
                )
            )

        return altered_sents

    def transitive_verb_subj(
        self, sentence: conllu.models.TokenList
    ) -> List[Dict[str, Any]]:
        """
        Perturb sentence by changing an animate transitive verb subject
        for an inanimate one

        Example:
        Девушка читала книгу ('A girl read a book')
          -> Книга читала девушку ('A book read a girl')
          -> Машина читала книгу ('A car read a book')
        """
        altered_sents = []

        # a dictionary of all the dependencies
        deprels = get_dependencies(sentence)

        for token in sentence:
            parse = check_verb(token, self.morph)
            if not parse:
                continue

            obj = find_deprels("obj", token["id"], deprels)
            if (
                not obj
                or len(obj["form"]) < 2
                or obj["upos"] not in ["NOUN", "PROPN"]
                or obj["feats"] is None
                or ("Animacy" in obj["feats"] and obj["feats"]["Animacy"] != "Inan")
                or "Gender" not in obj["feats"]
                or get_modifiers(obj, deprels)
            ):
                continue

            subj = find_deprels("nsubj", token["id"], deprels)
            if (
                not subj
                or len(subj["form"]) < 2
                or subj["upos"] not in ["NOUN", "PROPN"]
                or subj["feats"] is None
                or ("Animacy" in subj["feats"] and subj["feats"]["Animacy"] == "Inan")
                or "Gender" not in subj["feats"]
                or get_modifiers(subj, deprels)
            ):
                continue

            subj_parse = get_pymorphy_parse(subj, ["NOUN"], self.morph)
            if not subj_parse or subj_parse.tag.animacy == 'inan':
                continue

            subj_infl_feats = get_noun_inlf_feats(subj)

            if (
                not check_permutaility(subj, obj)
                or subj['upos'] == 'PROPN'
                or any(x in subj_parse.tag for x in ['Surn', 'Name'])
            ):
                pass
            else:
                obj_parse = get_pymorphy_parse(obj, ["NOUN"], self.morph)
                if not obj_parse:
                    pass
                else:
                    obj_infl_feats = get_noun_inlf_feats(obj)

                    new_subj = inflect_word(obj_parse, subj_infl_feats)
                    new_obj = inflect_word(subj_parse, obj_infl_feats)
                    if not new_subj or not new_obj:
                        pass
                    else:
                        new_sentence = [
                            capitalize_word(t, new_subj, obj["upos"])
                            if t["id"] == subj["id"]
                            else capitalize_word(t, new_obj, subj["upos"])
                            if t["id"] == obj["id"]
                            else t["form"]
                            for t in sentence
                        ]
                        new_sentence = " ".join(new_sentence)

                        source_features = subj["feats"].copy()
                        source_features["index"] = subj["id"]
                        new_features = source_features.copy()
                        new_features["Animacy"] = "Inan"
                        new_features["index"] = obj["id"]

                        # save results
                        altered_sents.append(
                            self.generate_dict(
                                sentence=sentence,
                                target_sentence=new_sentence,
                                phenomenon=self.name,
                                phenomenon_subtype=f"transitive_verb_subject_perm",
                                source_word=subj["form"],
                                target_word=new_subj,
                                source_word_feats=source_features,
                                target_word_feats=new_features,
                                feature="Animacy",
                            )
                        )
            new_subj = self.get_similar_word(
                subj, infl_feats=subj_infl_feats, tp="noun"
            )
            if not new_subj:
                continue

            new_sentence = [
                capitalize_word(t, new_subj) if t["id"] == subj["id"] else t["form"]
                for t in sentence
            ]

            new_sentence = " ".join(new_sentence)

            source_features = subj["feats"].copy()
            source_features["index"] = subj["id"]
            new_features = source_features.copy()
            new_features["Animacy"] = "Inan"

            # save results
            altered_sents.append(
                self.generate_dict(
                    sentence=sentence,
                    target_sentence=new_sentence,
                    phenomenon=self.name,
                    phenomenon_subtype=f"transitive_verb_subject_rand",
                    source_word=subj["form"],
                    target_word=new_subj,
                    source_word_feats=source_features,
                    target_word_feats=new_features,
                    feature="Animacy",
                )
            )

        return altered_sents

    def transitive_verb_passive(
        self, sentence: conllu.models.TokenList
    ) -> List[Dict[str, Any]]:
        """
        Perturb sentence by changing an animate transitive verb agent
        for an inanimate one

        Example:
        Книга была прочитана девушкой ('A book was read by a girl')
          -> Девушка была прочитана книгой ('A girl was read by a book')
          -> Книга была прочитана машиной ('A book was read by a car')
        """
        altered_sents = []

        # a dictionary of all the dependencies
        deprels = get_dependencies(sentence)

        for token in sentence:
            parse = check_verb(token, self.morph, allow_part=True)
            if not parse:
                continue

            subj = find_deprels("nsubj:pass", token["id"], deprels)
            if (
                not subj
                or len(subj["form"]) < 2
                or subj["upos"] not in ["NOUN", "PROPN"]
                or subj["feats"] is None
                or ("Animacy" in subj["feats"] and subj["feats"]["Animacy"] != "Inan")
                or "Gender" not in subj["feats"]
                or get_modifiers(subj, deprels)
            ):
                continue

            agent = find_deprels("obl:agent", token["id"], deprels)
            if (
                not agent
                or len(agent["form"]) < 2
                or agent["feats"] is None
                or ("Animacy" in agent["feats"] and agent["feats"]["Animacy"] == "Inan")
                or "Gender" not in agent["feats"]
                or get_modifiers(agent, deprels)
            ):
                continue
            agent_parse = get_pymorphy_parse(agent, ["NOUN", "NPRO"], self.morph)
            if not agent_parse or agent_parse.tag.animacy == 'inan':
                continue

            agent_infl_feats = get_noun_inlf_feats(agent)
            if len(agent_infl_feats) == 0:
                continue

            if (
                not check_permutaility(agent, subj)
                or agent['upos'] == 'PROPN'
                or any(x in agent_parse.tag for x in ['Surn', 'Name'])
            ):
                pass
            else:
                subj_parse = get_pymorphy_parse(subj, ["NOUN", "NPRO"], self.morph)
                if not subj_parse:
                    pass
                else:
                    nsubj_infl_feats = get_noun_inlf_feats(subj)

                    new_subj = inflect_word(agent_parse, nsubj_infl_feats)
                    new_agent = inflect_word(subj_parse, agent_infl_feats)
                    if not new_subj or not new_agent:
                        pass
                    else:
                        new_sentence = [
                            capitalize_word(t, new_agent, subj["upos"])
                            if t["id"] == agent["id"]
                            else capitalize_word(t, new_subj, agent["upos"])
                            if t["id"] == subj["id"]
                            else t["form"]
                            for t in sentence
                        ]
                        new_sentence = " ".join(new_sentence)

                        source_features = agent["feats"].copy()
                        source_features["index"] = agent["id"]
                        new_features = source_features.copy()
                        new_features["Animacy"] = "Inan"
                        new_features["index"] = subj["id"]

                        # save results
                        altered_sents.append(
                            self.generate_dict(
                                sentence=sentence,
                                target_sentence=new_sentence,
                                phenomenon=self.name,
                                phenomenon_subtype=f"transitive_verb_passive_perm",
                                source_word=agent["form"],
                                target_word=new_agent,
                                source_word_feats=source_features,
                                target_word_feats=new_features,
                                feature="Animacy",
                            )
                        )

            new_agent = self.get_similar_word(
                agent, infl_feats=agent_infl_feats, tp="noun_filt"
            )
            if not new_agent:
                continue

            new_sentence = [
                capitalize_word(t, new_agent) if t["id"] == agent["id"] else t["form"]
                for t in sentence
            ]
            new_sentence = " ".join(new_sentence)

            source_features = agent["feats"].copy()
            source_features["index"] = agent["id"]
            new_features = source_features.copy()
            new_features["Animacy"] = "Inan"

            # save results
            altered_sents.append(
                self.generate_dict(
                    sentence=sentence,
                    target_sentence=new_sentence,
                    phenomenon=self.name,
                    phenomenon_subtype=f"transitive_verb_passive_rand",
                    source_word=agent["form"],
                    target_word=new_agent,
                    source_word_feats=source_features,
                    target_word_feats=new_features,
                    feature="Animacy",
                )
            )

        return altered_sents

    def transitive_verb_iobj(
        self, sentence: conllu.models.TokenList
    ) -> List[Dict[str, Any]]:
        """
        Perturb sentence by changing an animate transitive verb indirect object
        for an inanimate one

        Example:
        Мама подарила своей дочке книгу ('A mom bought her daughter a book')
          -> Мама подарила своей книге дочку ('A mom bought her book a daughter')
          -> Мама подарила своей машине книгу ('A mom bought her car a book')
        """
        altered_sents = []

        # a dictionary of all the dependencies
        deprels = get_dependencies(sentence)

        for token in sentence:
            parse = check_verb(token, self.morph)
            if not parse:
                continue

            subj = find_deprels("nsubj", token["id"], deprels)
            if (
                not subj
                or len(subj["form"]) < 2
                or subj["upos"] not in ["NOUN", "PROPN"]
                or subj["feats"] is None
                or ("Animacy" in subj["feats"] and subj["feats"]["Animacy"] == "Inan")
                or "Gender" not in subj["feats"]
            ):
                continue

            iobj = find_deprels("iobj", token["id"], deprels)
            if (
                not iobj
                or len(iobj["form"]) < 2
                or iobj["feats"] is None
                or ("Animacy" in iobj["feats"] and iobj["feats"]["Animacy"] == "Inan")
                or "Gender" not in iobj["feats"]
                or get_modifiers(iobj, deprels)
            ):
                continue

            obj = find_deprels("obj", token["id"], deprels)
            if (
                not obj
                or len(obj["form"]) < 2
                or obj["feats"] is None
                or ("Animacy" in obj["feats"] and obj["feats"]["Animacy"] != "Inan")
                or "Gender" not in obj["feats"]
                or get_modifiers(obj, deprels)
            ):
                continue

            iobj_parse = get_pymorphy_parse(iobj, "NOUN", self.morph)
            if not iobj_parse  or iobj_parse.tag.animacy == 'inan':
                continue

            iobj_infl_feats = get_noun_inlf_feats(iobj)

            if (
                not check_permutaility(obj, iobj)
                or iobj['upos'] == 'PROPN'
                or any(x in iobj_parse.tag for x in ['Surn', 'Name'])
            ):
                pass
            else:
                obj_parse = get_pymorphy_parse(obj, "NOUN", self.morph)
                if not obj_parse:
                    pass
                else:
                    obj_infl_feats = get_noun_inlf_feats(obj)

                    new_obj = inflect_word(iobj_parse, obj_infl_feats)
                    new_iobj = inflect_word(obj_parse, iobj_infl_feats)

                    if not new_obj or not new_iobj:
                        pass
                    else:
                        new_sentence = [
                            capitalize_word(t, new_obj, iobj["upos"])
                            if t["id"] == obj["id"]
                            else capitalize_word(t, new_iobj, obj["upos"])
                            if t["id"] == iobj["id"]
                            else t["form"]
                            for t in sentence
                        ]
                        new_sentence = " ".join(new_sentence)

                        source_features = iobj["feats"].copy()
                        source_features["index"] = iobj["id"]
                        new_features = source_features.copy()
                        new_features["Animacy"] = "Inan"
                        new_features["index"] = obj["id"]

                        # save results
                        altered_sents.append(
                            self.generate_dict(
                                sentence=sentence,
                                target_sentence=new_sentence,
                                phenomenon=self.name,
                                phenomenon_subtype=f"transitive_verb_iobj_perm",
                                source_word=iobj["form"],
                                target_word=new_iobj,
                                source_word_feats=source_features,
                                target_word_feats=new_features,
                                feature="Animacy",
                            )
                        )

            new_iobj = self.get_similar_word(
                iobj, infl_feats=iobj_infl_feats, tp="noun_filt"
            )
            if not new_iobj:
                continue

            new_sentence = [
                capitalize_word(t, new_iobj) if t["id"] == iobj["id"] else t["form"]
                for t in sentence
            ]
            new_sentence = " ".join(new_sentence)

            source_features = iobj["feats"].copy()
            source_features["index"] = iobj["id"]
            new_features = source_features.copy()
            new_features["Animacy"] = "Inan"

            # save results
            altered_sents.append(
                self.generate_dict(
                    sentence=sentence,
                    target_sentence=new_sentence,
                    phenomenon=self.name,
                    phenomenon_subtype=f"transitive_verb_iobj_rand",
                    source_word=iobj["form"],
                    target_word=new_iobj,
                    source_word_feats=source_features,
                    target_word_feats=new_features,
                    feature="Animacy",
                )
            )

        return altered_sents

    def transitive_verb_obj(
        self, sentence: conllu.models.TokenList
    ) -> List[Dict[str, Any]]:
        """
        Perturb sentence by changing an animate transitive verb object
        for an inanimate one

        Example:
        Девушка убедила водителя ехать ('A girl persuaded a driver to go')
          -> Девушка убедила машину ехать ('A girl persuaded a car to go')
        """
        altered_sents = []

        # a dictionary of all the dependencies
        deprels = get_dependencies(sentence)

        for token in sentence:
            parse = check_verb(token, self.morph)
            if not parse:
                continue

            subj = find_deprels("nsubj", token["id"], deprels)
            if (
                not subj
                or len(subj["form"]) < 2
                or subj["upos"] not in ["NOUN", "PROPN"]
                or subj["feats"] is None
                or ("Animacy" in subj["feats"] and subj["feats"]["Animacy"] == "Inan")
                or "Gender" not in subj["feats"]
                or get_modifiers(subj, deprels)
            ):
                continue

            obj = find_deprels("obj", token["id"], deprels)
            if (
                not obj
                or len(obj["form"]) < 2
                or obj["feats"] is None
                or ("Animacy" in obj["feats"] and obj["feats"]["Animacy"] == "Inan")
                or "Gender" not in obj["feats"]
                or get_modifiers(obj, deprels)
            ):
                continue

            xcomp = find_deprels("xcomp", token["id"], deprels)
            if (
                not xcomp
                or (xcomp["id"] - obj["id"]) != 1
                or (
                    xcomp["feats"] is not None
                    and (
                        (
                            "VerbForm" in xcomp["feats"]
                            and xcomp["feats"]["VerbForm"] == "Part"
                        )
                        or (
                            "Voice" in xcomp["feats"]
                            and xcomp["feats"]["Voice"] == "Pass"
                        )
                    )
                )
            ):
                continue

            obj_parse = get_pymorphy_parse(obj, "NOUN", self.morph)
            if not obj_parse:
                continue

            obj_infl_feats = get_noun_inlf_feats(obj)

            new_obj = self.get_similar_word(obj, infl_feats=obj_infl_feats, tp="noun")
            if not new_obj:
                continue

            new_sentence = [
                capitalize_word(t, new_obj) if t["id"] == obj["id"] else t["form"]
                for t in sentence
            ]
            new_sentence = " ".join(new_sentence)

            source_features = obj["feats"].copy()
            source_features["index"] = obj["id"]
            new_features = source_features.copy()
            new_features["Animacy"] = "Inan"

            # save results
            altered_sents.append(
                self.generate_dict(
                    sentence=sentence,
                    target_sentence=new_sentence,
                    phenomenon=self.name,
                    phenomenon_subtype=f"transitive_verb_obj",
                    source_word=obj["form"],
                    target_word=new_obj,
                    source_word_feats=source_features,
                    target_word_feats=new_features,
                    feature="Animacy",
                )
            )

        return altered_sents

    def get_minimal_pairs(
        self, sentence: conllu.models.TokenList, return_df: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Recieves a conllu.models.TokenList and outputs
        all possible minimal pairs for the phenomena
        """
        altered = []
        for perturbation_func in [
            self.transitive_verb,
            self.transitive_verb_subj,
            self.transitive_verb_passive,
            self.transitive_verb_iobj,
            self.transitive_verb_obj,
        ]:
            altered.extend(perturbation_func(sentence))

        return pd.DataFrame(altered) if return_df else altered