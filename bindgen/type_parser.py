# %% Expression used for stripping handle etc
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


# %% Expression used for parsing collections
from pyparsing import (
    Word,
    alphanums,
    Optional,
    Literal,
    delimitedList,
    Forward,
    ZeroOrMore,
    Or,
    Suppress,
    Combine,
    Group,
)

name = Word(alphanums + "_")
cpp_type = (
    Literal("const")[0, 1]
    + (Literal("long ") | Literal("unsigned "))[0, 1]
    + Literal("long")[0, 1]
    + name[0, 1]
    + ZeroOrMore(Literal("::") + name)
)
open_bracket = Literal("<")
close_bracket = Literal(">")

cpp_expr = Forward()
cpp_expr << cpp_type + Optional(
    Suppress(open_bracket)
    + delimitedList(Group(cpp_expr) + Suppress(Literal("*")[0, 1]), combine=False)
    + Suppress(close_bracket)
    + Optional(cpp_type)
)

ptr_types = ["handle"]

# final expresion for arg type parsing
arg_type_expr = (
    Suppress(Literal("const"))[0, 1]
    + Suppress(Literal("typename"))[0, 1]
    + Suppress(Or(map(Literal, ptr_types)) + open_bracket)[0, 1]
    + (cpp_expr)
    + Suppress(close_bracket)[0, 1]
    + Suppress(Literal("*")[0, 1] + Literal("&")[0, 1])
)

# %% PODs for the parsing results
from typing import NamedTuple, Union
from pyparsing import ParseResults


class TemplateSpecialization(NamedTuple):

    template_base: str
    template_args: tuple[Union[str, "TemplateSpecialization"]]

    @classmethod
    def make(cls, arg: ParseResults):
        base = []
        args = []

        for el in arg:
            # base typ element
            if isinstance(el, str):
                base.append(el)
            # simple argument
            elif len(el) == 1:
                args.append(el[0])
            # complex argument - recurse
            else:
                args.append(cls.make(el))

        return cls("".join(base), tuple(args))

    def name(self):

        # we don't want to have handles in the naming
        if self.template_base.endswith("handle"):
            arg = self.template_args[0]
            if isinstance(arg, str):
                return arg
            else:
                return arg.name()
        else:
            rv = self.template_base

        return rv
    
    def leaf_args(self) -> list[str]:

        rv = []

        for arg in self.template_args:
            if isinstance(arg, str):
                rv.append(arg)
            else:
                rv.extend(arg.leaf_args())

        return rv

    def full_type(self) -> str:

        rv = []
        rv.append(self.template_base)

        for arg in self.template_args:
            if isinstance(arg, str):
                rv.append(arg)
            else:
                rv.append(arg.full_type())

        return '{}<{}>'.format(rv[0], ','.join(rv[1:])) 


class config:
    IGNORE = ("TopTools_ShapeMapHasher",)
    COLLECTION = "NCollection"


class CollectionTypedef(NamedTuple):

    template_base: str
    template_args: tuple[Union[str, "TemplateSpecialization", "CollectionTypedef"]]

    @classmethod
    def make(cls, res: ParseResults):

        base = res[0]
        args = []
        
        for el in res[1:]:
            if len(el) == 1:
                args.append(el[0])
            elif el[0].startswith(config.COLLECTION):
                args.append(CollectionTypedef.make(el))
            else:
                args.append(TemplateSpecialization.make(el))

        return cls(res[0], tuple(args))

    def name(self):
        """
        Generate a name to bind the class.
        """
        arg_names = []

        for arg in self.template_args:
            if isinstance(arg, str) and not arg in config.IGNORE:
                arg_names.append(arg)
            elif not isinstance(arg, str):
                arg_names.append(arg.name())

        return self.template_base.split("_")[-1] + "_" + "_".join(arg_names)

    def leaf_args(self) -> list[str]:
        """
        Return all leaf (i.e. not nested) types.
        """
        rv = []

        for arg in self.template_args:
            if isinstance(arg, str):
                rv.append(arg)
            else:
                rv.extend(arg.leaf_args())

        return rv

    def full_type(self) -> str:

        rv = []
        rv.append(self.template_base)

        for arg in self.template_args:
            if isinstance(arg, str):
                rv.append(arg)
            else:
                rv.append(arg.full_type())

        return '{}<{}>'.format(rv[0], ','.join(rv[1:])) 

