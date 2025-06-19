import logzero
import pybind11

from clang.cindex import TranslationUnit as TU

from .utils import get_index, get_includes


def parse_tu(
    path,
    input_folder,
    prefix=None,
    platform_includes=[],
    args=[
        "-x",
        "c++",
        "-std=c++17",
        "-D__CODE_GENERATOR__",
        "-Wno-deprecated-declarations",
    ],
    parsing_header="",
    tu_parsing_header="",
    platform_parsing_header="",
):
    """Run a translation unit thorugh clang
    """

    args.append(f"-I{pybind11.get_include()}")
    args.append(f"-I{input_folder}")

    if prefix:
        args.append(f"--sysroot={prefix}")

    for inc in get_includes():
        args.append(f"-I{inc}")

    for inc in platform_includes:
        args.append(f"-I{inc}")

    ix = get_index()

    with open(path) as f:
        src = f.read()

    # skip possible invisible BOM character which would lead to clang error later
    if src[0] == "\ufeff" :
        src = src[1:]

    dummy_code = (
        f"{parsing_header}\n{platform_parsing_header}\n{tu_parsing_header}\n{src}"
    )
    tr_unit = ix.parse(
        "dummy.cxx",
        args,
        unsaved_files=[("dummy.cxx", dummy_code)],
        options=TU.PARSE_INCOMPLETE,
    )

    diag = list(tr_unit.diagnostics)
    if diag:
        logzero.logger.warning(path)
        for d in diag:
            logzero.logger.warning(d)

    tr_unit.path = ("dummy.cxx", path.name)

    return tr_unit
