import os
import gc
import logging
import pandas as pd
from tqdm.auto import tqdm
from argparse import ArgumentParser
from phenomena.aspect.aspect import Aspect
from phenomena.tense.tense import Tense
from phenomena.negation.negation import Negation
from phenomena.reflexives.reflexives import Reflexives
from phenomena.government.government import Government
from phenomena.agreement.agreement import Agreement
from phenomena.word_formation.word_formation import WordFormation
from phenomena.word_inflection.word_inflection import WordInflection
from phenomena.argument_structure.argument_structure import ArgumentStructure


EXTENSION = ".conllu"
OUTPUT_EXTENSION = ".tsv"

PHENOMENON2GENERATOR = {
    "aspect": Aspect,
    "tense": Tense,
    "negation": Negation,
    "reflexives": Reflexives,
    "government": Government,
    "word_formation": WordFormation,
    "word_inflection": WordInflection,
    "argument_structure": ArgumentStructure,
    "agreement": Agreement,
}


def create_logger(logging_fdir: str, log_fname: str):
    os.makedirs(logging_fdir, exist_ok=True)
    log_fname = os.path.join(logging_fdir, log_fname)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(log_fname)
    logger.addHandler(file_handler)


def main(phenomenon: str, data_fname: str, output_fdir_name: str, sample: bool):
    generator = PHENOMENON2GENERATOR[phenomenon]()
    output_fdir = os.path.join(output_fdir_name, phenomenon)
    os.makedirs(output_fdir, exist_ok=True)
    if sample:
        shard_dataset = generator.generate_dataset(datapath=data_fname, max_samples=100)
    else:
        shard_dataset = generator.generate_dataset(datapath=data_fname)
    shard_dataframe = pd.DataFrame(shard_dataset)
    output_fpath = os.path.join(output_fdir, data_fname + OUTPUT_EXTENSION)
    shard_dataframe.to_csv(output_fpath, sep="\t", index=False)
    message = (
        f"Generated {shard_dataframe.shape[0]} pairs.\nShard name: {data_fname}.\n"
    )
    logging.info(message)
    del shard_dataframe, shard_dataset
    gc.collect()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--phenomenon", choices=PHENOMENON2GENERATOR.keys(), required=True, type=str
    )
    parser.add_argument("--data_fname", required=False, type=str)
    parser.add_argument(
        "--output_fdir_name", required=False, default="generated_data", type=str
    )
    parser.add_argument("--sample", required=False, default=False, type=bool)
    args = parser.parse_args()
    main(
        phenomenon=args.phenomenon,
        data_fname=args.data_fname,
        output_fdir_name=args.output_fdir_name,
        sample=args.sample,
    )
