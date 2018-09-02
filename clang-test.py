from clang.cindex import *
from clang.cindex import CursorKind, AccessSpecifier, Index, Config
from path import Path
from os import getenv


def get_classes(tu):
    '''Classes defined locally (i.e. without includes)
    '''
    
    for child in tu.cursor.get_children():
        if Path(child.location.file.name) == Path(tu.spelling):
            yield child
            
def get_xx(cls,kind,access):
    '''Get children entities of the specified type
    '''
    
    for child in cls.get_children():
        if child.kind is kind and child.access_specifier is access:
                yield child
            
def get_public_methods(cls):
    '''Public methods of a given class
    '''
    
    for child in get_xx(cls,CursorKind.CXX_METHOD,AccessSpecifier.PUBLIC):
        yield child
                
def get_public_operators(cls):
    '''Public operators of a given class
    '''
    
    for m in get_public_methods(cls):
        if 'operator' in m.spelling:
            yield m
            
def get_public_constructors(cls):
    '''Public constructors of a given class
    '''
    
    for child in get_xx(cls,CursorKind.CONSTRUCTOR,AccessSpecifier.PUBLIC):
        yield child
        
def get_public_destructors(cls):
    '''Public destructors of a given class
    '''
    
    for child in get_xx(cls,CursorKind.DESTRUCTOR,AccessSpecifier.PUBLIC):
        yield child
        
def get_private_destructors(cls):
    '''Private destructors of a given class
    '''
    
    for child in get_xx(cls,CursorKind.DESTRUCTOR,AccessSpecifier.PRIVATE):
        yield child
    

if __name__ == '__main__':
    
    conda_prefix = Path(getenv('CONDA_PREFIX'))    
    
    Config.set_library_file(conda_prefix / 'lib' / 'libclang.so')
    i = Index.create()
    
    tu = i.parse(conda_prefix /  'include' / 'opencascade' / 'gp_Ax1.hxx',
                 ['-x', 'c++', '-std=c++11', '-D__CODE_GENERATOR__' ])
    
    tmp = []
    all_classes = []
    for el in tu.cursor.get_children(): 
        if el.kind == CursorKind.CLASS_DECL and 'gp_Ax1.hxx' in el.location.file.name:
            print(el.spelling)
            print(el.location)
            print(el.kind)
            
            tmp.append(el)
        if el.kind == CursorKind.CLASS_DECL:
            all_classes.append(el)
            
    
    methods = [c for c in tmp[-1].get_children() if c.kind == CursorKind.CXX_METHOD]