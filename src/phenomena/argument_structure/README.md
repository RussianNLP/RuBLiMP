# Argument Structure

**Argument structure** phenomenon includes errors in the verb's argument structure. Similarily to BLiMP [(Warstadt et al., 2020)](https://arxiv.org/abs/1912.00582), we focus on cases where the animacy requirement for the arguments of a transitive verb is violated as a results of verb, subject or object replacement.

## Background

**Transitive verbs** comprise a group of verbs that have two or more arguments: an Agent, or someone performing the action, and a Patient, or someone or something directly affected by the action. In the simple case, Agent is the subject of a sentence, and Patient is the object.

    Mama myla ramu.
    'Mother cleaned the [window] frame.'
        
The word *mama* 'mother' in the sentenece above is the subject and Agent of the verb *myla* 'cleaned', while *ramu* 'window frame' is its direct object and Patient. 

In contrast to transitive verbs, **intransitive** verbs allow only for one argument -- an Agent, or a subject. Thus, **swapping the transitive verb with an intransitive one would be impossible** (even if they have the same meaning) and would create an ungrammatical sentence 100% of the time. That is why we use this as one of the strategies for creating our minimal pairs (see paradigm 1 below).

Another phenomenon we employ is that **most of the transitive verbs require the Agent (or subject) to be animate** [(Hopper and Thompson, 1980)](https://doi.org/10.2307/413757). This is relevant for several constructions with a transitive verb, and we include both the passive voice and regular constructions in our paradigms (see paradigms 2 and 3 below).

Additionally, we include more **complex cases, where the animacy of the object (direct or indirect) is required** as dictated by the sentence structure and semantics (see paradigms 4 and 5 below). 

See the [Implemetation](#implementation) section for more details on how the minimal pairs are created.


## Paradigms

We include several defferent paradigms for the phenomenon:

1. **Transitivity** (`transitive_verb`)

    - <u>Replacing the transitive verb with an intransitive one:</u> (`transitive_verb`)

        *Ya rasshchityval, chto budet mnogo smaylov i vse **zatsenyat** sarkazm.* \
        \**Ya rasshchityval, chto budet mnogo smaylov i vse **ascend** sarkazm.*

        **Translation:** \
        I figured there would be a lot of emoticons and everyone would **love** the sarcasm. \
        \*I figured there would be a lot of emoticons and everyone would **love** the sarcasm.

2. **Animate Subject of a Transitive Verb** (`transitive_verb_subject`)

    - <u>Swapping the subject and the direct object:</u> (`transitive_verb_subject_perm`)

       ***Ona** ostavila sumku na stole.* \
       \**Sumka ostavila yeye na stole.*

       **Translation:** \
       **She** left the bag on the table. \
       \***The bag** left her on the table.
        
    - <u>Replacing the subject with a random inanimate word:</u> (`transitive_verb_subject_rand`)
    
        ***Shante** teryaet soznanie i snova prosypaetsya v svoej krovati.* \
        \****Khimiya** teryaet soznanie i snova prosypaetsya v svoej krovati.*

        **Translation:** \
        **Chante** passes out and wakes up again in her bed. \
        \***Chemistry** passes out and wakes up again in her bed.

3. **Animate Subject of a Passive Verb** (`transitive_verb_passive`)

    - <u>Swapping the subject and the direct object of a verb in a passive construction:</u> (`,transitive_verb_passive_perm`)

        *Rama byla pomyta **mamoj**.* \
        \**Mama byla pomyta **ramoj**.*

        **Translation:** \
        The [window] frame was cleaned by **mom**. \
        \*Mom was cleaned by **the [window] frame**.

    - <u>Replacing the subject with a random inanimate word:</u> (`,transitive_verb_passive_rand`)
    
        *Al’tron byl unichtozhen **Vizhenom**, kotoryj prines sebya v zhertvu.* \
        \**Al’tron byl unichtozhen **navykom**, kotoryj prines sebya v zhertvu*

        **Translation:** \
        Ultron was destroyed by **Vision**, who sacrificed himself. \
        \*Ultron was destroyed by **the skill**, who sacrificed himself.

4. **Animate Direct Object of a Transitive Verb** (`transitive_verb_object`)

    - <u>Replacing the direct object with a random inanimate word:</u> (`transitive_verb_obj`)
        
        *Professor Farnsvort naznachaet **Lilu** kapitanom kosmicheskogo korablya.* \
        \**Professor Farnsvort naznachaet **krug** kapitanom kosmicheskogo korablya.*

        **Translation:**\
        Professor Farnsworth appoints **Leela** captain of the spaceship.\
        \*Professor Farnsworth appoints **circle** captain of the spaceship.

5. **Animate Indirect Object of a Transitive Verb** (`transitive_verb_iobject`)

    - <u>Swapping the subject and the indirect object of a verb:</u> (`transitive_verb_iobj_perm`)

        *Harry podaril **Dobby** nosok.* \
        \**Harry podaril **nosku** Dobby.*

        **Translation:** \
        Harry gave the sock to **Dobby**. \
        \*Harry gave Dobby to **the sock**.

    - <u>Replacing the indirect subject with a random inanimate word:</u> (`transitive_verb_iobj_rand`)
    
        *Nasledniki posle ego smerti prodali dvorets **Oginskomu**.* \
        \**Nasledniki posle ego smerti prodali dvorets **fragmentu**.*

        **Translation:** \
        After his death, the heirs sold the palace to **Oginsky**. \
        \*After his death, the heirs sold the palace to **the fragment**.
  
## Implementation 

- To generate minimal pairs for this paradigm we filter the sentences with a transitive verb in finite form. 
- In cases where the several arguments are swapped (paradigms 2-5), to isolate the phenomenon we make sure that the words to be swapped do not have any modifiers -- this ensures that no agreement errors appear after the perturbation. 
- When swapping words we make sure to inflect them to preserve sentence structure. For transitivity (paradigm 1) that includes replacing a verb with a verb of the same aspect, tense, number, person and gender values. For subjects and objects swaps that includes sampling the nouns with the same number and gender features as the original.
- Sometimes transitive verbs allow for inanimate nouns as subjects, but in most cases this is only true for the nouns that belong to specific semantic classes, that can be used metaphorically. To avoid those, we filter out the nouns that denote: 
    - heterogeneous groups of people ('group', 'army', 'crowd', etc.) or objects ('humanity', 'set', etc.)
    - organizations ('corporation', 'bank', etc.)
    - events ('elections', 'auction', etc.)
    - instruments, weapons and their parts ('gun', 'bullet', 'needle', etc.)
    - means of transport ('car', 'bus', 'plane', etc.)
    - space, place and time ('planet', 'city', 'spring', etc.)
    - names of places ('Moscow', 'Russia', 'Europe', etc.)
- To generate minimal pairs for the "Animate Indirect Object of a Transitive Verb" paradigm we search for sentences with an open clausal complement (`xcomp`) dependent on an animate object and following the said object. This way we filter out most of the sentences, that could be grammatical after the perturbation.

## Limitations

**Annotation**
        
In order to generate minimal pairs for the phenomenon, we employ additional semantic annotation from the [Russian National Corpus](https://ruscorpora.ru/en/) (RNC), provided to us by the authors on request. While neither the annotation nor the annotator used can be released publically, this code can still be be used to generate new data, provided you annotate your data manually or using a similar annotator.

**Inflection**

Due to the fact that we use token swaps as one of the strategies for minimal pair generation, and Russian language is a language with agreement, in most cases we swap not only token positions, but also their inflection features. This is required to ensure that the phenomenon is isolated and no additional errors are present. It can be argued, that the pairs are not minimal in this way, since several actions are performed to transform the grammatical sentence inot an ungrammatical one. However, it is not possible to isolate the phenomenon in other ways. To account for that we also include a random swap for most of the paradigms: we change the word in question for a randomly sampled one, having one alteration only. Nevertheless, this can introduce some semantical inconsistencies which we cannot account for.


## Related Work

- Alex Warstadt, Alicia Parrish, Haokun Liu, Anhad Mohananey, Wei Peng, Sheng-Fu Wang, and Samuel R. Bowman. 2020. [BLiMP: The Benchmark of Linguistic Minimal Pairs for English.](https://aclanthology.org/2020.tacl-1.25/) Transactions of the Association for Computational Linguistics, 8:377–392.
- Hopper, P. J., & Thompson, S. A. 1980. [Transitivity in Grammar and Discourse](https://doi.org/10.2307/413757). Language, 56(2), 251–299.


