from clang.cindex import Config, Index, Cursor
from cymbal import monkeypatch_cursor
from ctypes import c_uint
from path import Path
from os import getenv
from sys import platform

initialized = False
ix = None

def init_clang():
    
    global initialized,ix
    
    if not initialized:
        conda_prefix = Path(getenv('CONDA_PREFIX'))
        
        if platform.startswith('win'):
            Config.set_library_file(conda_prefix / 'Library' / 'bin' / 'libclang.dll')
        else:
            Config.set_library_file(conda_prefix / 'lib' / 'libclang.so')
        
        # Monkeypatch clang
        monkeypatch_cursor('is_virtual',
                           'clang_isVirtualBase',
                           [Cursor], c_uint)
        
        monkeypatch_cursor('is_inline',
                           'clang_Cursor_isFunctionInlined',
                           [Cursor], c_uint)
        
        
        monkeypatch_cursor('get_specialization',
                           'clang_getSpecializedCursorTemplate',
                           [Cursor], Cursor)
        
        monkeypatch_cursor('get_template_kind',
                           'clang_getTemplateCursorKind',
                           [Cursor], c_uint)
        
        monkeypatch_cursor('get_num_overloaded_decl',
                           'clang_getNumOverloadedDecls',
                           [Cursor], c_uint)
        
        initialized = True
        ix = Index.create()

        
def get_index():
    
    global initialized,ix
    
    if not initialized: init_clang()
    
    return ix