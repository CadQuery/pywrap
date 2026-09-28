import logzero
import pybind11
import os
import tempfile

from clang.cindex import TranslationUnit as TU

from .utils import get_index, get_includes

_pch = {}
_pch_dirs = []


def preamble_pch(ix, args, text):
    """Precompiled header of the preamble shared by every translation unit, built once per process"""

    key = (tuple(args), text)
    if key not in _pch:
        _pch_dirs.append(tempfile.TemporaryDirectory())
        path = os.path.join(_pch_dirs[-1].name, "preamble.hxx")
        with open(path, "w") as f:
            f.write(text)
        tu = ix.parse(
            path,
            [a for a in args if a not in ("-x", "c++")] + ["-x", "c++-header"],
            options=TU.PARSE_INCOMPLETE,
        )
        if tu.diagnostics:
            logzero.logger.warning(path)
        for d in tu.diagnostics:
            logzero.logger.warning(d)
        tu.save(path + ".pch")
        _pch[key] = path + ".pch"

    return _pch[key]


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
        "-Wno-#pragma-messages",
    ],
    parsing_header="",
    tu_parsing_header="",
    platform_parsing_header="",
    target_platform=None,
):
    """Run a translation unit thorugh clang"""

    args = list(args)
    args.append(f"-I{pybind11.get_include()}")
    args.append(f"-I{input_folder}")

    if target_platform == "Windows":
        args.append("--target=x86_64-pc-windows-msvc")
        args.append("-fms-compatibility")
        args.append("-fms-extensions")
    elif target_platform == "OSX":
        args.append("--target=x86_64-apple-darwin")

    if prefix:
        args.append(f"--sysroot={prefix}")

    for inc in get_includes():
        args.append(f"-idirafter{inc}")

    for inc in platform_includes:
        args.append(f"-I{inc}")

    ix = get_index()

    with open(path) as f:
        src = f.read()

    # skip possible invisible BOM character which would lead to clang error later
    if src[0] == "\ufeff":
        src = src[1:]

    pch = preamble_pch(ix, args, f"{parsing_header}\n{platform_parsing_header}\n")
    dummy_code = f"{parsing_header}\n{platform_parsing_header}\n{
            tu_parsing_header}\n{src}"
    tr_unit = ix.parse(
        "dummy.cxx",
        args + ["-include-pch", pch],
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
