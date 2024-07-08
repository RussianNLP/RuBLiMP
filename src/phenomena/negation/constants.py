NEGATIVE_PRONOUNS = {
    "какой-то": ["никакой"],
    "какой-либо": ["никакой"],
    "какой-нибудь": ["никакой"],
    "кто-то": ["никто"],
    "кто-либо": ["никто"],
    "кто-нибудь": ["никто"],
    "что-то": ["ничто"],
    "что-либо": ["ничто"],
    "что-нибудь": ["ничто"],
    "где-то": ["нигде"],
    "где-либо": ["нигде"],
    "где-нибудь": ["нигде"],
    "чей-то": ["ничей"],
    "чей-либо": ["ничей"],
    "чей-нибудь": ["ничей"],
    "когда-то": ["никогда"],
    "когда-либо": ["никогда"],
    "когда-нибудь": ["никогда"],
}


PRONOUNS_NEGATIVE = {
    "никакой": ["какой-нибудь"],
    "никто": ["кто-нибудь"],  # +
    "ничто": ["что-то", "что-нибудь"],  # +
    "никогда": ["когда-нибудь", "когда-либо"],
}