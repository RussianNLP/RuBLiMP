import conllu
import json
import random
import pandas as pd
from copy import deepcopy
from typing import List, Dict, Any, Optional, Tuple

from phenomena.min_pair_generator import MinPairGenerator
from .utils import (
    get_verb_features,
    get_new_features,
    ud2pymorphy,
    update_feats,
)
from utils.utils import (
    capitalize_word,
    get_dependencies,
    get_pymorphy_parse,
    get_subject,
    get_conjuncts,
    filter_conjuncts,
)


class Tense(MinPairGenerator):
    """
    Tense violations

    Perturbs sentences by changing either verb tense or tense markers
    to create tense violations such as the use of a past tense marker
    with a verb in future tense

    Example:
        Вчера он сделал что-то ('Yesterday he did something')
          -> Вчера он сделает что-то 'Yesterday he will do something'
          -> Завтра он сделал что-то 'Tomorrow he did something'
    """

    def __init__(self):
        super().__init__(name="Tense")

        self.load_tense_markers()

    def load_tense_markers(self):
        """
        Load all required collocations and tense markers
        """
        self.tense_markers = {
            "Futr": ["завтра", "послезавтра"],
            "Past": ["вчера", "позавчера"],
        }
        self.adj_list = {
            "Futr": ["будущий", "наступающий", "грядущий", "завтрашний"],
            "Past": ["прошлый", "прошедший", "минувший", "вчерашний"],
        }

        # 3-grams from the Russian National Corpora
        self.collocations = {}

        for tense in ["past", "futr"]:
            with open(
                f"phenomena/tense/{tense}_tense_markers.json", encoding="utf-8"
            ) as f:
                self.collocations[tense.title()] = json.load(f)

    def check_marker_clash(
        self,
        marker: conllu.models.Token,
        current_verb: conllu.models.Token,
        ids: List[int],
        sentence: conllu.models.TokenList,
        deprels: Dict[str, List[conllu.models.Token]],
    ) -> Optional[conllu.models.Token]:
        """
        Check whether the verb has a modifier with tense semantics
        to determine conjuncts that have different modifiers, e.g.

        ВЧЕРА он был в Италии, а ЗАВТРА полетит в Германию
        'YESTERDAY he was in Italy and TOMORROW he will fly to Germany'
        """
        # marker is a verb's dependant
        if marker["head"] == current_verb["id"]:
            return marker

    def simple_tense_marker(
        self,
        current_verb: conllu.models.Token,
        ids: List[int],
        sentence: conllu.models.TokenList,
        deprels: Dict[str, List[conllu.models.Token]],
    ) -> Optional[Tuple[str, str]]:
        """
        Check for the simple tense markers such as
        вчера 'yesterday', завтра 'tomorrow', etc.
        """
        # find tense markers
        verb_tense = current_verb["feats"]["Tense"]
        tense_markers = self.tense_markers[
            "Futr" if verb_tense == "Fut" else verb_tense
        ]
        all_markers = list(
            filter(
                lambda x: x["lemma"] in tense_markers and x["deprel"] == "advmod",
                sentence,
            )
        )

        for marker in all_markers:
            # check there's no adposition (e.g. на завтра подготовил 'prepared for tomorrow')
            deps = deprels.get(marker["id"])
            if deps and any(x["upos"] == "ADP" for x in deps):
                continue

            # check for marker clashes
            simple_marker = self.check_marker_clash(
                marker, current_verb, ids, sentence, deprels
            )
            if simple_marker:
                return "simple", simple_marker["form"]

    def num_group_tense_marker(
        self,
        marker: conllu.models.Token,
        current_verb: conllu.models.Token,
        ids: List[int],
        sentence: conllu.models.TokenList,
        deprels: Dict[str, List[conllu.models.Token]],
    ) -> Optional[str]:
        """
        Find tense markers with numerals such as
        несколько дней назад 'a few days ago',
        пару недель назад 'a couple of weeks ago', etc.
        """
        full_marker = []

        # check for adverbs
        adverb = list(filter(lambda x: x["form"] == "назад", deprels[marker["id"]]))
        if len(adverb) != 0:
            full_marker.append(adverb[0])

            if any(x["upos"] == "ADP" for x in deprels[marker["id"]]):
                return

            # check for a numeral modifier
            numeral = list(filter(lambda x: x["upos"] == "NUM", deprels[marker["id"]]))
            if len(numeral) != 0:
                full_marker.extend([marker, numeral[0]])
                full_marker = sorted(full_marker, key=lambda x: x["id"])

                no_clash = self.check_marker_clash(
                    marker, current_verb, ids, sentence, deprels
                )

                if no_clash is not None:
                    return " ".join((x["form"] for x in full_marker))

    def adp_group_tense_marker(
        self,
        marker: conllu.models.Token,
        current_verb: conllu.models.Token,
        ids: List[int],
        sentence: conllu.models.TokenList,
        deprels: Dict[str, List[conllu.models.Token]],
    ) -> Optional[str]:
        """
        Find tense markers that are prepositional phrases such as
        в будущий раз 'next time', на будущей неделе 'next week',
        в прошлый вторник 'last Tuesday', на прошлой неделе 'last week', etc.
        """

        if not deprels.get(marker["id"]):
            return

        # check for marker case
        if not marker.get("feats") or marker.get("feats").get("Case") not in [
            "Loc",
            "Acc",
        ]:
            return

        deps = [t for t in deprels.get(marker["id"])]

        if (
            any(t for t in deps if t["deprel"] == "det")
            or len([t for t in deps if t["deprel"] == "amod"]) > 1
        ):
            return

        full_marker = []

        # check for adjectives with tense semantics (прошлый 'last', будущий 'future', etc.)
        adj_list = sum(self.adj_list.values(), [])
        adj = list(
            filter(
                lambda x: x["lemma"] in adj_list and x["deprel"] == "amod",
                deprels.get(marker["id"]),
            )
        )
        if len(adj) == 1:
            full_marker.append(adj[0])

            # check for adpostions
            adp = list(
                filter(
                    lambda x: x["upos"] == "ADP" and x["lemma"] in ["в", "на"],
                    deprels[marker["id"]],
                )
            )
            if len(adp) == 1:
                full_marker.extend([marker, adp[0]])
                full_marker = sorted(full_marker, key=lambda x: x["id"])

                no_clash = self.check_marker_clash(
                    marker, current_verb, ids, sentence, deprels
                )
                if no_clash:
                    return " ".join((x["form"] for x in full_marker))

    def check_tense_markers(
        self,
        current_verb: conllu.models.Token,
        conjs: List[conllu.models.Token],
        sentence: conllu.models.TokenList,
        deprels: Dict[str, List[conllu.models.Token]],
    ) -> Optional[Tuple[str, str]]:
        """
        Check current verb for tense markers in its dependants
        """
        # get indices for all the conjuncts
        ids = [verb["id"] for verb in conjs]

        # check for simple markers
        simple_marker = self.simple_tense_marker(current_verb, ids, sentence, deprels)
        if simple_marker:
            return simple_marker

        # check for time expressions
        # find possible heads
        possible_markers = [
            t
            for t in sentence
            if (
                t["head"] in [current_verb["id"]] + ids
                and t["deprel"].startswith(("obl", "advmod"))
                and t["upos"] in ["NOUN", "PART", "ADV"]
            )
        ]

        for marker in possible_markers:
            # check for dependants
            if marker["id"] not in deprels:
                continue

            # только что 'just now'
            if marker["upos"] == "PART" and marker["form"] == "только":
                deps = [t["form"] for t in deprels[marker["id"]]]
                if "что" in deps:
                    if "не" not in [x["form"] for x in deprels[current_verb["id"]]]:
                        time_expression = self.check_marker_clash(
                            marker, current_verb, ids, sentence, deprels
                        )
                        if time_expression:
                            return "expression", marker["form"] + " " + "что"

            if marker["upos"] == "NOUN":
                # expressions with numerals
                time_expression = self.num_group_tense_marker(
                    marker, current_verb, ids, sentence, deprels
                )
                if time_expression:
                    return "expression", time_expression

                # prepositional phrases
                time_expression = self.adp_group_tense_marker(
                    marker, current_verb, ids, sentence, deprels
                )
                if time_expression:
                    return "expression", time_expression

    def check_verb(
        self,
        token: conllu.models.Token,
        deprels: Dict[str, List[conllu.models.Token]],
    ) -> Optional[str]:
        """
        Check of a token is a verb suitable for the task,
        i.e. can be inflected and is in the correct form
        """
        # check if token is a verb
        if token["upos"] != "VERB":
            return

        # check for features
        if token.get("feats") is None:
            return

        # check the verb is finite (i.e. shows tense)
        verbform = token["feats"].get("VerbForm")
        if verbform and verbform != "Fin":
            return

        # check for tense
        verb_tense = token["feats"].get("Tense")
        if not verb_tense:
            return

        # check for aspect
        verb_aspect = token["feats"].get("Aspect")
        if not verb_aspect:
            return

        # check if its a perfective verb
        if verb_aspect == "Imp":
            return

        # check if its a verb in past/future tense
        if verb_tense == "Pres":
            return

        # check for bad annotation
        if verb_tense == "Fut" and token["feats"].get("Gender"):
            # a verb in future tense cannot express gender
            return
        if verb_tense == "Past" and token["feats"].get("Person"):
            # a verb in past tense cannot express person
            return

        # check for clausal complements that are verbs to account
        # for cases like собираюсь сделать 'am going to do' that can be
        # used with markers of both past and future tenses when changed
        # завтра я собираюсь/собирался сделать X
        # 'tomorrow I am/was going to do X'
        deps = deprels.get(token["id"], [])
        if any(
            (
                t["deprel"] == "xcomp"
                and t.get("feats")
                and t["upos"] == "VERB"
                and t.get("feats").get("VerbForm") == "Inf"
            )
            for t in deps
        ):
            return

        return verb_tense

    def change_verb_tense(
        self, sentence: conllu.models.TokenList
    ) -> List[Dict[str, Any]]:
        """
        Perturb sentence by changing verb tense when a certain
        tense marker is present

        Takes a verb in past/future tense  and checks for a
        tense marker in its dependants, replaces a verb with the
        same verb in 'opposite' tense if the form exists
        """
        altered_sents = []

        # a dictionary of all the dependencies
        deprels = get_dependencies(sentence)

        for token in sentence:
            # check if token is a verb with required features
            verb_tense = self.check_verb(token, deprels)
            if not verb_tense:
                continue

            # check for marker-verb dependence
            conj = get_conjuncts(token, deprels, sentence)
            conj = filter_conjuncts(conj, token, deprels)
            subtype_nverbs = "single" if len(conj) == 0 else "conj"

            # check for tense markers
            tense_marker = self.check_tense_markers(token, conj, sentence, deprels)
            if not tense_marker:
                continue
            else:
                subtype_marker, tense_marker = tense_marker

            # parse verb with pymorphy
            verb_parse = get_pymorphy_parse(token, "VERB", self.morph)
            if not verb_parse:
                continue

            # extract features for inflection
            # subject features (person, number, gender)
            subj_features = get_verb_features(token, deprels, conj)
            if subj_features is None:
                continue

            # add verb tense
            features = {"Tense": verb_tense}
            if len(subj_features) != 0:
                features.update(subj_features)

            # change verb features for inflection
            subj = get_subject(token, deprels, conj)
            new_features = get_new_features(
                features, subj[0] if len(subj) > 0 else None
            )
            if not new_features:
                continue

            # inflect verb
            new_verb = verb_parse.inflect(frozenset(ud2pymorphy(new_features).values()))
            if not new_verb:
                continue
            new_verb = new_verb.word

            # update sentence
            new_sentence = [
                capitalize_word(t["form"], new_verb)
                if t["id"] == token["id"]
                else t["form"]
                for t in sentence
            ]
            new_sentence = " ".join(new_sentence)

            source_features = deepcopy(token["feats"])
            source_features.update(subj_features)
            source_features["TenseMarker"] = tense_marker

            # save results
            altered_sents.append(
                self.generate_dict(
                    sentence=sentence,
                    target_sentence=new_sentence,
                    phenomenon=self.name,
                    phenomenon_subtype=f"{subtype_nverbs}_verb_tense_{subtype_marker}_marker",
                    source_word=token["form"],
                    target_word=new_verb,
                    source_word_feats=source_features,
                    target_word_feats=update_feats(token["feats"], new_features),
                    feature="Tense",
                )
            )
        return altered_sents

    def change_tense_marker(
        self, sentence: conllu.models.TokenList
    ) -> List[Dict[str, Any]]:
        """
        Perturb sentence by changing tense markers when a verb in past/future
        tense is present

        Takes a tense marker and checks if a verb in past/future tense
        or an imperfective verb in prerent tense is its head, replaces
        a marker with the corresponding 'opposite' tense marker
        """
        altered_sents = []

        # a dictionary of all the dependencies
        deprels = get_dependencies(sentence)

        for token in sentence:
            # get token head
            token_head = sentence[token["head"] - 1]

            # check if token head is a verb with required features
            if not token_head["upos"] == "VERB" or token_head.get("feats") is None:
                continue

            # check if token is a possible tense marker
            # only consider simple markers (e.g. вчера 'yesterday')
            # and a prepositional phrases (e.g. на прошлой неделе 'last week')
            if not token["lemma"] in sum(self.tense_markers.values(), []):
                if not (
                    token["deprel"].startswith(("obl", "advmod"))
                    and token["upos"] == "NOUN"
                    and token["id"] in deprels
                ):
                    continue

            # check that a verb is in the required form
            # ignore present tense verbs here to avoid historical present
            verb_tense = token_head.get("feats").get("Tense")
            mood = token_head.get("feats").get("Mood")
            if verb_tense not in ["Past", "Fut"]:
                continue

            # get source token features
            verb_tense = "Futr" if verb_tense == "Fut" else "Past"
            new_tense = "Futr" if verb_tense == "Past" else "Past"

            source_features = {
                "Verb": token_head["form"],
                "Mood": mood,
                "VerbTense": verb_tense,
                "Tense": verb_tense,
            }

            # simple marker
            if token["lemma"] in self.tense_markers[verb_tense]:
                token_id = token["id"]

                # replace marker with a corresponding one of the 'opposite' tense:
                # yesterday -> tomorrow, the day before -> the day after tomorow
                ind = self.tense_markers[verb_tense].index(token["lemma"])
                new_token = self.tense_markers[new_tense][ind]

                source_features["TenseMarker"] = token["form"]
                marker_type = "simple"
                exists = None

            # prepositional phrases
            else:
                # check if its a correct tense expression
                tense_expression = self.adp_group_tense_marker(
                    token, token_head, [token_head["id"]], sentence, deprels
                )
                if not tense_expression:
                    continue

                marker_type = "expression"

                # find the adjective that has time semantics
                adj_token = [
                    x
                    for x in deprels[token["id"]]
                    if x["lemma"] in self.adj_list[verb_tense]
                ]
                if len(adj_token) == 0:
                    continue

                adj_token = adj_token[0]
                token_id = adj_token["id"]

                # check for collocations
                # of a noun is in the list of collocations, replace the adjective
                # with the one from the list  else choose a random one from the list
                # Example:
                # раз 'time' appears in the corpora only next to
                # прошлый 'last' or будущий 'next', so we would choose out target
                # token from these options depending on the target tense,
                # i.e. прошлый 'last' when changing from future to past tense and
                # будущий 'next' otherwise

                if token["lemma"] in self.collocations[new_tense]:
                    new_token = random.choice(
                        self.collocations[new_tense][token["lemma"]]
                    )
                    exists = True
                else:
                    new_token = random.choice(self.adj_list[new_tense])
                    exists = False

                feats = adj_token["feats"]
                feats = {
                    k: v
                    for (k, v) in feats.items()
                    if k in ["Gender", "Number", "Case", 'Animacy']
                }
                
                if 'Case' not in feats:
                    continue
                   
                new_token_parse = self.morph.parse(new_token)[0]
                new_token_infl = new_token_parse.inflect(
                    frozenset(ud2pymorphy(feats).values())
                )
                if not new_token_infl:
                    continue
                new_token = new_token_infl.word
                full_marker = tense_expression.split()
                full_marker[full_marker.index(adj_token["form"])] = new_token
                full_marker = " ".join(full_marker)
                source_features["TenseMarker"] = full_marker

            # update sentence
            new_sentence = [
                capitalize_word(t["form"], new_token)
                if t["id"] == token_id
                else t["form"]
                for t in sentence
            ]
            new_sentence = " ".join(new_sentence)

            # update target token features
            new_features = source_features.copy()
            new_features["Tense"] = new_tense
            new_features["TenseMarker"] = (
                new_token if marker_type == "simple" else full_marker
            )
            new_features["CollocationExists"] = exists

            # save results
            altered_sents.append(
                self.generate_dict(
                    sentence=sentence,
                    target_sentence=new_sentence,
                    phenomenon=self.name,
                    phenomenon_subtype=f"tense_marker_{marker_type}",
                    source_word=token["form"]
                    if marker_type == "simple"
                    else adj_token["form"],
                    target_word=new_token,
                    source_word_feats=source_features,
                    target_word_feats=new_features,
                    feature="Tense",
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
        for perturbation_func in [self.change_verb_tense, self.change_tense_marker]:
            altered.extend(perturbation_func(sentence))

        return pd.DataFrame(altered) if return_df else altered
