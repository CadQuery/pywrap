from clang.cindex import CursorKind, AccessSpecifier
from path import Path

from .utils import get_index

def paths_approximately_equal(p1,p2):
    '''Approximate path equality. This is due to 
    '''
    return p1.split('.')[0] == p2.split('.')[0]

def get_symbols(tu,kind):
    '''Symbols defined locally (i.e. without includes) and are not forward declarations
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
                
def get_all_symbols(tu,kind):
    '''All defined symbols of given kind
    '''
    tu_path = Path(tu.spelling)

    for child in tu.cursor.get_children():
        if paths_approximately_equal(Path(child.location.file.name),tu_path) \
        and child.kind is kind:
            yield child

def get_functions(tu):
    '''Functions defined locally (i.e. without includes)
    '''

    return (f for f in get_symbols(tu,CursorKind.FUNCTION_DECL) if 'operator' not in f.spelling)

def get_operators(tu):
    '''Functions defined locally (i.e. without includes)
    '''

    return (f for f in get_symbols(tu,CursorKind.FUNCTION_DECL) if 'operator' in f.spelling)

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

    return  get_symbols(tu,CursorKind.CLASS_DECL)

def get_x(cls,kind):
    '''Get children entities of the specified type excluding forward declataions
    '''

    for child in cls.get_children():
        if child.kind is kind and child.get_definition():
                yield child

def get_xx(cls,kind,access):
    '''Get children entities of the specified type with given access specifier
    '''

    for child in cls.get_children():
        if child.kind is kind and child.access_specifier is access:
                yield child
    
def get_base_class(c):
    '''Get all class-baseclass pairs
    '''
    #import pdb; pdb.set_trace()
    if c.get_definition():
        rv = list(get_x(c.get_definition(),CursorKind.CXX_BASE_SPECIFIER))
    else:
        rv = list(get_x(c,CursorKind.CXX_BASE_SPECIFIER))
        
    if len(rv) == 0:
        return None
    else:
        return rv[0].type.spelling
    
def get_inheritance_relations(tu):
    '''Inheritance relations pairs
    '''
    
    all_classes = get_x(tu.cursor,CursorKind.CLASS_DECL)
    
    for c in all_classes:
        yield c.spelling,get_base_class((c))

def get_public_methods(cls):
    '''Public methods of a given class
    '''

    for child in get_xx(cls,CursorKind.CXX_METHOD,AccessSpecifier.PUBLIC):
        if not child.is_static_method() and not child.spelling.startswith('operator'):
            yield child

def get_public_static_methods(cls):
    '''Public static methods of a given class
    '''

    for child in get_xx(cls,CursorKind.CXX_METHOD,AccessSpecifier.PUBLIC):
        if child.is_static_method() and not child.spelling.startswith('operator'):
            yield child

def get_public_operators(cls):
    '''Public operators of a given class
    '''

    for child in get_xx(cls,CursorKind.CXX_METHOD,AccessSpecifier.PUBLIC):
        if not child.is_static_method() and child.spelling.startswith('operator'):
            yield child

def get_public_static_operators(cls):
    '''Public static operators of a given class
    '''

    for child in get_xx(cls,CursorKind.CXX_METHOD,AccessSpecifier.PUBLIC):
        if child.is_static_method() and child.spelling.startswith('operator'):
            yield child

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

        self.name = cur.spelling
        self.comment = cur.brief_comment


class EnumInfo(BaseInfo):
    '''Container for enum parsing results
    '''

    def __init__(self,cur):

        super(EnumInfo,self).__init__(cur)
        
        self.comment = cur.brief_comment
        self.values = [el.spelling for el in get_enum_values(cur)]

class FunctionInfo(BaseInfo):
    '''Container for function parsing results
    '''

    def __init__(self,cur):

        super(FunctionInfo,self).__init__(cur)

        self.comment = cur.brief_comment
        self.full_name = cur.displayname
        self.return_type = cur.result_type.spelling
        self.args = {el.spelling : el.type.spelling for el in cur.get_arguments()}

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
        
        self.name = cur.spelling
        self.comment = cur.brief_comment
        
        self.constructors = [ConstructorInfo(el) for el in get_public_constructors(cur)]
        
        self.methods = [MethodInfo(el) for el in get_public_methods(cur)]
        self.static_methods = [MethodInfo(el) for el in get_public_static_methods(cur)]

        self.operators = [MethodInfo(el) for el in get_public_operators(cur)]        
        self.static_operators = [MethodInfo(el) for el in get_public_static_operators(cur)]
        
        self.destructors = [DestructorInfo(el) for el in get_public_destructors(cur)]
        self.private_destructors = [DestructorInfo(el) for el in get_private_destructors(cur)]
        
        self.ptr = None
        self.superclass = None
        self.rootclass = None


class HeaderInfo(object):
    '''Container for header parsing results
    '''

    def __init__(self):

        self.dependencies = []
        self.classes = {}
        self.functions = []
        self.enums = []
        self.methods = []
        self.inheritance = {}
        
    def resolve_inheritance(self,cls):
        
        inheritance = self.inheritance        
    
        cls.superclass = inheritance.get(cls.name,None)
        
        rootclass = tmp = cls.superclass
        while tmp in inheritance:
            tmp = inheritance[tmp]
            if tmp: rootclass = tmp
            
        cls.rootclass = rootclass
            

    def parse(self, path,
              args=['-x', 'c++', '-std=c++11', '-D__CODE_GENERATOR__' ]):

        ix = get_index()
        tr_unit = ix.parse(path, args)

        self.name = path
        self.short_name = path.splitpath()[-1]
        self.dependencies = [el.location.file.name for el in tr_unit.get_includes()]
        self.enums = [EnumInfo(el) for el in get_enums(tr_unit)]
        self.functions = [FunctionInfo(el) for el in get_functions(tr_unit)]
        self.operators = [FunctionInfo(el) for el in get_operators(tr_unit)]
        self.classes = {el.displayname:ClassInfo(el) for el in get_classes(tr_unit)}
        self.inheritance = {k:v for k,v in get_inheritance_relations(tr_unit)}
        
        #handle freely defined methods
        methods = [el for el in get_free_method_definitions(tr_unit)]
        
        #match methods to classes
        for m in methods:
            cls = self.classes.get(m.semantic_parent.displayname,None)
            if cls:
                cls.methods.append(MethodInfo(m))
                
        #resolve inheritance relations
        for c in self.classes.values():
            self.resolve_inheritance(c)
                

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

    #try public methods
    for el in el.methods:
        print(el.name,el.args,el.return_type)

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
        
    for el in gp_Vec2d.operators:
        print(el.name)
        
    #try inheritance
    TopoDS = process_header(conda_prefix /  'include' / 'opencascade' / 'TopoDS_Solid.hxx')

    for k in TopoDS.inheritance:
        print(k,TopoDS.inheritance[k])