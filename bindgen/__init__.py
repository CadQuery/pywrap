from functools import reduce
from operator import add

import toml as toml

from joblib import Parallel, delayed
from path import Path
from tqdm import tqdm
from jinja2 import Environment, FileSystemLoader

from .module import ModuleInfo

def read_settings(p):
    
    with open('conf.toml') as f:
        settings = toml.load(f)
    
    #extract and compile the module name extraction callable
    code = compile('func={}'.format(settings.pop('module_mapping')),'<tmp>','exec')
    tmp = {'Path' : Path}; exec(code,tmp,tmp)
    module_mapping = tmp['func']

    #get module specific settings if defined
    if 'Modules' in settings:
        modules = settings.pop('Modules')
    else:
        modules = None
        
    return settings,module_mapping,modules


def parse_modules(settings,
                  module_mapping,
                  settings_per_module):

    path = Path(settings['input_folder'])
    file_pats = settings['include']
    
    all_files = reduce(add,(path.files(pat) for pat in file_pats))
    module_names = sorted(set((module_mapping(p) for p in all_files)))
    
    modules = []
    class_dict = {}
    
    def _process_module(n):
        return ModuleInfo(n,path,path.files(n+'_*.hxx'))
    
    modules = Parallel(prefer='processes',n_jobs=-2)\
        (delayed(_process_module)(n) for n in tqdm(module_names))
    
    for m in modules: class_dict.update(m.class_dict)
    
    return modules,class_dict

def render(settings,modules):
    
    name = settings['name']
    output_path = Path(settings['output_folder'])
    operator_dict = settings['Operators']

    pre = settings['Extras']['include_pre']
    post = settings['Extras']['include_post']
        
    jinja_env = Environment(loader=FileSystemLoader(Path(__file__).dirname()),
                            trim_blocks=True,
                            lstrip_blocks = True)
    template = jinja_env.get_template('template.j2')
    
    output_path.mkdir_p()
    with  output_path:
        for m in tqdm(modules):
            tqdm.write('Processing module {}'.format(m.name))
            with open('{}.cpp'.format(m.name),'w') as f:
                f.write(template.render({'module' : m,
                                         'project_name' : name,
                                         'operator_dict' : operator_dict,
                                         'include_pre' : pre,
                                         'include_post' : post}))

def run(settings,
        module_mapping,
        settings_per_module):

    name = settings['name']
    path = Path(settings['input_folder'])
    output_path = Path(settings['output_folder'])
    file_pat = settings['include'][0]
    operator_dict = settings['Operators']
    
    all_files = path.files(file_pat)
    module_names = sorted(set((module_mapping(p) for p in all_files)))
    
    modules = []
    for n in tqdm(module_names):
        tqdm.write('Processing module {}'.format(n))
        modules.append(ModuleInfo(n,path,path.files(n+'*.hxx')))
        
    jinja_env = Environment(loader=FileSystemLoader(Path(__file__).dirname()),
                            trim_blocks=True,
                            lstrip_blocks = True)
    template = jinja_env.get_template('template.j2')
    
    output_path.mkdir_p()
    with  output_path:
        for m in tqdm(modules):
            tqdm.write('Processing module {}'.format(m.name))
            with open('{}.cpp'.format(m.name),'w') as f:
                f.write(template.render({'module' : m,
                                         'project_name' : name,
                                         'operator_dict' : operator_dict}))
    
    return modules