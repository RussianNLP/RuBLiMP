import pandas as pd
import json
from typing import Dict


GRAMEVAL2PYMORPHY = {
    "Nom": "nomn",
    "Gen": "gent",
    "Dat": "datv",
    "Acc": "accs",
    "Ins": "ablt",
    "Loc": "loct",
    "Par": "gen2",
    "Voc": "voct",
}


PYMORPHY2GRAMEVAL = {
    "nomn": "Nom",
    "gent": "Gen",
    "datv": "Dat",
    "accs": "Acc",
    "ablt": "Ins",
    "loct": "Loc",
    "gen2": "Par",
    "voct": "Voc",
    "loc2": "Loc"
}

CONLLU_FEAT2PYMORPHY_TAGFEAT = {
    "nom": "nomn", "gen": "gent", "par": "gen2", "dat": "datv", "acc": "accs",
        "ins": "ablt", "loc": "loct", "voc": "voct",
    "fem": "femn",
    "1": "1per", "2": "2per", "3": "3per",
    "fut": "futr",
}


VOWELS = ["а", "о", "и", "ы", "у", "э", "ё", "е", "я"]


MINUS_VOICE = ["к", "п", "с", "т", "ф", "х", "ц", "ч", "ш", "щ"]


PLUS_VOICE = ["б", "в", "г", "д", "ж", "з", "й", "л", "м", "н", "р"]


FREQ_DICT = pd.read_csv("data/freqrnc2011.csv", sep="\t")
FREQ_DICT = dict(zip(FREQ_DICT["Lemma"].tolist(), FREQ_DICT["Freq(ipm)"].tolist()))
FREQ_DICT = {k: float(v) for k, v in FREQ_DICT.items()}


ASPECT_VERBS = pd.read_csv("data/aspect_pair_zal.csv")

MORPH_SEGMENTATION = pd.read_csv("data/segmentation.csv")

