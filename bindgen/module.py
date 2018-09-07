from .header import process_header
import logzero

from path import Path

class ModuleInfo(object):
    '''Conatianer for the whole module
    '''    
    
    def get_module_name(self,x):
        
        return Path(x).splitpath()[-1].split('.')[-2].split('_')[0]
    
    def __init__(self,name,prefix,paths):
        
        self.prefix = prefix
        self.name = name
        self.headers = []

        logzero.logger.debug('Processing headers')        
        
        for p in paths:
            logzero.logger.debug(p)
            self.headers.append(process_header(p))
        
        dependencies = []
        
        logzero.logger.debug('Processing dependancies')
        
        for h in self.headers:            
            logzero.logger.debug(h.name)
            dependencies += \
            [self.get_module_name(inc) for inc in h.dependencies if \
             inc not in paths \
             and prefix in inc \
             and name not in Path(inc).splitpath()[-1]]
             
        self.dependencies = set(dependencies) - set((name,))
        
        self.classes = []
        self.enums = []
        self.functions = []
        self.operators = []
        for h in self.headers:
            self.classes.extend(h.classes.values())
            self.enums.extend(h.enums)
            self.functions.extend(h.functions)
            self.operators.extend(h.operators)
            
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