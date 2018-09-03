from .header import process_header
import logzero


class ModuleInfo(object):
    '''Conatianer for the whole module
    '''    
    
    def __init__(self,name,prefix,paths):
        
        self.prefix = prefix
        self.name = name
        self.headers = []

        logzero.logger.debug('Processing headers')        
        
        for p in paths:
            logzero.logger.debug(p)
            self.headers.append(process_header(p))
        self.dependencies = []
        
        logzero.logger.debug('Processing dependancies')
        
        for h in self.headers:            
            logzero.logger.debug(h)
            self.dependencies += \
            [inc.source.name for inc in h.dependencies if \
             inc.source.name not in paths \
             and prefix in inc.source.name \
             and name not in Path(inc.source.name).split()[-1]]
             
        self.dependencies = set(self.dependencies)
        
            
            
if __name__ == '__main__':
    
    from path import Path
    from os import getenv
    from .utils import init_clang
    init_clang()
    
    conda_prefix = Path(getenv('CONDA_PREFIX'))

    p = Path(conda_prefix /  'include' / 'opencascade' )

    gp = ModuleInfo('gp',p,p.files('gp_*.hxx'))
    
    for el in [Path(el).split()[-1] for el in gp.dependencies]: print(el)