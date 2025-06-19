from functools import reduce
from operator import add
from re import match
from sys import platform

import logzero
import toml as toml
import pandas as pd

from joblib import Parallel, delayed
from path import Path
from tqdm import tqdm
from jinja2 import Environment, FileSystemLoader
from toposort import toposort_flatten

from .module import ModuleInfo
from .header import parse_tu, ClassInfo
from .utils import current_platform, get_includes, init_clang
from .schemas import global_schema, module_schema


def read_settings(p):

    with open(p) as f:
        settings = toml.load(f)

    # validate
    settings = global_schema.validate(settings)

    # extract and compile the module name extraction callable
    code = compile("func={}".format(settings.pop("module_mapping")), "<tmp>", "exec")
    tmp = {"Path": Path}
    exec(code, tmp, tmp)
    module_mapping = tmp["func"]

    # get module specific settings if defined
    if "Modules" in settings:
        modules = settings.pop("Modules")
    else:
        modules = None

    return settings, module_mapping, modules


def read_symbols(p):
    """Read provided symbols file and return a dataframe

    This information is used later for flagging undefined symbols
    """

    if int(pd.__version__.split(".")[0]) >= 2:
        sym = pd.read_csv(
            p, header=None, names=["name"], sep="\\s+", on_bad_lines="skip"
        ).dropna()
    else:
        sym = pd.read_csv(
            p, header=None, names=["name"], delim_whitespace=True, error_bad_lines=False
        ).dropna()
    return sym


def remove_undefined_mangled(m, sym):

    # exclude methods
    for c in m.classes:
        c.methods_unfiltered = c.methods
        c.methods_byref_unfiltered = c.methods_byref
        c.methods_return_byref_unfiltered = c.methods_return_byref
        c.static_methods_unfiltered = c.static_methods
        c.static_methods_byref_unfiltered = c.static_methods_byref
        c.constructors_unfiltered = c.constructors

        c.methods = [
            el
            for el in c.methods
            if sym.name.str.endswith(el.mangled_name).any()
            or el.inline
            or el.pure_virtual
            or el.virtual
        ]
        c.methods_byref = [
            el
            for el in c.methods_byref
            if sym.name.str.endswith(el.mangled_name).any()
            or el.inline
            or el.pure_virtual
            or el.virtual
        ]
        c.methods_return_byref = [
            el
            for el in c.methods_return_byref
            if sym.name.str.endswith(el.mangled_name).any()
            or el.inline
            or el.pure_virtual
            or el.virtual
        ]
        c.static_methods = [
            el
            for el in c.static_methods
            if sym.name.str.endswith(el.mangled_name).any() or el.inline
        ]
        c.static_methods_byref = [
            el
            for el in c.static_methods_byref
            if sym.name.str.endswith(el.mangled_name).any() or el.inline
        ]
        c.constructors = [
            el
            for el in c.constructors
            if sym.name.str.endswith(el.mangled_name).any()
            or el.inline
            or el.pure_virtual
            or el.virtual
        ]

    # exclude functions
    m.functions = [
        f
        for f in m.functions
        if sym.name.str.startswith(f.mangled_name).any() or f.inline
    ]

    # exclude functions per header
    for h in m.headers:
        h.functions_unfiltered = h.functions
        h.functions = [
            f
            for f in h.functions
            if sym.name.str.startswith(f.mangled_name).any() or f.inline
        ]


def is_byref_arg(arg, byref_types):

    rv = False

    if any(arg.startswith(byref_t) and arg.endswith("&") for byref_t in byref_types):
        rv = True

    return rv


def is_byref_return(met):

    rv = False

    ret = met.return_type
    if ret.endswith("&") and len(met.args) == 0:
        rv = True

    return rv


def is_byref(met, byref_types):

    rv = False

    if met.return_type == "void":
        for _, arg, _ in met.args:
            if any(
                arg.startswith(byref_t) and arg.endswith("&") for byref_t in byref_types
            ):
                rv = True
                break

    return rv


def _exclude_methods(classes, exclusions):

    for pat in exclusions:
        cls_pat, m_pat = pat.split("::")
        for c in (c for c in classes if match(cls_pat, c.name)):
            c.methods = [m for m in c.methods if not match(m_pat, m.name)]
            c.static_methods = [m for m in c.static_methods if not match(m_pat, m.name)]
            c.operators = [m for m in c.operators if not match(m_pat, m.name)]


def transform_module(m, sym, settings, settings_per_module):

    s = settings_per_module.get(m.name, None)
    global_excludes = settings[current_platform()]["exclude_classes"]

    # handle global excludes
    m.classes = [
        c for c in m.classes if not any(match(pat, c.name) for pat in global_excludes)
    ]
    m.class_dict = {
        k: v
        for k, v, in m.class_dict.items()
        if not any(match(pat, k) for pat in global_excludes)
    }

    if s:
        # exclude classes
        m.classes = [c for c in m.classes if c.name not in s["exclude_classes"]]
        m.class_dict = {
            k: v for k, v, in m.class_dict.items() if k not in s["exclude_classes"]
        }

        # exclude class templates
        m.class_templates = [
            c for c in m.class_templates if c.name not in s["exclude_class_templates"]
        ]
        m.class_template_dict = {
            k: v
            for k, v, in m.class_template_dict.items()
            if not any(match(f"^{pat}<.*>", k) for pat in s["exclude_class_templates"])
        }

        # exclude methods (including static methods)
        _exclude_methods(m.classes, s["exclude_methods"])
        _exclude_methods(m.class_templates, s["exclude_class_template_methods"])

        # exclude functions
        m.functions = [f for f in m.functions if f.name not in s["exclude_functions"]]
        for h in m.headers:
            h.functions = [
                f for f in h.functions if f.name not in s["exclude_functions"]
            ]

        # exclude typedefs
        m.typedefs = [t for t in m.typedefs if t.name not in s["exclude_typedefs"]]
        for h in m.headers:
            h.typedefs = [t for t in h.typedefs if t.name not in s["exclude_typedefs"]]

    # collect methods and static methods using byref i.s.o. return
    byref_types = settings["byref_types"] + settings["byref_types_smart_ptr"]

    if byref_types:
        for c in m.classes:

            c.methods_byref = [met for met in c.methods if is_byref(met, byref_types)]
            c.methods_return_byref = [
                met
                for met in c.methods
                if is_byref_return(met) and not met.pure_virtual
            ]
            c.static_methods_byref = [
                met for met in c.static_methods if is_byref(met, byref_types)
            ]

            for met in c.methods_byref:
                c.methods.remove(met)

            for met in c.methods_return_byref:
                c.methods.remove(met)

            for met in c.static_methods_byref:
                c.static_methods.remove(met)

    # collect exceptions
    for c in m.classes:
        if any([match(pat, c.name) for pat in settings["exceptions"]]):
            m.exceptions.append(c)
        elif c.superclasses:
            for s in (s for s in c.superclasses if s):  # remove None etc
                if any([match(pat, s) for pat in settings["exceptions"]]):
                    m.exceptions.append(c)
                    break

    for ex in m.exceptions:
        m.classes.remove(ex)

    # remove undefined symbols
    remove_undefined_mangled(m, sym)

    # sort to be reproducible
    m.headers = sorted(m.headers, key=lambda x: x.name)
    for h in m.headers:
        h.dependencies = sorted(set(h.dependencies))


def split_into_modules(names, files):

    rv = {}

    for n in names:
        rv[n] = [
            f for f in files if f.name.startswith(n + "_") or f.name.startswith(n + ".")
        ]

    return rv


def parse_modules(
    verbose, n_jobs, settings, module_mapping, settings_per_module, target_platform
):

    settings["Modules"] = settings_per_module

    path = Path(settings["input_folder"])
    file_pats = settings["pats"]
    file_exc = settings["exclude"]
    module_names = settings["modules"]

    if target_platform is None:
        module_names += settings[current_platform()]["modules"]
    else:
        module_names += settings[target_platform]["modules"]

    file_pats = [p.format(m) for m in module_names for p in settings["pats"]]

    all_files = reduce(add, (path.files(pat) for pat in file_pats))
    all_files = set(f for f in all_files if f.name not in file_exc)

    module_dict = split_into_modules(module_names, all_files)

    modules = []

    # parse modules using libclang

    def _process_module(name, files, module_names, includes, clang_location):

        # loky based workaround
        get_includes.__defaults__ = includes
        init_clang.__defaults__ = clang_location

        if not verbose:
            logzero.logger.setLevel(logzero.logging.INFO)
        return ModuleInfo(name, path, files, module_names, settings)

    modules = Parallel(prefer="processes", n_jobs=n_jobs)(
        delayed(_process_module)(
            name,
            files,
            module_names,
            get_includes.__defaults__,
            init_clang.__defaults__,
        )
        for name, files in tqdm(module_dict.items())
    )

    return modules


def transform_modules(
    verbose, n_jobs, settings, module_mapping, settings_per_module, modules
):

    sym = read_symbols(settings[current_platform()]["symbols"])

    # ignore functions and classes based on settings and update the global class_dict
    def _filter_module(m):
        if not verbose:
            logzero.logger.setLevel(logzero.logging.INFO)
        logzero.logger.debug(m.name)
        transform_module(m, sym, settings, settings_per_module)

        return m

    modules = Parallel(prefer="processes", n_jobs=n_jobs)(
        delayed(_filter_module)(m) for m in tqdm(modules)
    )

    # construct global class dictionary
    class_dict = {}
    for m in modules:
        class_dict.update(m.class_dict)

    # sort modules
    logzero.logger.info("sorting")

    cls_dict = {c.name: m.name for m in modules for c in m.classes}
    enum_dict = {e.name: m.name for m in modules for e in m.enums}
    # Update dependencies based on superclasses and default argument types

    for m in modules:
        m.dependencies.update(
            [
                cls_dict[s]
                for c in m.classes
                for s in c.superclass
                if s in cls_dict and cls_dict[s] != m.name
            ]
        )
        # Consts should be removed before
        for t in (
            t
            for c in m.classes
            for method in c.methods + c.constructors + c.destructors
            for t in method.default_value_types
        ):
            if t.startswith("const "):
                t = t.split("const ")[1]
            if t in cls_dict and cls_dict[t] != m.name:
                m.dependencies.add(cls_dict[t])
            # elif t in enum_dict and enum_dict[t] != m.name:
            #    m.dependencies.add(enum_dict[t])

    # remove duplicate typedefs
    logzero.logger.info("removing duplicate typedefs")

    typedefs_dict = {}
    for m in modules:
        for h in m.headers:
            to_remove = []
            for t in h.typedefs:
                if t.type in typedefs_dict:
                    typedefs_dict[t.type].append(t)
                    to_remove.append(t)
                else:
                    typedefs_dict[t.type] = [t]

            for t in to_remove:
                h.typedefs.remove(t)

    return modules, class_dict, enum_dict


def toposort_modules(modules):

    deps = {}

    cls_dict = {c.name: m.name for m in modules for c in m.classes}
    tmpl_dict = {t.name: t for m in modules for t in m.class_templates}

    for m in modules:

        typedefs = []
        for t in m.typedefs:
            if not t.pod:
                if t.template_base:
                    if t.template_base[0] in tmpl_dict:
                        typedefs.append(tmpl_dict[t.template_base[0]])

        deps[m.name] = set(
            cls_dict[s]
            for c in m.classes + m.class_templates + typedefs
            for s in c.superclass
            if s in cls_dict
        ) - {m.name}

    return toposort_flatten(deps)


def render(settings, module_settings, modules, class_dict):

    name = settings["name"]
    module_names = [m.name for m in modules]
    output_path = Path(settings["output_folder"])
    operator_dict = settings["Operators"]

    pre = settings["Extras"]["include_pre"]
    post = settings["Extras"]["include_post"]

    def proper_new_operator(cls):

        new_ops = [op for op in cls.static_operators if op.name == "operator new"]

        if not new_ops:
            return True

        new_ops = [op for op in new_ops if len(op.args) == 1]

        return new_ops

    def proper_delete_operator(cls):

        del_ops = [op for op in cls.static_operators if op.name == "operator delete"]

        if not del_ops:
            return True

        del_ops = [op for op in del_ops if len(op.args) == 1]

        return del_ops

    default_path = [Path(__file__).dirname()]
    additional_path = (
        [Path(settings["template_path"]),] if settings["template_path"] else []
    )
    template_paths = additional_path + default_path

    jinja_env = Environment(
        loader=FileSystemLoader(template_paths),
        trim_blocks=True,
        lstrip_blocks=True,
        extensions=["jinja2.ext.do"],
    )

    all_classes = {c.name: c for m in modules for c in m.classes}
    all_enums = {e.name: e for m in modules for e in m.enums}
    all_typedefs = {t.name: t for m in modules for t in m.typedefs}

    jinja_env.globals.update(
        {
            "parent_has_nonpublic_destructor": lambda c: any(
                all_classes[p].nonpublic_destructors
                for p in c.superclasses
                if p in all_classes
            ),
            "is_byref": lambda t: is_byref_arg(t, settings["byref_types"]),
            "is_byref_smart_ptr": lambda t: is_byref_arg(
                t, settings["byref_types_smart_ptr"]
            ),
            "args_byref": lambda f: [
                arg for arg, t, _ in f.args if is_byref_arg(t, settings["byref_types"])
            ],
            "enumerate": enumerate,
            "platform": platform,
            "class_dict": class_dict,
            "all_classes": all_classes,
            "all_enums": all_enums,
            "all_typedefs": all_typedefs,
            "project_name": name,
            "operator_dict": operator_dict,
            "include_pre": pre,
            "include_post": post,
            "references_inner": lambda name, method: name + "::" in method.return_type
            or any([name + "::" in a for _, a, _ in method.args]),
            "proper_new_operator": proper_new_operator,
            "proper_delete_operator": proper_delete_operator,
            "module_names": module_names,
            "sorted_modules": toposort_modules(modules),
            "settings": settings,
        }
    )

    jinja_env.filters["get"] = lambda x, n: x[n]

    template_sub = jinja_env.get_template("template_sub.j2")
    template_sub_pre = jinja_env.get_template("template_sub_pre.j2")
    template_tmpl = jinja_env.get_template("template_templates.j2")
    template_main = jinja_env.get_template("template_main.j2")
    template_cmake = jinja_env.get_template("CMakeLists.j2")

    output_path.mkdir_p()
    with output_path:
        for m in tqdm(modules):
            tqdm.write(f"Processing module {m.name}")

            jinja_env.globals.update(
                {
                    "module_settings": module_settings.get(
                        m.name, module_schema.validate({})
                    )
                }
            )

            class_templates = {el.name: el for el in m.class_templates}

            typedefs = (
                t
                for h in m.headers
                for t in h.typedefs
                if not t.pod
                and not "_H" in t.name
                and len(t.template_base) > 0
                and not t.type.startswith("opencascade::handle")
            )
            typedefs = filter(
                lambda t: not t.type.split(t.template_base[0])[-1].endswith(
                    "::Iterator"
                ),
                typedefs,
            )

            classes_typedefs = {el.name: el for el in (m.classes + list(typedefs))}

            dag = {}
            for el in classes_typedefs.values():
                if isinstance(el, ClassInfo):
                    deps = set(el.superclass)
                else:
                    base = el.template_base[0]
                    deps = set(el.template_args)
                    deps |= (
                        set(class_templates[base].superclass)
                        if base in class_templates
                        else set()
                    )

                dag[el.name] = deps

            sorted_classes_typedefs = [
                classes_typedefs[k]
                for k in toposort_flatten(dag)
                if k in classes_typedefs
            ]

            with open(f"{m.name}_pre.cpp", "w") as f:
                f.write(
                    template_sub_pre.render(
                        {
                            "module": m,
                            "classes_typedefs": sorted_classes_typedefs,
                            "str": str,
                            "type": type,
                        }
                    )
                )

            with open(f"{m.name}.cpp", "w") as f:
                f.write(template_sub.render({"module": m}))

            with open(f"{m.name}_tmpl.hxx", "w") as f:
                f.write(template_tmpl.render({"module": m}))

        with open(f"{name}.cpp", "w") as f:
            f.write(template_main.render({"name": name}))

        with open("CMakeLists.txt", "w") as f:
            f.write(template_cmake.render({"name": name}))

    for p in settings["additional_files"]:
        Path(p).copy(output_path)


def validate_result(verbose, n_jobs, folder):
    def _validate(f):

        tu = parse_tu(f, pre_includes="")
        if len([d for d in tu.diagnostics if d.severity > 2]):
            logzero.logger.error("Validation {}: NOK".format(f))
            if verbose:
                for d in tu.diagnostics:
                    logzero.logger.warning(d)
        else:
            logzero.logger.info("Validation {}: OK".format(f))

    result = Parallel(prefer="processes", n_jobs=n_jobs)(
        delayed(_validate)(n) for n in Path(folder).files("*.cpp")
    )

    for r in result:
        pass
