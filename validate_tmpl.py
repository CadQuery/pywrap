import sys

from jinja2 import Environment,meta,FileSystemLoader
from path import Path


def get_variables(filename):
    env = Environment(loader=FileSystemLoader(Path(filename).dirname()))
    template_source = env.loader.get_source(env, Path(filename).name)[0]
    parsed_content = env.parse(template_source)

    return meta.find_undeclared_variables(parsed_content)

if __name__ == '__main__':
    
    env = Environment()
    with open(sys.argv[1]) as template:
        env.parse(template.read())