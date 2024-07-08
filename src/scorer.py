import torch
import numpy as np
import pandas as pd
from tqdm.auto import tqdm
from transformers import AutoModelForMaskedLM, AutoModelForCausalLM, AutoTokenizer
from typing import Union


PRETTY_MODEL_NAMES = {
    "ai-forever/ruBert-base": "rubert-base",
    "ai-forever/ruBert-large": "rubert-large",
    "ai-forever/ruRoberta-large": "ruroberta",
    "google/rembert": "rembert",
    "google-bert/bert-base-multilingual-cased": "mbert",
    "distilbert/distilbert-base-multilingual-cased": "distil-mbert",
    "FacebookAI/xlm-roberta-base": "xlmr-base",
    "FacebookAI/xlm-roberta-large": "xlmr-large",
    "microsoft/mdeberta-v3-base": "mdeberta",
    "ai-forever/rugpt3small_based_on_gpt2": "rugpt-s",
    "ai-forever/rugpt3medium_based_on_gpt2": "rugpt-m",
    "ai-forever/rugpt3large_based_on_gpt2": "rugpt-l",
    "ai-forever/ruGPT-3.5-13B": "ruGPT-3.5-13B",
    "sambanovasystems/SambaLingo-Russian-Base": "SambaLingo-Russian-Base",
    "facebook/xglm-1.7B": "xglm-1.7b",
    "facebook/xglm-4.5B": "xglm-4.5b",
    "facebook/xglm-7.5B": "xglm-7.5b",
    "bigscience/bloom-1b7": "bloom-1b7",
    "bigscience/bloom-3b": "bloom-3b",
    "bigscience/bloom-7b1": "bloom-7b1",
    "ai-forever/mGPT": "mGPT",
    "ai-forever/mGPT-13B": "mGPT-13B",
    "meta-llama/Llama-2-7b-hf": "Llama-2-7b-hf",
    "mistralai/Mistral-7B-v0.1": "mistral",
    "meta-llama/Llama-2-13b-hf": "Llama-2-13b-hf",
}


class Scorer:
    def __init__(self, model_name, ratios=[0.3, 0.4, 0.5, 0.6]):
        """
        :param model: str
            a HuggingFace model name
        :param ratios: list[float]
            ratios for min-k scoring
        """
        self.model_name = model_name
        self.pretty_model_name = PRETTY_MODEL_NAMES.get(
            self.model_name, self.model_name.replace("/", "-")
        )
        self.model, self.tokenizer = self.load_model_and_tokenizer()
        self.ratios = ratios

    def load_model_and_tokenizer(
        self,
    ) -> Union[AutoModelForCausalLM, AutoModelForMaskedLM, AutoTokenizer]:
        """
        :param model: str
            a HuggingFace model name
        """
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = (
            AutoModelForMaskedLM.from_pretrained(self.model_name).cuda().eval()
            if "bert" in self.model_name.lower()
            else AutoModelForCausalLM.from_pretrained(self.model_name).cuda().eval()
        )
        return model, tokenizer

    def get_pll(self, sentence):
        """
        Based on https://aclanthology.org/2022.emnlp-main.305:
            https://github.com/Yixiao-Song/SLING_Data_Code/blob/master/SLING_Code/utils.py#L86

        :param sentence: str
            an input sentence
        :param model: AutoModelForMaskedLM
            an encoder-only model
        :param tokenizer: AutoTokenizer
            the model tokenizer
        """
        token_log_probs = []
        MASK = self.tokenizer.mask_token_id
        with torch.no_grad():
            inputs = self.tokenizer(sentence, return_tensors="pt")
            if torch.cuda.is_available():
                for k, v in inputs.items():
                    inputs[k] = v.cuda()
            # skip first ([CLS]) and last ([SEP]) tokens for for loop
            for i in range(1, len(inputs["input_ids"][-1]) - 1, 1):
                # store a copy of token_id at mask_index position
                true_id = inputs["input_ids"][-1][i].item()
                # replace inputs['input_ids'][0, i] with [MASK] (id: 103)
                inputs["input_ids"][-1][i] = MASK
                outs = self.model.forward(**inputs)
                masked_token_logits = outs["logits"][-1][i]
                log_prob = torch.log_softmax(masked_token_logits, dim=-1)
                token_log_probs.append(log_prob[true_id].item())
                # replace [MASK] with true_id
                inputs["input_ids"][-1][i] = true_id
            sent_pll = sum(token_log_probs)
            neg_pppl = -1 * (torch.tensor(np.exp(-sent_pll / len(token_log_probs))))
            return token_log_probs, neg_pppl.item()

    def get_ll(self, sentence):
        """
        :param sentence: str
            an input sentence
        :param model: AutoModelForCausalLM
            an encoder-only model
        :param tokenizer: AutoTokenizer
            the model tokenizer
        """
        sentence = "</s>{}".format(sentence)
        input_ids = torch.tensor(self.tokenizer.encode(sentence)).unsqueeze(0).cuda()
        with torch.no_grad():
            outputs = self.model(input_ids, labels=input_ids)
        loss, logits = outputs[:2]

        # Apply softmax to the logits to get probabilities
        probabilities = torch.nn.functional.log_softmax(logits, dim=-1)
        all_prob = []
        input_ids_processed = input_ids[0][1:]
        for i, token_id in enumerate(input_ids_processed):
            probability = probabilities[0, i, token_id].item()
            all_prob.append(probability)
        return all_prob, torch.exp(loss).item()

    def score_with_min_k(self, example):
        """
        :param example: pd.Series or Dict
            a dataset example
        """
        source_sentence, target_sentence = (
            example["source_sentence"],
            example["target_sentence"],
        )
        func = self.get_pll if "bert" in self.model_name.lower() else self.get_ll
        # score the grammatical sentence
        source_all_prob, source_likelihood = func(sentence=source_sentence)
        example[f"{self.pretty_model_name}-ppl-s"] = source_likelihood
        # score the ungrammatical sentence
        target_all_prob, target_likelihood = func(sentence=target_sentence)
        example[f"{self.pretty_model_name}-ppl-t"] = target_likelihood
        # calculate min-k for both sentences, store results in the dataframe row
        for ratio in self.ratios:
            k_length_s = int(len(source_all_prob) * ratio)
            topk_prob_s = np.sort(source_all_prob)[:k_length_s]
            example[f"{self.pretty_model_name}-{ratio*100}-s"] = -np.mean(
                topk_prob_s
            ).item()
        return example

    def run(self, pool):
        """
        :param pool: pd.DataFrame
            a pool or a dataset of minimal pairs to score
        """
        scored_examples = []
        for i, example in tqdm(
            pool.iterrows(),
            total=pool.shape[0],
            desc=f"Scoring with: {self.model_name}",
        ):
            scored_example = self.score_with_min_k(example=example)
            scored_examples.append(scored_example)
        torch.cuda.empty_cache()
        return pd.DataFrame(scored_examples)
