import click
import logzero
import pickle

from types import SimpleNamespace
from path import Path

from . import read_settings, parse_modules, transform_modules, render, validate_result
from .utils import get_includes, init_clang


@click.group()
@click.option("-n", "--njobs", default=-2, type=int)
@click.option(
    "-p",
    "--prefix",
    default=".",
    type=click.Path(False, False, True),
    help="Source prefix",
)
@click.option("-v", "--verbose", is_flag=True)
@click.option("-c", "--clean", is_flag=True)
@click.option(
    "-i",
    "--include",
    multiple=True,
    type=click.Path(True, False, True),
    default=[],
    help="additional inlcude paths",
)
@click.option(
    "-l",
    "--libclang",
    type=click.Path(True, True, False),
    default=None,
    help="libclang location",
)
@click.pass_context
def main(ctx, clean, verbose, njobs, include, prefix, libclang):

    if not verbose:
        logzero.logger.setLevel(logzero.logging.INFO)

    if include:
        get_includes.__defaults__ = (include,)

    if libclang:
        init_clang.__defaults__ = (libclang,)

    ctx.obj = SimpleNamespace(
        verbose=verbose, njobs=njobs, clean=clean, prefix=Path(prefix)
    )


@main.command()
@click.argument("configuration")
@click.argument("output")
@click.argument(
    "platform",
    default=None,
    required=False,
    type=click.Choice(("Linux", "Windows", "OSX", "FreeBSD")),
)
@click.pass_obj
def parse(obj, configuration, output, platform=None):

    settings, module_mapping, module_settings = read_settings(configuration)

    with obj.prefix:
        result = parse_modules(
            obj.verbose, obj.njobs, settings, module_mapping, module_settings, platform
        )

    with open(output, "wb") as f:
        pickle.dump(result, f)


@main.command()
@click.argument("configuration")
@click.argument(
    "platform",
    default=None,
    required=False,
    type=click.Choice(("Linux", "Windows", "OSX", "FreeBSD")),
)
@click.argument("input")
@click.argument("output")
@click.pass_obj
def transform(obj, configuration, platform, input, output):

    with open(input, "rb") as f:
        modules = pickle.load(f)

    settings, module_mapping, module_settings = read_settings(configuration)
    modules, class_dict, enum_dict = transform_modules(
        obj.verbose, obj.njobs, settings, module_mapping, module_settings, modules, platform=platform
    )

    with open(output, "wb") as f:
        pickle.dump((modules, class_dict, enum_dict), f)


@main.command()
@click.argument("configuration")
@click.argument(
    "platform",
    default=None,
    required=False,
    type=click.Choice(("Linux", "Windows", "OSX", "FreeBSD")),
)
@click.argument("input")
@click.pass_obj
def generate(obj, configuration, platform, input):

    settings, module_mapping, module_settings = read_settings(configuration)
    out = Path(settings["output_folder"])

    if obj.clean:
        out.rmtree_p()

    with open(input, "rb") as f:
        modules, class_dict, enum_dict = pickle.load(f)

    render(settings, module_settings, modules, class_dict, obj.prefix, platform=platform)

    pre = settings["Extras"]["include_pre"]
    post = settings["Extras"]["include_pre"]

    if pre:
        (obj.prefix / Path(pre)).copy(out)
    if post:
        (obj.prefix / Path(post)).copy(out)


@main.command()
@click.argument("folder")
@click.pass_obj
def validate(obj, folder):

    validate_result(obj.verbose, obj.njobs, folder)


@main.command()
@click.argument("configuration")
@click.argument(
    "platform",
    default=None,
    required=False,
    type=click.Choice(("Linux", "Windows", "OSX", "FreeBSD")),
)
@click.argument("tmp_parsed", default="tmp.pkl")
@click.argument("tmp_filtered", default="tmp_filtered.pkl")
@click.pass_context
def all(ctx, configuration, platform, tmp_parsed, tmp_filtered):

    ctx.invoke(parse, configuration=configuration, output=tmp_parsed, platform=platform)
    ctx.invoke(
        transform, configuration=configuration, input=tmp_parsed, output=tmp_filtered, platform=platform
    )
    ctx.invoke(generate, configuration=configuration, input=tmp_filtered, platform=platform)


if __name__ == "__main__":

    main()
