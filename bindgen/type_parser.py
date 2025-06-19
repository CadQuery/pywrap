from pyparsing import Word, Literal, alphas, alphanums, Optional


CONST = Literal("const")
HANDLE = Literal("opencascade::handle<")
TYPE = Word(alphas + "_", alphanums + "_")
CLOSING = Literal(">")
PTR_REF = Literal("&") | Literal("*")

parser = (
    Optional(CONST)
    + Optional(HANDLE)
    + TYPE.setResultsName("type")
    + Optional(CLOSING)
    + Optional(PTR_REF)
)


def parse_type(t):

    return parser.parseString(t).type
