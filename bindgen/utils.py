from clang.cindex import Config, Index, Cursor
from ctypes import c_uint
from path import Path
from os import getenv
from sys import platform, prefix

from .cymbal import monkeypatch_cursor

initialized = False
ix = None


def current_platform():
    
    rv=None
    if platform.startswith('win'):
        rv='Windows'
    elif platform.startswith('linux'):
        rv='Linux'
    elif platform.startswith('darwin'):
        rv='OSX'
    elif platform.startswith('freebsd'):
        rv='FreeBSD'
    else:
        raise RuntimeError(f'Unsupported platform: {platform}')
        
    return rv

def on_windows():
    
    rv = False
    if platform.startswith('win'):
        rv = True
        
    return rv

def get_includes(rv=[]):
    
    if rv:
        pass
    elif on_windows():
        rv.append(Path(prefix) / 'Library/include/clang/')
    else:
        rv.append(Path(prefix) / 'lib/clang/8.0.0/include/')
        rv.append(Path(prefix) / 'lib/clang/6.0.1/include/')
        rv.append(Path(prefix) / 'lib/clang/9.0.1/include/')
        rv.append(Path(prefix) / 'lib/clang/10.0.1/include/')
        rv.append(Path(prefix) / 'include/c++/v1/')
    
    return rv

def init_clang(path=None):
    
    global initialized,ix
    
    if not initialized:
        conda_prefix = Path(getenv('CONDA_PREFIX', ''))
        
        if path:
            pass
        elif platform.startswith('win'):
            path = conda_prefix / 'Library' / 'bin' / 'libclang.dll'
        elif platform.startswith('linux') or platform.startswith('freebsd'):
            path = conda_prefix / 'lib' / 'libclang.so'
        elif platform.startswith('darwin'):
            path = conda_prefix / 'lib' / 'libclang.dylib'
        
        Config.set_library_file(path)
        
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
