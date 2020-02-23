from .header import process_header
from logzero import logger
from toposort import toposort_flatten

from path import Path

class ModuleInfo(object):
    '''Container for the whole module
    '''    
    
    def get_module_name(self,x):
        
        return Path(x).splitpath()[-1].split('.')[0].split('_')[0]
    
    def __init__(self,name,prefix,paths,module_names,settings):
            
        self.prefix = prefix
        self.name = name
        self.headers = []

        logger.debug('Processing headers')        
        
        for p in paths:
            logger.debug(p)
            self.headers.append(process_header(p,prefix,settings))
        
        self.classes = []
        self.class_dict = {}
        self.typedefs = []
        self.typedef_dict = {}
        self.enums = []
        self.functions = []
        self.operators = []
        self.exceptions = []
        self.dependencies = set()
        self.dependencies_headers = set()
        
        for h in self.headers:
            self.classes.extend(h.classes.values())
            self.typedefs.extend(h.typedefs)
            self.enums.extend(h.enums)
            self.functions.extend(h.functions)
            self.operators.extend(h.operators)
            self.class_dict.update(h.class_dict)
            self.typedef_dict.update(h.typedef_dict)
            self.dependencies_headers.update(h.dependencies)
            
        #clean up dependencies
        dependencies_clean = set()
        for d in self.dependencies_headers:
            name = self.get_module_name(d)
            if name in module_names:
                dependencies_clean.add(name)
        
        self.dependencies_headers = dependencies_clean - {self.name}
        
        self.sort_classes()
        
    def sort_classes(self):
        
        class_dict = {c.name : c for c in self.classes}
        dag = {c.name : set(s for s in c.superclass if s in class_dict) for c in self.classes}
        
        self.classes = [class_dict[el] for el in toposort_flatten(dag)]
            
if __name__ == '__main__':
    
    from os import getenv
    from .utils import init_clang
    init_clang()
    
    conda_prefix = Path(getenv('CONDA_PREFIX'))
    p = Path(conda_prefix /  'include' / 'opencascade' )

    gp = ModuleInfo('gp',p,p.files('gp_*.hxx'))    
    for el in [Path(el).split()[-1] for el in gp.dependencies]: print(el)
        
    TColStd = ModuleInfo('TColStd',p,p.files('TColStd_*.hxx'))    
    for el in [Path(el).split()[-1] for el in gp.dependencies]: print(el)
        
    Standard = ModuleInfo('Standard',p,p.files('Standard_*.hxx'))    
    for el in [Path(el).split()[-1] for el in gp.dependencies]: print(el)