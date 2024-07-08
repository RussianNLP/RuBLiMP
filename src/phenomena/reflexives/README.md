# Reflexives

Reflexives are a special pronoun type that always refer to an antecedent in the same sentence. In Russian, the antecedent is usually the subject.

## Background

Reflexives in Russian don't distinguish gender, person or number, so there is a single reflexive pronoun *sebya* 'self', which inflects for case.

Errors in binding are generally complex to implement. We consider a special context, where possession is predicated (predicative possession):

U **nih** est' mashina.  
They have a car (lit. By them is a car).

The possessor here is external, it is expressed in a *u*-phrase (locative predicative possession in terms of Stassen, 2013). This context is special in that the possessor can't be a reflexive, as in this case it would be unbound, leading to ungrammaticality:

*U **nego** byli druz'ya*.  
**U **sebya** byli druz'ya*.

**Translation:**\
He had friends.  \
*Self had friends.

Such sentences never offer anything for reflexive pronouns to refer to, therefore replacing a personal pronoun possessor with a reflexive pronoun will always produce an ungrammatical sentence.

## Paradigms
We include a single paradigm for the phenomenon:

1. **External Posessor**

    - <u>Replacing the third person pronoun with a reflexive pronoun *sebya* 'self' (`external_posessor`)</u>:  
         *U **nih** est' mashina.* \
         \**U **sebya** est' mashina.*
         
         **Translation:**  
         *They have a car.* (lit. *By them is a car.*)  
         \**Themselves have a car.* (lit. *By self is a car.*)

## Implementation

+ To generate minimal pairs for this paradigm we find sentences whose predicate is either the verb *est'* 'is' or the verb *byt'* 'to be'.
+ The sentence must have a third person pronoun or a noun encoded as the object of a locative preposition *u* 'by'.
+  Also, the object of possession must follow the reflexive, not vice versa. 
+ We replace this third person pronoun (e.g., *oni* 'they', *ego* 'him') or a noun with a reflexive pronoun *sebya* 'self'

## Limitations

Replacement of a personal pronoun like *ego* 'him' or *menya* 'me' with a reflexive pronoun *sebya* 'self' or vice versa may yield a grammatical sentence (albeit, with a different meaning) in a lot of situations, so we don't perform it freely. Instead we employ a context of predicative possession, where reflexive is strictly illicit.

## Bibliography

+ Leon Stassen. 2013. Predicative Possession. In: Dryer, Matthew S. & Haspelmath, Martin (eds.) WALS Online (v2020.3) [Data set]. Zenodo. <https://doi.org/10.5281/zenodo.7385533> (Available online at <http://wals.info/chapter/117>, Accessed on 2023-11-16.)

+ Aysa Arylova. 2013. Possession in the Russian clause: towards dynamicity in syntax. Ph.D. thesis, University of Groningen.