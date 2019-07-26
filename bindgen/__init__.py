from functools import reduce
from operator import add
from re import match


import logzero
import toml as toml
import pandas as pd

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

def read_symbols(p):
    '''Read provided symbols file and return a dataframe
    
    This information is used later for flagging undefined symbols
    '''
    
    sym = pd.read_table(p,header=None,names=['adr','code','name'],delimiter=' ',
                        error_bad_lines=False).dropna()
    
    # return only defined symbols
    return sym.query('code == "T"')

def remove_undefined(m,sym):
    
       
    #exclude methods
    for c in m.classes:
        c.methods = [m for m in c.methods if sym.name.str.contains('{}::{}'.format(c.name,m.name)).any()]
    
    #exclude functions
    m.functions = [f for f in m.functions if sym.name.str.startswith(f.name).any()]

def transform_module(m,
                     sym,
                     settings,
                     settings_per_module):
    
    s = settings_per_module.get(m.name,None)
    if s:
        #exclude classes
        m.classes = [c for c in m.classes if c.name not in s['exclude_classes']]
        
        #exclude methods
        for pat in s['exclude_methods']:
            cls_pat,m_pat = pat.split('::')
            for c in (c for c in m.classes if match(cls_pat,c.name)):
                c.methods = [m for m in c.methods if not match(m_pat,m.name)]
        
        #exclude functions
        m.functions = [f for f in m.functions if f.name not in s['exclude_functions']]
        for h in m.headers:
            h.functions = [f for f in h.functions if f.name not in s['exclude_functions']]
    
    #collect exceptions
    for c in m.classes:
        if any([match(pat,c.name) for pat in settings['exceptions']]):
            m.exceptions.append(c)
        elif c.superclass:
            if any([match(pat,c.superclass) for pat in settings['exceptions']]):
                m.exceptions.append(c)
            elif any([match(pat,c.rootclass) for pat in settings['exceptions']]):
                m.exceptions.append(c)
    for ex in m.exceptions:
        m.classes.remove(ex)
    
    # remove undefined symbols
    remove_undefined(m,sym)

def parse_modules(verbose,
                  n_jobs,
                  settings,
                  module_mapping,
                  settings_per_module):

    path = Path(settings['input_folder'])
    file_pats = settings['include']
    file_exc = settings['exclude']
    
    all_files = reduce(add,(path.files(pat) for pat in file_pats))    
    all_files = [f for f in all_files if f.name not in file_exc]
    module_names = sorted(set((module_mapping(p) for p in all_files)))
    
    sym = read_symbols(settings['Symbols']['path'])
    
    modules = []
    class_dict = {}
    
    def _process_module(n):
        if not verbose:
            logzero.logger.setLevel(logzero.logging.INFO)
        return ModuleInfo(n,path,[ f for f in path.files(n+'*.hxx') if f.name not in file_exc])
    
    modules = Parallel(prefer='processes',n_jobs=n_jobs)\
        (delayed(_process_module)(n) for n in tqdm(module_names))
    '''
    modules=[ModuleInfo(n,path,path.files(n+'*.hxx')) for n in tqdm(module_names)]'''
    
    #ignore functions and classes based on settings and update the global class_dict
    for m in modules:
        transform_module(m,sym,settings,settings_per_module)
        class_dict.update(m.class_dict)
    
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
    template_main = jinja_env.get_template('template_main.j2')
    
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
    
        with open('{}.cpp'.format(name),'w') as f:
                f.write(template_main.render({'name' : name,
                                              'modules' : modules}))
    
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
    
    modules,class_dict = parse_modules(False,1,settings,
                                       module_mapping,settings_per_module)    
    render(settings,modules,class_dict)
    
    return modules