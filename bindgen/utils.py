from clang.cindex import Config
from path import Path
from os import getenv

initialized = False

def init_clang():
    
    global initialized    
    
    if not initialized:
        conda_prefix = Path(getenv('CONDA_PREFIX'))
        Config.set_library_file(conda_prefix / 'lib' / 'libclang.so')
        
        initialized = True