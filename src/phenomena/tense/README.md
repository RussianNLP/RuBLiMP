# Tense

**Tense** phenomenon focuses on errors to do with tense expression, namely, incorrect choice of the verb form in the presence of a temporal adverial (adverb or noun phrase) indicating the time of the event.

## Background

Tense is typically a morphological category of the verb, or verbal complex, that can be expressed either by verbal inflection, or by grammatical words adjacent to the verb. 

Russian language has 3 tenses: past and non-past, both expressed morphologically (via suffixation), and future, expressed analytically (to be + infinitive). 

Time reference of non-past verb forms is strictly determined by the aspect of the verb. Imperfective verbs refer to present tense, while perfective verbs refer to future. Thus, future tense for perfective and imperfective verbs is expressed diferently - morphologically or analytically, respectively. 

Additionally, morphological features expressed by the verbs also differ depending on the tense:
- person and number are only expressed in the non-past and future tenses
- gender and number - in the past tense

For the minimal pairs we only focus on past and morpholocial future tenses. See the [Implemetation](#implementation) section for more details on how the minimal pairs are created.


## Paradigms

We include several defferent paradigms for the phenomenon. Note, that for all of the paradigms we include several versions of perturbations with regards to tense -- swapping past tense for future tense and vice versa.

1. **Tense** (`single_verb_tense`)

    - <u>Changing verb tense in the presence of a temporal adverb:</u> (`single_verb_tense_simple_marker`)

        *Vchera on **dopustil** ochen’ grubuyu oshibku.* \
        \**Vchera on **dopustit** ochen’ grubuyu oshibku.*

        **Translation:** \
        Yesterday he **made** a very serious mistake. \
        \*Yesterday he **will make** a very serious mistake.
    
    - <u>Changing verb tense in the presence of a tense expression:</u> (`single_verb_tense_expression_marker`)

        *V proshlom mesyace oni **otpravilis'** v krugosvetnoe puteshestvie.* \
        \**V proshlom mesyace oni **otpravyatsya** v krugosvetnoe puteshestvie.*

        **Translation:** \
        Last month they **went** on a trip around the world. \
        \*Last month they **will go** on a trip around the world.

2. **Tense (coordination)** (`conj_verb_tense`)

    - <u>Changing verb tense in the presence of a temporal adverb:</u> (`conj_verb_tense_simple_marker`)

        *Vchera mama **otmyla** ramu i ubralas' v komnate.* \
        \**Vchera mama **otmoet** ramu i ubralas' v komnate.*

        **Translation:** \
        Yesterday mother **washed** the [window] frame and cleaned the room.
        \*Yesterday mother **will wash** the [window] frame and cleaned the room.
    
    - <u>Changing verb tense in the presence of a tense expression:</u> (`conj_verb_tense_expression_marker`)

        *Poslezavtra utrom on **pokinet** MKS i budet na Zemle.* \
        \**Poslezavtra utrom on **pokinul** MKS i budet na Zemle.*

        **Translation:** \
        The day after tomorrow morning he **will leave** the ISS and will be on Earth. \
        \*The day after tomorrow morning he **left** the ISS and will be on Earth.

2. **Tense Markers** (`tense_marker`)

    - <u>Changing temporal adverbs:</u> (`tense_marker_simple`)

        ***Vchera** on dopustil ochen’ grubuyu oshibku.* \
        \****Zavtra** on dopustil ochen’ grubuyu oshibku.*

        **Translation:** \
        **Yesterday** he made a very serious mistake. \
        \***Tomorrow** he made a very serious mistake.
    
    - <u>Changing tense expressions:</u> (`tense_marker_expression`)

        *Tonnel’ na Sinopskoy naberezhnoy otkroyut na **budushchey** nedele.* \
        \**Tonnel’ na Sinopskoy naberezhnoy otkroyut na **minuvshey** nedele.*

        **Translation:** \
        The tunnel on Sinopskaya embankment will open **next** week. \
        \*The tunnel on Sinopskaya embankment will open **last** week.
    
  
## Implementation 
- To generate the minimal pairs for the phenomenon we consider only the sentences with a perfective verb in future or past tense. This way we ensure that the pairs are indeed minimal (as perfective verbs express future tense morphologically) and the perturbations would lead to ungrammaticality.
- We find setences that include both a verb in past or future tense and a tense marker: a word or an expression that refers to a specific period of time when the action is performed. We include several types of temporal adverbialss:
    - <u>simple:</u> adverbs like *vchera* 'yesterday', *zavtra* 'tomorrow', *poslezavtra* 'the day after tomorrow', *pozavchera* 'the day before'\
    We collect a list of markers from the [Russian National Corpus](https://ruscorpora.ru/en/) (RNC) and check for their presense in the verb's dependents
    - <u>adpositional phrases:</u> 'next time', 'last Tuesday', 'next week', 'last week', etc.\
    We search for an adjective with "tense" semantics (*budushchij*, *nastupayushchij*, *gryadushchij*, *zavtrashnij* --  all used in contexts like 'next X'; *proshlyj*, *proshedshij*, *minuvshij*, *vcherashnij* -- all with the meaning 'last X').\
    Them we check the dependency tree for the construction: `PREP + ADJ + NOUN`
    . \
    To filter out potentially irrelevant constructions we limit the list of allowed prepositions to only *v* 'in' and *na* 'on/in', which are most frequently used in tense expressions. 
    - <u>numerical phrases:</u> *neskol'ko dnej nazad* 'a few days ago', *paru nedel' nazad* 'a couple of weeks ago', etc.\
    This type is only used for past --> future tense change and includes all of the constructions of the type `NUM + NOUN(pl) + ADP`. \
    We limit the list of allowed adpositions to *nazad* 'ago' to ensure the correct semantics.

- We check the verb's dependents to determine the presence of conjuncts that have different modifiers (see example below) and filter out those sentences. This way we control that the perturbed sentence won't end up having an ungrammatical sentence after perturbation.
    - *VCHERA on **byl** v Italii, a ZAVTRA **poletit** v Germaniyu*\
    'YESTERDAY he **was** in Italy and TOMORROW he **will fly** to Germany'

- Additionally, we check for clausal complements that are verbs to account for constructions like *sobirayus' sdelat'* 'am going to do' that can be used with markers of both past and future tenses when changed:
    - *Zavtra ya **sobirayus'/sobiralsya** pogulyat' po gorodu.*\
    'Tomorrow I **am/was** going to walk around the city.'

- For the "Tense Markers" paradigms we only consider temporal adverbs and adpositional phrases, since only those have contrasting phrases from another tense. To make sure that the resulting phrases are not completely random and, thus, more semantically plausible, we check the perturbed phrases for collocatioins with the noun used and select one of the more common ones to replace the adjective.

- As mentiond in the [Background](#background) Section Russian verbs express different morpholgical features in past and future tense. When swapping verb tense we extract missing features from their dependents, if possible. For example, we would look at the subject gender when transforming a verb in future tense to a verb in past tense. Where this is not possible, the sentence is filtered out.

## Limitations

**Historical Present**

Many contexts with a past tense adverbial and a verb in non-past tense are actually plausible in Russian. Those types of constructions are widely used for narration and are reffered to as histirical present tense. This, thus, makes the perturbation of past tense to present more complicated. While we try to limit the contexts and the adverbials to those that rarely allow for the historical present tense interpretation, some of them might pass the automatic checks, resulting in grammatical sentences after the perturbation.

**Tense Markers**

Due to histirical present tense, many tense expressions in Russian can also be used with verbs in both past and future tenses (see example below). To account for that, we create a small curated list of tense expressions that can only be a marker of one tense: past or future. While this limits the amount of possible constructions, this allows for a more controlled and reliable approach to minimal pair generation for this phenomenon, ensuring that the generated sentences are indeed ungrammatical.

- *Na sleduyushchij den' on **vernulsya/vernetsya** domoj.*\
    'The next day he **returned/will return** home.'



## Related Work

- Grenoble, Lenore. 1989. [Tense, Mood, Aspect: The Future in Russian](http://www.jstor.org/stable/40160227).Russian Linguistics 13, no. 2: 97–110.

- Comrie, B. 1985. [Tense](https://doi.org/10.1017/CBO9781139165815). Cambridge University Press, Cambridge.

