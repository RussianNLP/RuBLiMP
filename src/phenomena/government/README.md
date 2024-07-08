# Government

Government (or case government) is a phenomenon, wherein a verb or preposition determines the grammatical case of its noun phrase complement.

## Background

In Russian different verbs as well as different adpositions are governors in that they require certain cases of its complements. The choice of the case depends on several factors, such as sentence semantics and syntax, and idiosyncratic properties of the governing word.

For example, direct objects often require the usage of *accusative*.

*Mama myla ramu*[ACC].  
'Mom cleaned the [window] frame.'

Another example of government are requirements of different cases by different adpositions. Preposition *v* 'to' requires the usage of *accusative* when referring to *goal* of motion.

*Mama priekhala v shkolu*[ACC].  
'Mom arrived to school'.

At the same time, when referring to location, the preposition *v* means'in' and requires *locative* case:

*Mama rabotaet v shkole*[LOC].  
'Mom works at school'.

Another example is the preposition *k* 'at', that requires *dative*.

*Mama priekhala k shkole*[DAT].  
'Mom arrived at school'.

## Paradigms

We include several different paradigms for the phenomenon:

1. **Prepositional Government**

    - Changing the case of a noun, governed by a preposition (`adp_government_case`):

         *Petya prishel k **Mashe**.* \
        \**Petya prishel k **Mashey**.*

         **Translation:**\
         Petya came to **Masha**[ACC].\
         \*Petya came to **Masha**[INST].

2. **Verbal Government: Direct Object**

    - Changing the case of a direct verb object (`verb_acc_object`):

         *Petya udaril **ego**.* \
        \**Petya udaril **emu**.*

        **Translation:**\
         Petya hit **him**[ACC].\
         \*Petya hit **him**[DAT].

3. **Verbal Government: Genitive Object**
    
    - Changing the case of an indirect verb object in Genitive case(`verb_gen_object`):

        *Petya zhdet **ispolneniya** zhelanij.* \
        \**Petya zhdet **ispolneniem** zhelanij.*

        **Translation:**
         Petya is waiting for the **fulfillment**[GEN] of his wishes.\
         \*Petya is waiting with the **fulfillment**[INST] of his wishes.


4. **Verbal Government: Object in Instrumental Case**
    
    - Changing the case of an indirect verb object in Instrumental case(`verb_ins_object`): 

         *Masha pisala **ruchkoy**.* \
        \**Masha pisala **ruchke**.*
         
         **Translation:**\
         Masha wrote with a **pen**[INST].\
        \*Masha wrote to a **pen**[DAT].

4. **Nominalization Case**

    - <u>Replacing case of a nominalized object's dependent to another case:</u> (`nominalization_case`)  

        *Emu prinadlezhit ideya provedeniya **vechera**.* \
        \**Emu prinadlezhit ideya provedeniya **vecher**.*

        **Translation:**\
        He came up with the idea of ​​holding the **evening**[GEN].\
        He came up with the idea of ​​holding the **evening**[ACC].

## Implementation

+ Since several adpositions allow different cases (e.g., *v* ‘in’ allows both, *v dome* ‘in the house (Locative)’ and *v litso* ‘in the face (Ac- cusative)’), we create a list of adpositions and their allowed cases based on [Sichinava (2018)](http://rusgram.ru/Предлог).
+ To find nominalizations, we check for words ending with *-nie* as in *odobrenie* ‘blessing’.
+ Since many modifiers in Russian agree with their heads in number, case, and gender, a change in any of those categories will lead to agreement violations. To ensure that the phenomenon is isolated, we only include the sentences where the target word (i.g. a verb’s object, a dependent of a nominalization, or an adposition) has no modifiers.
+ Then, we obtain the PyMoprhy2 analysis of the target word. Often, PyMoprhy2 gives several analysis variants. We select the analysis, in which PyMorphy's characteristics (case, number, gender, etc) overlap with GramEval's characteristics.
+ We change the case of the target word so that it won't be ambiguous, and ensure that the resulting word form is not ambiguous, i.e., it cannot be interpreted as two different forms (e.g., ACC.SG is often the same as NOM.PL).


## Related work

+ Sichinava., D. (2018). [Preposition](http://rusgram.ru/Предлог). Materials for the project of corpus description of Russian grammar (http://rusgram.ru). 
