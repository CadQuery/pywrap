from functools import reduce
from operator import add


import logzero
import toml as toml

from joblib import Parallel, delayed
from path import Path
from tqdm import tqdm
from jinja2 import Environment, FileSystemLoader

from .module import ModuleInfo
from .header import parse_tu

def read_settings(p):
    
    with open(p) as f:
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


def parse_modules(verbose,
                  n_jobs,
                  settings,
                  module_mapping,
                  settings_per_module):

    path = Path(settings['input_folder'])
    file_pats = settings['include']
    
    all_files = reduce(add,(path.files(pat) for pat in file_pats))
    module_names = sorted(set((module_mapping(p) for p in all_files)))
    
    modules = []
    class_dict = {}
    
    def _process_module(n):
        if not verbose:
            logzero.logger.setLevel(logzero.logging.INFO)
        return ModuleInfo(n,path,path.files(n+'*.hxx'))
    
    modules = Parallel(prefer='processes',n_jobs=n_jobs)\
        (delayed(_process_module)(n) for n in tqdm(module_names))
    '''
    modules=[ModuleInfo(n,path,path.files(n+'*.hxx')) for n in tqdm(module_names)]'''
    for m in modules: class_dict.update(m.class_dict)
    
    return modules,class_dict

def render(settings,modules,class_dict):
    
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
                                         'class_dict' : class_dict,
                                         'project_name' : name,
                                         'operator_dict' : operator_dict,
                                         'include_pre' : pre,
                                         'include_post' : post}))
    
def validate_result(verbose,n_jobs,folder):
    
    def _validate(f):
        
        tu = parse_tu(f,pre_includes='')
        if len([d for d in tu.diagnostics if d.severity >2]):
            logzero.logger.error('Validation {}: NOK'.format(f))
            if verbose:
                for d in tu.diagnostics:
                    logzero.logger.warning(d)
        else:
            logzero.logger.info('Validation {}: OK'.format(f))
            
    result = Parallel(prefer='processes',n_jobs=n_jobs)\
        (delayed(_validate)(n) for n in Path(folder).files('*.cpp'))
        
    for r in result: pass

def run(settings,
        module_mapping,
        settings_per_module):
    
    name = settings['name']
    path = Path(settings['input_folder'])
    output_path = Path(settings['output_folder'])
    file_pats = settings['include']
    operator_dict = settings['Operators']
    
    pre = settings['Extras']['include_pre']
    post = settings['Extras']['include_post']
    
    all_files = reduce(add,(path.files(pat) for pat in file_pats))
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
                                         'operator_dict' : operator_dict,
                                         'include_pre' : pre,
                                         'include_post' : post}))
    
    return modules