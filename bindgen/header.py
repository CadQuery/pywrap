from clang.cindex import CursorKind, AccessSpecifier, Index, Config
from path import Path
from os import getenv


def get_symbols(tu,kind):
    '''Classes defined locally (i.e. without includes) and are not forward declarations
    '''
    tu_path = Path(tu.spelling)    
    
    for child in tu.cursor.get_children():
        if Path(child.location.file.name) ==  tu_path and \
        child.kind is kind:
            if child.get_definition() is None:
                pass #forward declaration
            elif Path(child.get_definition().location.file.name) != tu_path:
                pass #forward declaration but declared in an include
            else:
                yield child #legitimate

def get_functions(tu):
    '''Functions defined locally (i.e. without includes)
    '''
    
    return get_symbols(tu,CursorKind.FUNCTION_DECL)
    
def get_enums(tu):
    '''Enums defined locally (i.e. without includes)
    '''
    
    return get_symbols(tu,CursorKind.ENUM_DECL)

def get_enum_values(cur):
    '''Gets enum values
    '''
    
    for child in cur.get_children():
        if child.kind is CursorKind.ENUM_CONSTANT_DECL:
                yield child

def get_classes(tu):
    '''Classes defined locally (i.e. without includes)
    '''
    
    return get_symbols(tu,CursorKind.CLASS_DECL)
            
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

class BaseInfo(object):
    '''Base class for the info objects
    '''
    
    def __init__(self,cur):
        
        self._cur = cur
        self.name = cur.spelling


class EnumInfo(BaseInfo,object):
    '''Contianer for enum parsing results
    '''
    
    def __init__(self,cur):
        
        super(EnumInfo,self).__init__(cur)
        
        self.values = [el.spelling for el in get_enum_values(cur)]
        
class FunctionInfo(BaseInfo,object):
    '''Contianer for enum parsing results
    '''
    
    def __init__(self,cur):
        
        super(FunctionInfo,self).__init__(cur)
        
        self.return_type = cur.result_type
        self.args = [el for el in cur.get_arguments()]

class HeaderInfo(object):
    '''Contianer for header parsing results
    '''
    
    def __init__(self):
        
        self.dependencies = []
        self.classes = []
        self.functions = []
        self.enums = []
        
    def parse(self, path,
              args=['-x', 'c++', '-std=c++11', '-D__CODE_GENERATOR__' ]):
        
        ix = Index.create()
        tr_unit = ix.parse(path, args)
        
        self.dependencies = [el for el in tr_unit.get_includes()]
        self.enums = [EnumInfo(el) for el in get_enums(tr_unit)]
        self.functions = [FunctionInfo(el) for el in get_functions(tr_unit)]
        self.classes = [el for el in get_classes(tr_unit)]
        
def process_header(path):
    '''Main function from this module
    '''
    
    hi = HeaderInfo()
    hi.parse(path)
    
    return hi

__all__ = [process_header,]    

if __name__ == '__main__':
    
    conda_prefix = Path(getenv('CONDA_PREFIX'))    
    
    Config.set_library_file(conda_prefix / 'lib' / 'libclang.so')
    i = Index.create()
    
    gp_Ax1 = process_header(conda_prefix /  'include' / 'opencascade' / 'gp_Ax1.hxx')

    for el in gp_Ax1.classes: 
        print(el.spelling)
        print(el.location)
        print(el.kind)
        
    #try public methods
    for el in get_public_methods(el):
        print(el.spelling)
        print(el.location)
        print(el.kind)
    
    #try enums
    gp_TrsfForm = \
    process_header(conda_prefix /  'include' / 'opencascade' / 'gp_TrsfForm.hxx')
                 
    for el in gp_TrsfForm.enums: 
        print(el.name)
        print(el.values)
        
    #try functions
    gp_Vec2d = process_header(conda_prefix /  'include' / 'opencascade' / 'gp_Vec2d.lxx')
                 
    for el in gp_Vec2d.functions: 
        print(el.name)