# Negation

**Negation** phenomenon in RuBLiMP includes negative particle movement and in- appropriate use of negative and indefinite pronouns.

## Background

In Russian, negation can be conveyed through various means, including the particle *ne* 'not', which is the most common way to negate verbs, adjectives, and adverbs; negative pronouns such as *nikto* 'nobody', *nichto* 'nothing', *nikogda* 'never, etc can also be used to express negation (Paducheva, 2011). These negative elements are employed to indicate the absence or non-existence of something or to refute a statement.

Negative pronouns require the negation of the verb. Therefore, changing negative pronoun (in contexts with the negated verb)to an indefinite one or vice-versa (in contexts without the negated verb) would create a violation:

*Mama **nikogda** ne myla ramu.* \
'Mom never has not washed the [window] frame.'

\**Mama **kogda-libo** ne myla ramu.*\
'\*Mom ever has not washed the [window] frame.'

Moving the negative particle from the verb would also cause a violation:

*Mama nikogda **ne** myla ramu.*\
'Mom never has **not** washed the frame.'

\**Mama nikogda myla **ne** ramu.*\
'\*Mom never has washed **not** the frame.'

## Paradigms

We include several different paradigms for the phenomenon:

1. **Negative Concord**

    - Shifting the negative particle *ne* from a negated verb to another word in the sentence to violate negative concord rules: (`negative_concord`) 

         *Mama nikogda **ne** myla ramu.* \
         \**Mama nikogda myla **ne** ramu.* 

         **Translation:**\
         Mom has never [not] washed the frame.\
         \*Mom has never washed [not] the frame.

2. **Replacement of a Negative Pronoun with an Indefinite One**
    
    - Replacing a negative pronoun in the construction without a negated verb to an indefinite pronoun: (`negative_pronoun_to_indefinite`)
        
        *Mama **kogda-to** myla ramu.* \
        \**Mama **nikogda** myla ramu.* \

        **Translation:**\
        Mom **once** washed the frame.\
        \**Mom **never** washed the frame.*

3. **Replacement of an Indefinite Pronoun with a Negative One**
    
    - Replacing an indefinite pronoun in the construction with a negated verb to a negative pronoun: (`indefinite_pronoun_to_negative`)

         *Mame **nikogda** ne myla ramu.* \
        \**Mama **kogda-libo** ne myla ramu.* \

        **Translation:**\
         Mom has never [not] washed the frame.\
         \*Mom has once [not] washed the frame.


## Implementation

+ For this paradigm, we search sentences containing a verb under negation used with a negative pronoun or an indefinite pronoun used with a non-negated verb. 
+ We do not consider interrogative and conditional sentences and sentences containing an imperative, as their syntactic structures differ from affirmative sentences.
+ To create violations for paradigm (1), we move the negative particle *ne* `not' from a verb to the head of another noun, adjective, or another phrase. We ensure that the particle is moved not randomly but to specific syntactic constructions to avoid non-logical combinations of words. Such constructions can be negated in other contexts. Thus, the resulting combinations are more plausible and natural. Our systematic approach to replacing a negative pronoun with an indefinite one (and vice versa) ensures that only some replacements lead to ungrammatical sentences.
+ We curate a list of possible replacements, which consistently lead to the violation of negative concord. This list is then systematically applied to paradigms (2-3), resulting in the necessary changes to the pronouns.


## Limitations

The replacement of negative pronouns with indefinite and vice versa does not always create implausible contexts. For that reason, we create a list of pronouns the replacement of which would always lead to violations. While this limits the contexts, it allows more control, resulting in better quality data after perturbation. 


## Bibliography

+ Paducheva., E. (2011). Negation. Materials for the project of corpus description of Russian grammar (http://rusgram.ru).