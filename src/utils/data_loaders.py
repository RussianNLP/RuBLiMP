from collections import Counter
from itertools import product
import json
import pickle
import typing as T
from typing import Dict, Tuple, Union


VocabCounter = T.Counter[Tuple[str, ...]]


def load_vocab(
    filename: str = "./data/lemmas_enriched.json",
):
    with open(filename, "r", encoding="utf-8") as f:
        form2analyses = json.load(f)

    for form, analyses in form2analyses.items():
        for analysis in analyses:
            sem_str = analysis["sem"]
            analysis["sem"] = set(sem_str.split())

    return Counter(form2analyses)


def find_nouns_man_woman(lemmas2ana=None, anim_only=True):
    if not lemmas2ana:
        lemmas2ana = load_vocab()

    ana_differ_by_gender = {}
    for lemma, analyses in lemmas2ana.items():
        male_s = []
        feminine_s = []

        for ana in analyses:
            if ana["pos"] == "S":
                gram = ana["gr"].split(",")
                if anim_only and "anim" not in gram:
                    continue

                if "m" in gram:
                    male_s.append(set(gram))
                elif "f" in gram:
                    feminine_s.append(set(gram))

            for male_ana, feminine_ana in product(male_s, feminine_s):
                if male_ana - feminine_ana == {"m"}:
                    ana_differ_by_gender[lemma] = [male_ana, feminine_ana]
                    break

    return ana_differ_by_gender


def find_nouns_prof_commongender(lemmas2ana=None, anim_only=True):
    if not lemmas2ana:
        lemmas2ana = load_vocab()

    ana_prof_commongender = {}
    for lemma, analyses in lemmas2ana.items():
        for ana in analyses:
            if "t:prof" in ana["sem"] or "d:nag" in ana["sem"]:
                ana_prof_commongender[lemma] = ana

    return ana_prof_commongender


def find_nouns_semantically_plural(lemmas2ana=None, sem_tags=frozenset({"pt:set"})):
    if not lemmas2ana:
        lemmas2ana = load_vocab()

    semantically_plural_nouns = {}
    for lemma, analyses in lemmas2ana.items():
        for ana in analyses:
            if ana["pos"] == "S":
                if ana["sem"] & sem_tags:
                    semantically_plural_nouns[lemma] = analyses

    return semantically_plural_nouns
