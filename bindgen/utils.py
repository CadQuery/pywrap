from clang.cindex import Config, Index
from path import Path
from os import getenv

initialized = False
ix = None

def init_clang():
    
    global initialized,ix
    
    if not initialized:
        conda_prefix = Path(getenv('CONDA_PREFIX'))
        Config.set_library_file(conda_prefix / 'lib' / 'libclang.so')
        
        initialized = True
        ix = Index.create()
        
def get_index():
    
    global initialized,ix
    
    if not initialized: init_clang()
    
    return ix