# Aspect

**Aspect** phenomenon includes the incorrect use of perfective verbs in contexts with semantics of duration and repetition and in negative constructions with deontic verbs. 

# Background

Aspect is the grammatical category of verbs that indicates whether an action is complete or incomplete at a certain time. The *perfect* aspect shows completeness of an action, while the *imperfect* aspect indicates incompleteness.

**Aspects**:
+ *Imperfective* - incomplete, ongoing, habitual, reversed or repeated action.
+ *Perfective* - action has been completed successfully.

Perfective verbs can not occur in contexts that imply duration or repetition as it causes semantic violation.
Another restraint is that some strong deontic modals (deontic modality indicates how the world ought to be according to certain norms, expectations, etc) in Russian always require imperfective form in the complement.

# Paradigms

We include several different paradigms for the phenomenon:

1. **Incompatibility of the Perfective with the Semantics of Duration**

    - Replacing an imperfective verb with a perfective one in contexts with semantics of duration: (`change_duration_aspect`)

         *Petya dolgo **reshal** zadachu.* \
         \**Petya dolgo **reshil** (perfective) zadachu.* 


         **Translation:**\
         Petya **has been solving** the task for a long time.\
         \*Petya **has solved** the task for a long time.

2. **Impossibility of the Perfective in Repetitive Situations**
    
    - Replacing an imperfective verb with a perfective one in contexts with semantics of repetition: (`change_repetition_aspect`)

         *On **begal** kazhdyj den'.* \
         \**On **pobegal** (perfective) kazhdyj den'.* \

         **Translation:**\
         He **was running** every day.
         \*He **has ran** every day.

3. **Impossibility of the Perfective Under Negated Strong Deontic Verbs**
    
    - Replacing an imperfective verb with a perfective one in contexts with a negated deontic verb: (`deontic_imp`)

         *Mame ne stoit **myt'**  ramu.* \
        \**Mame ne stoit **pomyt'** ramu* 
        

        **Translation:** \
         Mom **shouldn't wash** the [window] frame.\
         \*Mom **shouldn't washed** the [window] frame.

# Implementation

- We curate a list of words and constructions that indicate the required semantics and use them to filter the contexts. The following lexical cues are used:

    - <u>Duration:</u> *dolgo*, *dlitel’no*, *prodolzhitel’no*, all with the semantics of ‘continuously, for a long time’.
    - <u>Repetition:</u> *kazhdyj* ‘every’ + X construction, where X is a noun denoting a time period, such as *kazhdyj den’/god* ‘every day/year’, etc.; and adverbs like *ezhechasno /ezheminutno* ‘every hour/minute’.
    - <u>Deontic modality:</u> *stoit* and *sleduet* ‘should’, *nado* and *nuzhno* ‘need’

+ To generate minimal pairs, we find sentences with an imperfective verb and check its dependents for one of the lexical cues from the list. 
- We then use a [list](https://github.com/olesar/RNC2.0/blob/main/data/lists/aspect_pair_zal.txt) of aspect pairs (Zaliznyak, 1987) to change the verb with its perfective counterpart.
- Note that for some verbs, the list includes several possible versions of pairs (e.g., *sbrasyvat’* ‘to throw’ has two perfective forms: *sbrosit’* and *sbrosat’*). We filter the list by IPM and only leave the pairs with the higher frequency.

# Limitations

Since determining the semantics of the sentence automatically is not a trivial task, we curate a list of adverbials and noun phrases indicating the required meaning (see above). While this limits the number of sentences and their diversity, it allows for a more controlled approach to minimal pair generation resulting in ungrammaticality. 

# Fields

`Aspect` — aspect of the target verb.

`adverb_lemma` — adverb with semantic duration related to the target verb (only for `change_duration_aspect`).

`repetition_adverb` — adverb or phrase with semantic repetition related to the target verb (only for `change_repetition_aspect`).

`control_form` — a deontic verb that controls the target infinitive verb (only for `deontic_imp` and `deontic_imp_conj`).


# Bibliography

+ Zaliznyak, A. (1987). Grammatical Dictionary of Russian Language: Word Inflection. Moscow.
