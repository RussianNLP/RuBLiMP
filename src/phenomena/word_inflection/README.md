# Word Inflection

Word inflection is the process of word formation in order to express tense, person, number, gender, etc. Usually, in Russian, inflection markers are word-final and called *endings*.

## Background

Russian verbs, depending on the person morphemes, are divided into two types of conjugation: the first (I) and the second (II). The forms are as following (*named* (cI) *and* (cII) *below*):

+ (1SG, 2SG, 3SG, 1PL, 2PL, 3PL)
+ I conjugation (*cI*) endings: *-u*, *-esh*, *-et*, *-em*, *-ete*, *-(y)ut*.
+ II conjugation (*cII*) endings: *-(y)u*, *-ish*, *-it*, *-im*, *-ite*, *-(y)at*.

For example, verbs of the I conjugation have the *-et* ending in 3SG (third person singular form); verbs of the II conjugation have the *-it* ending in this form.

Therefore, the replacement of the ending of one conjugation with the corresponding ending of another conjugation will create a violation: 

On **chitaet** knigu.  
*On **chitait** knigu.

**Translation:**  
He is reading the book.  
*He is read the book.  

Another important phenomenon for word inflection is declension. Declension is the inflection of nouns for the grammatical categories of case, number, and gender.

In Russian scholarly tradition three declensions are distinguished (*named* (dI), (dII) *and* (dIII) *below*):
+ I: *golova* 'head' - *golovy* 'heads'.
+ II: *stol* 'table' - *stoly* 'tables'.
+ III: *tetrad'* 'notebook' - *tetradi* 'notebooks'.

Declensions have unique paradigms of inflection: each case-number combination has its own set of possible endings for each declension (similarly to conjugations above). Replacing this ending with a corresponding ending of another declension will lead to a violation:

U nego net **stola**.  
*U nego net **stoli**.  

**Translation:**  
He does not have a table.  
*He does not have a tabl.

## Paradigms

We include several different paradigms for the phenomenon:

*Below, several glosses are used to highlight the error*:  
Declensions: (dI) — declension I, (dII) — declension II, (dIII) — declension III  
Conjugations: (cI) — conjugation I, (cII) — conjugation II

1. **Changing noun declension**
    
    - <u>Changing the noun's declension ending to the corresponding ending of another declension (`change_declension_ending`):</u>

         *U nego net **stola**.* \
         **U nego net **stoli**.* 

         **Translation:**  
         He does not have a table. — (dII) noun -  (dII) ending  
         \*He does not have a tabl. — (dII) noun - *(dIII) ending

         **English analogue:**  
        *He does not have **sheep**.*  
        \**He does not have **sheeps**.*

1. **Changing noun declension (noun has a dependent)**
    
    - <u>Changing the noun's declension ending to the corresponding ending of another declension in cases, where the noun has a dependent adjective, determiner, or participle (`change_declension_ending_has_dep`):</u>
  
         *U nego net krasivogo **stola**.* \
        \**U nego net krasivogo **stoli**.*  

         **Translation:**  
         He does not have a nice table.   — (dII) noun -  (dII) ending  
         \*He does not have a nice tabl. — (dII) noun - *(dIII) ending

         **English analogue:**  
         *He does not have good **sheep**.*  
        \**He does not have good **sheeps**.*

1. **Changing the verb's conjugation**

    - <u>Changing the verb's ending to the corresponding ending of the opposite conjugation (`change_verb_conjugation`):</u>

         *On **chitaet** knigu.* \
        \**On **chitait** knigu.* 

        **Translation:**  
         He is reading the book. — (cI) noun -  (cI) ending  
         \*He is read the book. — (cI) noun - *(cII) ending  

         **English analogue:**  
         *He ate all food.*  
         \**He eated all food.*


## Implementation

+ To generate minimal pairs for this paradigm we find sentences with the corresponding phenomena (e.g., containing a verb or a noun).
+ We use manually crafted dictionaries to change verb conjugations and noun declensions.
+ In case of a declension change, we check that the new word does not contain a sequence of letters that do not occur in Russian (we constructed the list based on the corpora data).

## Limitations

Some endings can be present in both conjugations. For example, *pishu* '(I) write' and *dyshu* '(II) breathe' have the same ending *u*. We do not include such endings in the conjugations replacement dictionary.

The same also applies to the declensions replacement dictionary. For example, *sem'i* 'families' and *koni* 'horses' have the same ending, despite them belonging to different declensions, so we do not include them.