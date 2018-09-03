from clang.cindex import CursorKind, AccessSpecifier, Index
from path import Path

def paths_approximately_equal(p1,p2):
    '''Approximate path equality. This is due to 
    '''
    return p1.split('.')[0] == p2.split('.')[0]

def get_symbols(tu,kind):
    '''Classes defined locally (i.e. without includes) and are not forward declarations
    '''
    tu_path = Path(tu.spelling)

    for child in tu.cursor.get_children():
        if paths_approximately_equal(Path(child.location.file.name),tu_path) \
        and child.kind is kind:
            if child.get_definition() is None:
                pass #forward declaration
            elif not paths_approximately_equal(Path(child.get_definition().location.file.name),tu_path):
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

def get_free_method_definitions(tu):
    '''Free method definitions
    '''
    
    return get_symbols(tu,CursorKind.CXX_METHOD)

class BaseInfo(object):
    '''Base class for the info objects
    '''

    def __init__(self,cur):

        self._cur = cur
        self.name = cur.spelling


class EnumInfo(BaseInfo):
    '''Container for enum parsing results
    '''

    def __init__(self,cur):

        super(EnumInfo,self).__init__(cur)

        self.values = [el.spelling for el in get_enum_values(cur)]

class FunctionInfo(BaseInfo):
    '''Container for function parsing results
    '''

    def __init__(self,cur):

        super(FunctionInfo,self).__init__(cur)

        self.return_type = cur.result_type
        self.args = [el for el in cur.get_arguments()]

class MethodInfo(FunctionInfo):
    '''Container for method parsing results
    '''

    pass

class ConstructorInfo(FunctionInfo):
    '''Container for constructor parsing results
    '''

    pass

class DestructorInfo(FunctionInfo):
    '''Container for constructor parsing results
    '''
    
    pass

class ClassInfo(object):
    '''Container for constructor class results
    '''
    
    def __init__(self,cur):
        
        self._cur = cur
        self.name = cur.spelling
        self.constructors = [ConstructorInfo(el) for el in get_public_constructors(cur)]
        self.methods = [MethodInfo(el) for el in get_public_methods(cur)]
        self.destructors = [DestructorInfo(el) for el in get_public_destructors(cur)]


class HeaderInfo(object):
    '''Container for header parsing results
    '''

    def __init__(self):

        self.dependencies = []
        self.classes = []
        self.functions = []
        self.enums = []
        self.methods = []

    def parse(self, path,
              args=['-x', 'c++', '-std=c++11', '-D__CODE_GENERATOR__' ]):

        ix = Index.create()
        tr_unit = ix.parse(path, args)

        self.dependencies = [el for el in tr_unit.get_includes()]
        self.enums = [EnumInfo(el) for el in get_enums(tr_unit)]
        self.functions = [FunctionInfo(el) for el in get_functions(tr_unit)]
        self.classes = {el.displayname:ClassInfo(el) for el in get_classes(tr_unit)}
        
        #handle freele defined methods
        methods = [el for el in get_free_method_definitions(tr_unit)]
        
        #match methods to classes
        for m in methods:
            cls = self.classes[m.semantic_parent.displayname]
            cls.methods.append(MethodInfo(m))

def process_header(path):
    '''Main function from this module
    '''

    hi = HeaderInfo()
    hi.parse(path)

    return hi

__all__ = [process_header,]

if __name__ == '__main__':
    
    from os import getenv
    from .utils import init_clang
    init_clang()

    conda_prefix = Path(getenv('CONDA_PREFIX'))    

    gp_Ax1 = process_header(conda_prefix /  'include' / 'opencascade' / 'gp_Ax1.hxx')

    for el in gp_Ax1.classes.values():
        print(el.name)
        print(el._cur.location)
        print(el._cur.kind)

    #try public methods
    for el in get_public_methods(el._cur):
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
    gp_Vec2d = process_header(conda_prefix /  'include' / 'opencascade' / 'gp_Vec2d.hxx')

    for el in gp_Vec2d.functions:
        print(el.name)