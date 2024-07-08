# Agreement

**Agreement** is a phenomenon where the form of a word is dependent on the features of another, syntactically related, word.
 The first word is then called **a target** of agreement and the second word is the **controller** of agreement.
 The notion of agreement and how it manifests across the languages of the world is described in detail in (Corbett 2006). 
 The errors here have to do with incorrect form of the target or of the controller in various contexts where agreement must occur.

## Background

In Russian features like gender, number and person on controllers determine the form of the targets.
  Overall, Russian grammar distinguishes three genders (Masculine, Feminine and Neuter), two numbers (SG, singular and PL, plural) and three persons (1, 2, 3).
  Genders are only different in the singular, there are no gender contrasts in the plural (unlike in Arabic pronouns, for example).

Usually, words from parts of speech like nouns, pronouns and adjectives act as **controllers** and determine gender, number and person on their targets.
  Usually, words from parts of speech like verbs, adjectives, participles, nouns and adjective-like pronouns act as **targets** of agreement.

Parts of speech differ as to what they inflect (and can agree) for.
  Adjectives, adjective-like pronouns and participles agree for number and gender (and case, too).
  Nouns, if they have to agree (e.g. being predicates), inflect and agree for number.
  Verbs in the present and future tense agree for number and person.
  Verbs in the past tense agree for number and gender.

Consider the example of number-gender agreement of the verb in the past tense with its subject:

  *Nachalnitsa segodnya **vydala** premiju*.  
  'The chef[F] gave[F] a bonus today.'

Here, the subject *nachalnitsa* 'woman-chef[F]' is the controller of agreement by gender (feminine) and number (singular) on the target verb *vydala* 'gave[F]', which is the predicate of the sentence.
  A verb form with any other gender or number features is illicit here, so the following are all banned: **vydal* 'gave[M]', **vydalo* 'gave[N]', **vydali* 'gave[PL]'.

If the subject had different gender, the predicate would have a different form, as in the example with neuter gender subject *rukovodstvo* 'management[N]', where verb must also be in neuter:

  *Rukovodstvo segodnya **vydalo** premiju.*  
  'The management[N] gave[N] a bonus today.'

Again, any other gender-number form of the verb here is illicit: **vydal* 'gave[M]', **vydala* 'gave[F]', **vydali* 'gave[PL]'.

Finally, if the subject had different number, the predicate must again have a form with this number, as in the example with plural subject *nachalnitsy* `woman-chefs[PL]':

*Nachalnitsy segodnya **vydali** premiju*.  
'The chefs[PL] gave[PL] a bonus today.'

There are several contexts where agreement may occur in Russian, and which we treat as different paradigms.
  Note, these are almost, but not all possible contexts.
  For example, agreement of a depictive is missing as a distinct phenomenon (as it is not clearly distinguished by our parse based on Universal Dependencies).

*In addition to number (SG, PL), person (1, 2, 3) and gender marking (F, M, N) introduced above, case marking is also used here: NOM — nominative, GEN — genitive, DAT — dative, ACC — accusative, LOC — locative*


## Paradigms

Some paradigms involve attractors — subject's dependents, that have features different from subjects' features, but that occur closer to the verb and *attract* agreement to itself.
  On attractors see e.g. (Slioussar, Malko 2016).

*Additional grammatical features of Russian words not evident from the translation are provided in square brackets on the relevant words*.

1. Subject-predicate agreement (`...subj_predicate_agreement...`)

   - Changing the *number* of the predicate to be distinct from its subject's (or, sometimes, changing number of the subject to be distinct from its predicate's) (`noun_subj_predicate_agreement_number`):

     _**Mogli** oni dat' dva zolota?_  
     _***Mog** oni dat' dva zolota?_  

     **Translation:**  
     Could[PL] they have given two golds?  
     *Could[SG] they have given two golds?

   - Changing the *number* of the predicate to plural, when subject is genitive and the agreement must be the *default* singular neuter (`genitive_subj_predicate_agreement_number`):  
     
     _Predposylok dlya muzykal’noy kar’jery v ee sem’je ne **bylo**._  
     _*Predposylok dlya muzykal’noy kar’jery v ee sem’je ne **byli**._  
     
     **Translation:**  
     It was without premises in her family that she has a musician career.  
     *It were without premises in her family that she has a musician career.  


   - Changing the *number* of the predicate to plural, when subject is a clause and the agreement must be the *default* singular neuter  (`clause_subj_predicate_agreement_number`):  
     
     _Takim obrazom, dlya bol’shikh programm **prikhodilos’** ispol’zovat’ overlei._  
     _*Takim obrazom, dlya bol’shikh programm **prikhodilis’** ispol’zovat’ overlei._  

     **Translation:**  
     As such, for big programmes, using overlay was needed.  
     *As such, for big programmes, using overlay were needed.

   - Changing the *number* of the verb to that, which is different from the subject, but the same as subject's dependent — the attractor (`subj_predicate_agreement_number_attractor`):  
     
     _Rasprostranennost’ drugikh yazykov **nevelika**._  
     _*Rasprostranennost’ drugikh YAZYKOV **neveliki**._  

     **Translation:**  
     The spread of other languages is moderate.  
     *The spread of other languages are moderate.

   - Changing the *gender* of the predicate to be distinct from its subject's (or, sometimes, changing number of the subject to be distinct from its predicate's)  (`noun_subj_predicate_agreement_gender`):  
     
     _Na territorii kompleksa **postroen** Kongress-tsentr._  
     _*Na territorii kompleksa **postroena** Kongress-tsentr._  
    
     **Translation:**  
     On the complex territory a Kongress-center is[M] built.  
     On the complex territory a Kongress-center is[F] built.  

   - Changing the gender of the predicate to feminine or masculine, when subject is genitive and the agreement must be the *default* singular neuter (`genitive_subj_predicate_agreement_gender`):  
     
     _Ushedshikh iz kluba v dannyj transfernyj period ne **bylo**._  
     _*Ushedshikh iz kluba v dannyj transfernyj period ne **byla**._  

     **Translation:**  
     It was[N] without people leaving the club in the given transfer period.  
     *It was[F] without people leaving the club in the given transfer period.  

   - Changing the *gender* of the predicate to feminine or masculine, when subject is a clause and the agreement must be the *default* singular neuter (`clause_subj_predicate_agreement_gender`):  
     
     _Dalee **neobkhodimo** sdelat’ obratnuyu zamenu._  
     _*Dalee **neobkhodima** sdelat’ obratnuyu zamenu._  

     **Translation:**   
     Then it is[N] necessary to do a reverse replacement.  
     *Then it is[F] necessary to do a reverse replacement.  

   - Changing the *gender* of the verb to that, which is different from the subject, but the same as subject's dependent — the attractor (`subj_predicate_agreement_gender_attractor`):  
     
     _Mestnost’ vokrug sela sil’no **zabolochena**._  
     _*Mestnost’ vokrug SELA sil’no **zabolocheno**._  

     **Translation:**  
     The area[F] around the village[N] is[F] severely waterlogged.  
     *The area[F] around the village[N] is[N] severely waterlogged.

   - Changing the *person* of the predicate to be distinct from its subject's (`noun_subj_predicate_agreement_person`):

     _Liturgicheskaya komissiya **rabotaet** v Monreale._  
     _*Liturgicheskaya komissiya **rabotayu** v Monreale._  

     **Translation:**  
     The Liturgical Commission works[3SG] in Montreal.  
     *The Liturgical Commission work[1SG] in Montreal.  

   - Changing the *person* of the predicate to first or second person, when subject is genitive and the agreement must be the *default* third person singular `genitive_subj_predicate_agreement_person`:
     
     _Detey u Magnusa i Elizavety ne **bylo**._  
     _*Detey u Magnusa i Elizavety ne **budu**._  

     **Translation:**  
     Magnus and Elizabeth didn't have children.  
     *Magnus and Elizabeth didn't have[1SG] children.  

   - Changing the *person* of the predicate to first or second person, when subject is a clause and the agreement must be the *default* third person singular  `clause_subj_predicate_agreement_person`:  
     
     _Po otsenkam, **ostaetsya** raskopat’ okolo 350 m._  
     _*Po otsenkam, **ostaesh’sya** raskopat’ okolo 350 m._  
     
     **Translation:**  
     According to estimates, digging up about 350 m remains[3SG].  
     *According to estimates, digging up about 350 m remain[2SG].

2. Agreement inside the noun phrase (concord) (`np_agreement...`)
    - Changing the *number* of an agreeing adjective (`np_agreement_number`):

      _No **malen’kaya** geroinya vashego naroda ostalas’ tverda._  
      _*No **malen’kie** geroinya vashego naroda ostalas’ tverda._  

      **Translation:**  
      But a small[F] heroine[F] of your people remained firm.  
      *But a small[PL] heroine[F] of your people remained firm.  

    - Changing the *gender* of an agreeing adjective (`np_agreement_gender`):

      _Titul luchshej komandy Anglii **togo** sezona takzhe otoshel «osam»._  
      _*Titul luchshej komandy Anglii **toj** sezona takzhe otoshel «osam»._  

      **Translation:**  
      A title of the best English team of that[M] season[M] also went to «wasps».  
      *A title of the best English team of that[F] season[M] also went to «wasps».

    - Changing the *case* of an agreeing adjective (`np_agreement_case`):  

      _Zoloto bylo obnaruzheno v **etom** rajone v 1923 godu._  
      _*Zoloto bylo obnaruzheno v **etogo** rajone v 1923 godu._  

      **Translation:**  
      The gold was found in this[LOC] area[LOC] in 1923.  
      *The gold was found in this[GEN] area[LOC] in 1923.  

2. Agreement targetting floating quantifier *sam* 'self' (`floating_quantifier_agreement...`)

    - Changing the *number* of the quantifier or of the controller(`floating_quantifier_agreement_number`):

       _Informatsiyu podtverdili i v samoj **shkole**._  
       _*Informatsiyu podtverdili i v samoj **shkolakh**._  

      **Translation:**  
      They confirmed the information in the school[SG] itself[SG].  
      *They confirmed the information in the schools[PL] itself[SG].  

    - Changing the *gender* of the quantifier or  of the controller (`floating_quantifier_agreement_gender`):

       _Pri etom **samo** povestvovanie nikuda vas ne gonit._  
       _*Pri etom **sama** povestvovanie nikuda vas ne gonit._  

      **Translation:**  
      With that said, the narration[N] itself[N doesn't rush you anywhere.  
      *With that said, the narration[N] herself[F] doesn't rush you anywhere.  

   - Changing the *case* of the quantifier or of the controller (`floating_quantifier_agreement_case`):  

       _Ego **samogo** uzhe malo kto priznaet avtoritetom._  
       _*Ego **samomu** uzhe malo kto priznaet avtoritetom._  

      **Translation:**  
      He[ACC] himself[ACC] is considered an authority by few already.  
      *He[ACC] himself[DAT] is considered an authority by few already.  

3. Agreement of the relative pronoun *kotoryj* 'which' with its head noun (`anaphor_agreement...`)

   - Changing the *number* of the relative pronoun or of its head noun (`anaphor_agreement_number`):

       _Est’ neskol’ko rastenij, **kotorye** mozhno nayti tol’ko v Velikobritanii._  
       _*Est’ neskol’ko rastenij, **kotoroe** mozhno nayti tol’ko v Velikobritanii._  

      **Translation:**  
      There are several plants[N.PL], which[N.PL] could be found only in Great Britain.  
      *There are several plants[N.PL], which[N.SG] could be found only in Great Britain.  

   - Changing the *number* of the relative pronoun to that, which is different from the head noun, but the same as head noun's dependent — the attractor (`anaphor_agreement_number_attractor`):

       _Priznakom etoj bolezni bylo opukhanie nog, **kotorym** stradal tsar’._  
       _*Priznakom etoj bolezni bylo opukhanie NOG, **kotorymi** stradal tsar’._  

      **Translation:**  
      A sign of this disease was a swelling[N.SG] of the legs[PL], which[N.SG] tsar experienced.  
      *A sign of this disease was a swelling[N.SG] of the legs[PL], which[PL] tsar experienced.

   - Changing the *gender* of the relative pronoun (`anaphor_agreement_gender`):

       _Tekhnika, **kotoruyu** on izobrel, poluchila nazvanie «skul’ptura sveta»._  
       _*Tekhnika, **kotoryj** on izobrel, poluchila nazvanie «skul’ptura sveta»._  

      **Translation:**  
      The technique[F], which[F] he invented, was named «a sculpture of light».  
      *The technique[F], which[M] he invented, was named «a sculpture of light».


   - Changing the *gender* of the relative pronoun to that, which is different from the head noun, but the same as head noun's dependent — the attractor (`anaphor_agreement_gender_attractor`):

       _Osvoil professiyu prokhodchika, **kotoroj** ostalsya veren na vsyu zhizn’._  
       _Osvoil professiyu PROKHODCHIKA, **kotoromu** ostalsya veren na vsyu zhizn’._  

      **Translation:**  
      Mastered the job[F] of a tunneler[M], to which[F] he remained loyal whole life.  
      Mastered the job[F] of a tunneler[M], to which[M] he remained loyal whole life.

## Implementation

- We analyze each sentence with state-of-the-art [parser for Russian](https://github.com/DanAnastasyev/GramEval2020).
  The alternations themselves are implemented with [PyMorphy2](https://github.com/pymorphy2/pymorphy2).

- We check each sentence for all four possible agreement relations: subject-predicate (+clausal subject-predicate), inside the noun phrase / concord, floating quantifier agreement and relative clause.

- For *subject-predicate agreement* we had to distinguish nominal subjects, that have features like number, gender and person, from clausal subjects (which may be considered not to have such features).
  While UD makes such distinction with two different relations: `nsubj` for nominal subjects and `csubj` for clausal subjects and we exploited this, additional checks were made to ensure these subject kinds weren't confused.
  Our parser may be oriented too much on morphology, since in the following case it considered *odinok* 'lonely' a nominal subject (when this is clearly a clausal subject).

  *Tol'ko otsyuda **stanovitsya** ponyatnym, pochemu Yadozub ODINOK*.  
  'Only from this does it become clear, why Yadozub is lonely'

  To prevent such errors we made sure no predicative adjectives (to which *odinok* 'lonely' belongs) are considered nominal subjects and, more strongly, that a nominal subject must not have its own subject (which here is the name *Yadozub*).

- For *subject-predicate agreement* we find all the targets in the predicate, of which there could be multiple in cases with auxillary verbs and lexical predicates.

- Several different targets may agree with a single controller, as in the following example, where *uchitel'* 'teacher[M]' controls the verb in an instance of subject-predicate agreement and the adjective in an instance of noun phrase agreement.
  In such cases we never alternate the controller.

    *Lyubimyj[SG.M] **uchitel'**[SG.M] prishyol[SG.M].*  
    Favourite teacher came.

- For *subject-predicate agreement* and *anaphor agreement* (relative pronoun agreement) we additionally check whether there is an attractor between the controller (the subject or the head noun) and the target (the predicate or the anaphor, relative pronoun).
  As noted in [Section Paradigms](#paradigms), we define an attractor as a word, dependent on actual controller, that could have potentially been a controller itself, but isn't.
  We also ask that it have different feature from the actual controller.
  If such an attractor exists, we mark the sentence as *attractor* type and only perform that alternation on target, which gives it an attractor feature.

- Before word forms could be alternated, they are analyzed by PyMorphy2.
  Some word forms are inherently ambigious and there may be several possible analyses for them.
  To an extent, we trust the syntactic parser and choose the morphological analysis that is most similar to the one performed by the syntactic parser. 

- At the same time, in all cases we additionally check that the controller and the target, that are found by a syntactic parser, do indeed agree according to their morphological analysis by PyMorphy2.
  If they don't agree, we discard this pair.

- The alternation itself is performed by means of [PyMorphy2](https://github.com/pymorphy2/pymorphy2).
  Before this stage we have checked that whatever is to be inflected (target or controller) could be inflected.
  This prior check is performed using part of speech and feature provided by [the morphosyntactic parser](https://github.com/DanAnastasyev/GramEval2020).
  Some words may be dropped here.
  We then attempt the alternation.
  It may not go trough for all words, e.g. number inflection is unavailable or yields the same form for Singularia Tantum *pal'to* 'coat' or Pluralia Tantum *vorota* 'gates' — such words are discarded.

- The alternation is performed from the original feature into all permitted features **one by one**, so that original sentence and sentence with an alternation differ only minimally, by word forms differing in a single features.
  Thus a single original sentence may occur as part of several different pairs.
  Overall the options are the following: from singular to plural and vice versa, from a certain gender (feminine, masculine, neuter) to any other of the two genders, from a certain case to any other of the cases.
  Some specific values may be banned in certain situations due to homonymity or other factors.

- In all cases, we make sure that changed controller manifests no homonymity.
  In Russian nouns declension paradigm certain case-number combinations are syncretic, yield the same form, e.g. *dom* 'house' (NOM.SG) has the same form (except for stress that isn't visible in common written texts) in genitive singular and nominative plural: *doma* 'of a house' (GEN.SG) / 'houses' (NOM.PL).
  We make no alternations that yield homonymous forms in order to prevent ambiguity.

- In all cases we also note whether there are constituents coordinated with the controller.
  In case of coordination, change of a target into plural may not lead to ungrammaticality, so we don't perform it.

- For proper noun controllers it isn't possible to determine gender or number.
  Original agreement is, of course, correct given the context, but for sentences in isolation any gender or number could be correct.
  So we don't alternate targets whose controllers are proper nouns, unless there are other targets in the sentence (which thus determine the correct gender or number).

- In two cases we had to use an external dictionary and markup, provided to us by [Russian National Corpus](https://ruscorpora.ru/en/) (RNC) team.
  - One case is similar to proper nouns, it is nouns denoting jobs and occupations and "common gender" nouns.
    We made a list of such nouns using RNC markup.
    Without context it isn't possible to determine the semantic gender of these nouns: job names like *direktor* 'director', *vrach* 'doctor' and common gender nouns like *sirota* 'orphan', *yabeda* 'sneak'.
    We obtain a list of such nouns from RNC dictionary and, similarly to proper nouns, only alternate their targets if such nouns have other agreement targets in the sentence, which thus define the gender for this sentence.
    We should note that *semantic gender* is dicussed here.
    Speaking formally, job names like *direktor* 'director' or *vrach* 'doctor' unlike common gender nouns do have a gender (masculine in this case and usually).
    But for such nouns Russian allows not only formal agreement with masculine gender, but also **semantic agreement** (with the gender of the person referred to).
    As such, all the sentences below are possible, and thus our alternations (and this discussion) are meaningful.

    *Vrach prishla.*   
    *Vrach prishyol.*   

    **Translation:**  
    The doctor[F] came[F].  
    The doctor[M] came[M].

  - Another case is collective nouns like *kucha* 'bunch' or *kollektiv* 'collective', which similarly to English and other languages, can take either singular or plural agreement. 
    We made a list of such nouns, too.
    We don't alternate number to plural on targets of such controllers.

- Some potential changes demand that the letter *ё* (*yo* [jo] / [o] after soft consonant) be used, like *vsyo* 'all/whole' (N.SG.NOM) — *vse* 'all' (PL.NOM).
  We don't perform such changes, as the letter isn't always used in Russian typed texts.


## Limitations

**Parser**

- Despite us doing our best to correct or circumvent parser errors, they may occur and lead to incorrect analyses.
  - In particular, proper nouns are often missed in the input, not being tagged properly.

**Word lists**

- We are using word lists provided by [Russian National Corpus](https://ruscorpora.ru/en/) (RNC) team: a list of nouns that could be masculine or feminine and a list of collective nouns.
  These lists could be incomplete.

## Related work

Corbett, G. G. (2006). [Agreement](https://www.cambridge.org/us/universitypress/subjects/languages-linguistics/morphology/agreement?format=PB&isbn=9780521001700). Cambridge University Press.

Slioussar, N., & Malko, A. (2016). Gender agreement attraction in Russian: Production and comprehension evidence. Frontiers in Psychology, 7. <https://doi.org/10.3389/fpsyg.2016.01651>
