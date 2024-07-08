# Word Formation

Word formation is the creation of new words from an existing word. In Russian, new word forms are derived with prefixes (usually, verbs) and suffixes (usually, nouns and adjectives).

## Background

Word formation is possible for words of various parts of speech. We consider verbs formed from verbs with prefixes and nominals formed from nominals with suffixes.

There are two types of verb prefixes in Russian: external and internal (for the list of prefixes see Svenonius, 2004). External prefixes express adverbial-like meanings that combine with the meaning of a verbal stem systematically and predictably; internal prefixes tend to have idiosyncratic semantics (Tatevosov, 2008). For example, the external prefix *za* in *zapet'* 'to start singing' expresses the inception of the process; the internal prefix *za* in *zapisat'* 'to write down' indicates that the process is relatively short and temporally bounded. This demonstrates that the semantic contribution of internal prefixes can hardly be reduced to a simple and uniform meaning component, contrary to external prefixes.

Prefixes have their own stacking rules. Prefix stacking rules are presented in Reynolds (2013). These rules are a simplification of much more diverse and complex rules, however, they could be easily implemented for performing word formation violations (for a more detailed view of Russian verb prefix morphology see Tatevosov, 2008). An example of a prefix stacking rule is the ban on putting the internal prefix before the external one: while *pere-u-govorit'* 'to persuade again' is a semantically plausible word form, the meaning of *\*u-pere-govorit'* can hardly be formulated, it is banned.

For nouns two types of suffixes are used: inflectional and derivational. Adding a new suffix to the word could lead to the formation of semantically implausible and non-existing words. For example, the adjective *vodoprovod-n-yj* 'tap' has the derivational suffix *n*, which is used to derive adjectives from nouns. By adding the derivational suffix *ist* (meaning either 'containing more than normal' or 'similar') before *n* we get the non-existing word *vodoprovod-ist-n-yj*.

## Paradigms

We include several different paradigms for the phenomenon:

1. **Adding New Suffix**
    - <u>Adding a new suffix to the noun or adjective to create a non-existing word (`change_verb_prefixes_order`):</u>

         ***Vodoprovodnaya** voda ispol'zuetsya tol'ko dlya rukomojnikov i v celyah prigotovleniya pishchi.*  
         \****Vodoprovodistnaya** voda ispol'zuetsya tol'ko dlya rukomojnikov i v celyah prigotovleniya pishchi.*  

         **Translation:**  
         *Tap water is used only for washing basins and food preparation purposes.*  
         \**Tapous water is used only for washing basins and food preparation purposes.*

1. **Adding Prefix to Verb**

    - <u>Adding a prefix to the verb to create a violation of prefix stacking rules (`add_verb_prefix`):</u>  

         *Vasya zabyl **zapisat'** domashnee zadanie.*  
         \**Vasya zabyl **prozapisat'** domashnee zadanie.*

         **Translation:**  
         *Vasya forgot to write down the homework.*  
         \**Vasya forgot to repeatedly-write down the homework.*

1. **Changing the verb's prefixes order**

    - <u>Changing the order of the verb's prefixes to create a violation of prefix stacking rules (`change_verb_prefixes_order`):</u>  
  
         *Petya **podustal** na rabote.*   
         \**Petya **upodstal** na rabote.* 

         **Translation:**  
         *Petya got slightly tired at work.*  
         \**Petya slightly got tired at work.*

## Implementation

+ To generate minimal pairs for this paradigm we find sentences with the corresponding phenomena (e.g., containing the verb with prefixes).
+ Using PyMorphy2, we get the initial form of the word and then segment it using dictionaries from Bolshakova & Sapin (2021) into morphological elements (prefixes, root, suffixes, ending, etc).
+ For verb prefix violations, we either add a new internal prefix to the word or change the order of prefixes to violate the rules listed in Reynolds (2013); we check that the added prefix co-occurs with the word root.
+ For noun suffix violations, we add a new derivational suffix that co-occurs with the word root; we check that the new suffix is between the root and the inflectional suffix (which always holds for nouns in Russian).
+ We check that the new word does not exist in PyMorphy2 dictionaries and does not contain a character sequence unnatural to Russian.

## Limitations

**Annotation**

Neither PyMorphy2 nor GramEval2020 annotate morphological elements or their subtypes (e.g., inflectional/derivational suffixes, internal/external prefixes). We manually crafted lists of suffixes and prefixes and divided them into subtypes. Depending on the context, some prefixes could be both internal and external (see an example with *za* above); the same also applies to suffixes that could be both inflectional and derivational. To create violations, we used internal prefixes which are distinct from all external prefixes and derivational suffixes that are distinct from all inflectional ones.

**Violating Prefix Stacking Rules**

To simplify prefix stacking rules, we only change the order of prefixes in verbs if the verb has two prefixes. For the same reason, we add a new prefix to the verb if the verb has no prefixes or only a single prefix.

## Fields

`lemma` — lemma of the target word

`control_form` — a form of the control word

`morpheme` — the target morpheme of the target word

`new_suffix_position` — the position of the added suffix in the violated form of the target word (only for `add_new_suffix`)

`new_prefix_position` — the position of the added prefix in the violated form of the target word (only for `add_verb_prefix` and `change_verb_prefixes_order`)

## Bibliography

+ Bolshakova, E., & Sapin, A. (2021). Building dataset and morpheme segmentation model for Russian word forms. In Computational Linguistics and Intellectual Technologies: Proceedings of the International Conference “Dialogue (pp. 154-161). https://doi.org/10.28995/2075-7182-2021-20-154-161

+ Reynolds, Robert (2013). Out of Order?: Russian Prefixes, Complexity-based Ordering and Acyclicity. University of Pennsylvania Working Papers in Linguistics: Vol. 19, Iss. 1, Article 19. https://repository.upenn.edu/pwpl/vol19/iss1/19

+ Svenonius, Peter (2004). Slavic prefixes and morphology. An Introduction to the Nordlyd volume. Nordlyd
32:177–204.

+ Tatevosov, S. (2008). Intermediate prefixes in Russian. In Proceedings of the annual workshop on formal approaches to Slavic linguistics (Vol. 16, pp. 423-445). http://darwin.philol.msu.ru/staff/people/tatevosov/intermediate.pdf


