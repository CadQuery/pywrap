from typing import List, Tuple, Any, Mapping, Optional
from itertools import chain

from clang.cindex import CursorKind, TypeKind, AccessSpecifier
from path import Path

from .type_parser import parse_type
from .translation_unit import parse_tu
from .utils import current_platform

def paths_approximately_equal(p1 : str, p2 : str):
    '''Approximate path equality. This is due to
    '''
    return any([Path(p1).name.split('.')[0] == Path(p).name.split('.')[0] for p in p2])


def is_public(el):

    return (el.acess_specifier == AccessSpecifier.PUBLIC) or (el.access_specifier is None)

def get_symbols(tu,
                kind,
                ignore_forwards=True,
                search_in = (CursorKind.NAMESPACE,)):
    '''
    Symbols defined locally (i.e. without includes) and are not forward declarations
    Search_in allows to explore nested entities as well.
    
    '''
    tu_path = tu.path
    
    def _get_symbols(cursor,kind,ignore_forwards):
    
        for child in cursor.get_children():
            if paths_approximately_equal(Path(child.location.file.name),tu_path) \
            and child.kind == kind:
                if ignore_forwards:
                    if child.get_definition() is None:
                        pass #forward declaration
                    elif not paths_approximately_equal(Path(child.get_definition().location.file.name),tu_path):
                        pass #forward declaration but declared in an include
                    else:
                        yield child #legitimate
                else:
                    yield child
            if paths_approximately_equal(Path(child.location.file.name),tu_path) \
            and child.kind in search_in:
                for nested in _get_symbols(child,kind,ignore_forwards):
                    if nested.access_specifier == AccessSpecifier.PUBLIC: yield nested
    
    for child in _get_symbols(tu.cursor, kind, ignore_forwards):
        yield child

def get_forward_declarations(tu):
    '''Get all symbols that are forward declared'''
    tu_path = tu.path

    for child in tu.cursor.get_children():
        if paths_approximately_equal(Path(child.location.file.name),tu_path):
            if child.get_definition() is None:
                yield child

def get_all_symbols(tu,kind):
    '''All defined symbols of given kind
    '''
    tu_path = tu.path

    for child in tu.cursor.get_children():
        if paths_approximately_equal(Path(child.location.file.name),tu_path) \
        and child.kind is kind:
            yield child

def get_all_symbols_multi(tu,kinds):
    '''All defined symbols of given kinds
    '''
    tu_path = tu.path

    for child in tu.cursor.get_children():
        if paths_approximately_equal(Path(child.location.file.name),tu_path) \
        and any((child.kind is kind for kind in kinds)):
            yield child

def get_functions(tu):
    '''Functions defined locally (i.e. without includes)
    '''

    return (f for f in get_symbols(tu,CursorKind.FUNCTION_DECL,False) if 'operator' not in f.spelling)

def get_function_templates(tu):
    '''Function templates defined locally (i.e. without includes)
    '''

    return (f for f in get_symbols(tu,CursorKind.FUNCTION_TEMPLATE,False) if 'operator' not in f.spelling)

def get_operators(tu):
    '''Functions defined locally (i.e. without includes)
    '''

    return (f for f in get_symbols(tu,CursorKind.FUNCTION_DECL,False) if 'operator' in f.spelling)

def get_operator_templates(tu):
    '''Operator templates defined locally (i.e. without includes)
    '''

    return (f for f in get_symbols(tu,CursorKind.FUNCTION_TEMPLATE,False) if 'operator' in f.spelling)

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

def get_typedefs(tu):
    '''Typedefs defined locally (i.e. without includes)
    '''

    return get_symbols(tu,CursorKind.TYPEDEF_DECL)

def get_classes(tu):
    '''Classes defined locally (i.e. without includes)
    '''

    return  chain(get_symbols(tu,CursorKind.CLASS_DECL),
                  get_symbols(tu,CursorKind.STRUCT_DECL))

def get_class_templates(tu):
    '''Class templates defined locally (i.e. without includes)
    '''

    return  get_symbols(tu,CursorKind.CLASS_TEMPLATE)

def get_x(cls,kind):
    '''Get children entities of the specified type excluding forward declataions
    '''

    for child in cls.get_children():
        if child.kind is kind and child.get_definition():
                yield child

def get_x_multi(cls,kinds):
    '''Get children entities of the specified types excluding forward declataions
    '''

    for child in cls.get_children():
        if any((child.kind is kind for kind in kinds)) and child.get_definition():
            yield child

def get_xx(cls,kind,access):
    '''Get children entities of the specified type with given access specifier
    '''

    for child in cls.get_children():
        if child.kind is kind and child.access_specifier is access:
                yield child

def get_template_type_params(cls):
    '''Get all template type params
    '''

    for t in get_x_multi(cls,(CursorKind.TEMPLATE_TYPE_PARAMETER, CursorKind.TEMPLATE_NON_TYPE_PARAMETER)):
        if len(list(t.get_children())) == 0:
            yield t,None
        else:
            yield t,''.join([tok.spelling for tok in t.get_tokens()][3:])

def get_base_class(c):
    '''Get all class-baseclass pairs with public or protected inheritance
    '''

    if c.get_definition():
        rv = [el for el in get_x(c.get_definition(),CursorKind.CXX_BASE_SPECIFIER) \
              if el.access_specifier in (AccessSpecifier.PUBLIC,)] # how to handle  AccessSpecifier.PROTECTED?
    else:
        rv = [el for el in get_x(c,CursorKind.CXX_BASE_SPECIFIER) \
              if el.access_specifier in (AccessSpecifier.PUBLIC,)] # how to handle  AccessSpecifier.PROTECTED?

    if len(rv) == 0:
        return []
    else:
        return [el.type.spelling for el in rv]

def get_inheritance_relations(tu):
    '''Inheritance relations pairs
    '''

    all_classes = get_x(tu.cursor,CursorKind.CLASS_DECL)

    for c in all_classes:
        yield c.spelling,get_base_class((c))
        
    all_templates = get_x(tu.cursor,CursorKind.CLASS_TEMPLATE)

    for c in all_templates:
        yield c.spelling,get_base_class((c))
        
def get_public_fields(cls):
    '''Public methods of a given class
    '''

    for child in get_xx(cls,CursorKind.FIELD_DECL, AccessSpecifier.PUBLIC):
        yield child
        
def get_public_enums(cls):
    '''Public enums of a given class
    '''

    for child in get_xx(cls,CursorKind.ENUM_DECL, AccessSpecifier.PUBLIC):
        yield child

def get_public_methods(cls):
    '''Public methods of a given class
    '''

    for child in get_xx(cls,CursorKind.CXX_METHOD,AccessSpecifier.PUBLIC):
        if not child.is_static_method() and not child.spelling.startswith('operator'):
            yield child

def get_protected_pure_virtual_methods(cls):
    '''Protected pure virtual methods of a given class
    '''

    for child in get_xx(cls,CursorKind.CXX_METHOD,AccessSpecifier.PROTECTED):
        if not child.is_static_method() and not child.spelling.startswith('operator') and child.is_pure_virtual_method():
            yield child

def get_private_pure_virtual_methods(cls):
    '''Private pure virtual methods of a given class
    '''

    for child in get_xx(cls,CursorKind.CXX_METHOD,AccessSpecifier.PRIVATE):
        if not child.is_static_method() and not child.spelling.startswith('operator') and child.is_pure_virtual_method():
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

def get_private_constructors(cls):
    '''Private constructors of a given class
    '''

    for child in get_xx(cls,CursorKind.CONSTRUCTOR,AccessSpecifier.PRIVATE):
        yield child

def get_protected_constructors(cls):
    '''Protected constructors of a given class
    '''

    for child in get_xx(cls,CursorKind.CONSTRUCTOR,AccessSpecifier.PROTECTED):
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

def get_protected_destructors(cls):
    '''Private destructors of a given class
    '''

    for child in get_xx(cls,CursorKind.DESTRUCTOR,AccessSpecifier.PROTECTED):
        yield child

def get_free_method_definitions(tu):
    '''Free method definitions
    '''

    return (el for el in get_symbols(tu,CursorKind.CXX_METHOD) \
            if not el.is_static_method() \
            and el.access_specifier==AccessSpecifier.PUBLIC)

class BaseInfo(object):
    '''Base class for the info objects
    '''
    
    name : str
    comment : str

    def __init__(self,cur):

        self.name = cur.spelling
        self.comment = cur.brief_comment

class FieldInfo(BaseInfo):
    '''Container for field parsing reults
    '''
    
    type : str
    const : bool
    pod : bool
    
    def __init__(self,cur):

        super(FieldInfo,self).__init__(cur)
        
        self.type = cur.type.spelling
        self.const = cur.type.is_const_qualified()
        self.pod = cur.type.is_pod()

class EnumInfo(BaseInfo):
    '''Container for enum parsing results
    '''
    
    comment : str
    values : List[str]
    anonymous : bool

    def __init__(self,cur):

        super(EnumInfo,self).__init__(cur)

        self.comment = cur.brief_comment
        self.values = [el.spelling for el in get_enum_values(cur)]
        self.anonymous = False
        self.name = cur.type.spelling
            
        if 'anonymous' in self.name:
            self.anonymous = True
            self.name = '::'.join(self.name.split('::')[:-1]) #get rid of anonymous
            

class FunctionInfo(BaseInfo):
    '''Container for function parsing results
    '''
    
    full_name : str
    mangled_name : str
    return_type : str
    inline : bool
    pointer_by_ref : bool
    args : List[Tuple[str, str, str]]
    default_value_types : List[str]

    KIND_DICT = {TypeKind.LVALUEREFERENCE : ' &',
                 TypeKind.RVALUEREFERENCE : ' &&',
                 TypeKind.POINTER : ' *'}

    def __init__(self,cur):

        super(FunctionInfo,self).__init__(cur)

        self.comment = cur.brief_comment
        self.full_name = cur.displayname
        self.mangled_name = cur.mangled_name
        self.return_type = cur.result_type.spelling
        self.inline = cur.get_definition().is_inline() if cur.get_definition() else False
        self.pointer_by_ref = any(self._pointer_by_ref(el) for el in cur.get_arguments())
        self.args = [(el.spelling,self._underlying_type(el),self._default_value(el)) for el in cur.get_arguments()]
        self.default_value_types = [self._underlying_type(el,False) for el in cur.get_arguments() if self._default_value(el)]


    def _pointer_by_ref(self,cur):
        '''Check is type is a Pointer passed by reference
        '''

        rv = False
        t = cur.type

        # if passed by ref
        if t.kind == TypeKind.LVALUEREFERENCE:
            tp = t.get_pointee().get_canonical()
            # if underlying type is a pointer
            if tp.kind in (TypeKind.POINTER,):
                rv = True

        return rv

    def _underlying_type(self,cur,add_qualifiers=True):
        '''Tries to resolve the underlying type. Needed for typedefed templates.
        '''

        ptr = self.KIND_DICT.get(cur.type.kind,'')

        # if lvaule,rvalue or pointer type
        if ptr:
            const_ptr = ' const ' if cur.type.is_const_qualified() else ''
            pointee = cur.type.get_pointee()
            const = ' const ' if pointee.is_const_qualified() else ''
            decl = pointee.get_declaration()
        else:
            const_ptr = ''
            const = ' const ' if cur.type.is_const_qualified() else ''
            decl = cur.type.get_declaration()

        # if typedef that is not POD
        if decl.kind == CursorKind.TYPEDEF_DECL and not decl.underlying_typedef_type.is_pod():
            spelling = decl.underlying_typedef_type.spelling
            if add_qualifiers:
                rv=const+spelling+ptr+const_ptr
            else:
                rv=spelling
        else:
            rv = cur.type.spelling

        # strip possible opencascade::handle<T> when
        if not add_qualifiers:
            rv = parse_type(rv)

        return rv

    def _default_value(self,cur):
        '''Tries to extract default value
        '''

        rv = None
        tokens = [t.spelling for t in cur.get_tokens()]
        if '=' in tokens:
            rv = ' '.join(tokens[tokens.index('=')+1:])

        return rv




class MethodInfo(FunctionInfo):
    '''Container for method parsing results
    '''

    const : bool
    virtual : bool
    pure_virtual : bool

    def __init__(self,cur):

        super(MethodInfo,self).__init__(cur)

        self.const = cur.is_const_method()
        self.virtual = cur.is_virtual_method()
        self.pure_virtual = cur.is_pure_virtual_method()

class ConstructorInfo(MethodInfo):
    '''Container for constructor parsing results
    '''

    pass

class DestructorInfo(FunctionInfo):
    '''Container for destructor parsing results
    '''

    pass

class ClassInfo(object):
    '''Container for class parsing results
    '''
    
    name : str
    comment : str
    abstract : bool

    constructors : List[ConstructorInfo]
    nonpublic_constructors : List[ConstructorInfo]

    fields : List[FieldInfo]
    
    enums : List[EnumInfo]

    methods : List[MethodInfo]
    protected_virtual_methods : List[MethodInfo]
    private_virtual_methods : List[MethodInfo]
    static_methods : List[MethodInfo]
    static_methods_byref : List[MethodInfo]
    methods_byref : List[MethodInfo]
    methods_return_byref : List[MethodInfo]

    operators : List[MethodInfo]
    static_operators : List[MethodInfo]

    destructors : List[DestructorInfo]
    nonpublic_destructors : List[DestructorInfo]

    ptr : Any #is this needed?
    
    superclass : List[str]
    rootclass : List[str]
    superclasses : List[str]

    methods_dict : Mapping[str,MethodInfo]
    protected_virtual_methods_dict : Mapping[str,MethodInfo]
    private_virtual_methods_dict : Mapping[str,MethodInfo]

    def __init__(self,cur):

        self.name = cur.type.spelling
        self.comment = cur.brief_comment
        self.abstract = cur.is_abstract_record()

        self.constructors = self.filter_rvalues((ConstructorInfo(el) for el in get_public_constructors(cur)))
        self.nonpublic_constructors = [ConstructorInfo(el) for el in get_private_constructors(cur)]\
            + [ConstructorInfo(el) for el in get_protected_constructors(cur)]

        self.fields = [FieldInfo(el) for el in  get_public_fields(cur)]
        self.enums = [EnumInfo(el) for el in  get_public_enums(cur)]

        self.methods = self.filter_rvalues((MethodInfo(el) for el in get_public_methods(cur)))
        self.protected_virtual_methods = self.filter_rvalues((MethodInfo(el) for el in get_protected_pure_virtual_methods(cur)))
        self.private_virtual_methods = self.filter_rvalues((MethodInfo(el) for el in get_private_pure_virtual_methods(cur)))

        self.static_methods = self.filter_rvalues((MethodInfo(el) for el in get_public_static_methods(cur)))
        
        self.static_methods_byref = []
        self.methods_byref = []
        self.methods_return_byref = []

        self.operators = [MethodInfo(el) for el in get_public_operators(cur)]
        self.static_operators = [MethodInfo(el) for el in get_public_static_operators(cur)]

        self.destructors = [DestructorInfo(el) for el in get_public_destructors(cur)]
        self.nonpublic_destructors = [DestructorInfo(el) for el in get_private_destructors(cur)]\
            + [DestructorInfo(el) for el in get_protected_destructors(cur)]

        self.ptr = None
        self.superclass = []
        self.rootclass = []
        self.superclasses = []

        self.methods_dict = {m.name:m for m in self.methods}
        self.protected_virtual_methods_dict = {m.name:m for m in self.protected_virtual_methods}
        self.private_virtual_methods_dict = {m.name:m for m in self.private_virtual_methods}

    def filter_rvalues(self,funcs):

        return [f for f in funcs if not any(('&&' in arg for _,arg,_ in f.args))]

    def extend_defintion(self,other):

        new_comment = ''
        if self.comment:
            new_comment += self.comment
        if other.comment:
            new_comment += other.comment
        self.comment = new_comment

        self.constructors += other.constructors
        self.nonpublic_constructors +=  other.nonpublic_constructors
        self.methods += other.methods
        self.protected_virtual_methods += other.protected_virtual_methods
        self.private_virtual_methods += other.private_virtual_methods
        self.static_methods += other.static_methods
        self.operators += other.operators
        self.static_operators += other.static_operators
        self.destructors += other.destructors
        self.nonpublic_destructors +=  other.nonpublic_destructors
        
        self.fields += other.fields
        self.enums += other.enums

        self.methods_dict = {**self.methods_dict,**other.methods_dict}
        self.protected_virtual_methods_dict = {**self.protected_virtual_methods_dict,**other.protected_virtual_methods_dict}
        self.private_virtual_methods_dict = {**self.protected_virtual_methods_dict,**other.protected_virtual_methods_dict}

class ClassTemplateInfo(ClassInfo):
  
    type_params : List[Tuple[Optional[str],str,str]]

    def __init__(self,cur):

         super(ClassTemplateInfo,self).__init__(cur)
         self.name = cur.spelling
         self.type_params = [(None if el.spelling == el.type.spelling else el.type.spelling,
                              el.spelling,
                              default) for el,default in get_template_type_params(cur)]

class TypedefInfo(BaseInfo):
  
    type : str
    pod : bool
    template_base : List[str]
    template_args : List[str]

    def __init__(self,cur):

        super(TypedefInfo,self).__init__(cur)

        t = cur.underlying_typedef_type

        self.type = t.spelling
        self.pod = t.is_pod()

        if not self.pod:
            self.template_base = [ch.spelling for ch in cur.get_children() if ch.kind == CursorKind.TEMPLATE_REF]
            self.template_args = [ch.spelling for ch in cur.get_children() if ch.kind == CursorKind.TYPE_REF]

class ForwardInfo(BaseInfo):

    pass

class HeaderInfo(object):
    '''Container for header parsing results
    '''
    
    name : str
    short_name : str
    dependencies : List[str]
    classes : Mapping[str, ClassInfo]
    class_templates : Mapping[str, ClassTemplateInfo]
    functions : List[FunctionInfo]
    operators : List[FunctionInfo]
    enums : List[EnumInfo]
    methods : List[MethodInfo]
    inheritance : Mapping[str,str]
    typedefs : List[TypedefInfo]
    typedef_dict : Mapping[str,str]
    forwards : List[ForwardInfo]

    def __init__(self):

        self.dependencies = []
        self.classes = {}
        self.class_templates = {}
        self.functions = []
        self.enums = []
        self.methods = []
        self.inheritance = {}
        self.typedefs = []
        self.forwards = []

    def resolve_inheritance(self,cls):

        inheritance = self.inheritance
        superclasses = cls.superclasses
        rootclass = cls.rootclass
        
        cls.superclass = inheritance.get(cls.name,[])
        
        def _resolve_inheritance(node):
            '''Recurisvely traverse the inheritance tree'''
            
            for el in node:
                superclasses.append(el)
                
                if el in inheritance:
                    _resolve_inheritance(inheritance[el])
                else:
                    rootclass.append(el)
        
        _resolve_inheritance(cls.superclass)


    def parse(self, path,input_folder,settings,module_name):

        module_settings= settings['Modules'].get(module_name)

        if module_settings:
            tu_parsing_header = module_settings['parsing_headers'].get(path.name,'')
        else:
            tu_parsing_header = ''

        tr_unit = parse_tu(path,
                           input_folder,
                           prefix=settings[current_platform()]['prefix'],
                           platform_includes=settings[current_platform()]['includes'],
                           parsing_header=settings['parsing_header'],
                           tu_parsing_header=tu_parsing_header,
                           platform_parsing_header=settings[current_platform()]['parsing_header'])

        self.name = path
        self.short_name = path.splitpath()[-1]
        self.dependencies = [el.location.file.name for el in tr_unit.get_includes()]
        self.enums = [EnumInfo(el) for el in get_enums(tr_unit)]
        self.functions = [FunctionInfo(el) for el in get_functions(tr_unit)]
        self.operators = [FunctionInfo(el) for el in get_operators(tr_unit)]

        self.classes = {}

        for el in get_classes(tr_unit):
            ci = ClassInfo(el)
            if ci.name in self.classes:
                self.classes[ci.name].extend_defintion(ci)
            else:
                self.classes[ci.name] = ci

        self.class_dict = {k : self.name for k in self.classes}
        self.class_templates = {el.displayname:ClassTemplateInfo(el) for el in get_class_templates(tr_unit)}
        self.class_template_dict = {k: self.name for k in self.class_templates}
        self.inheritance = {k:v for k,v in get_inheritance_relations(tr_unit) if v}
        self.typedefs = [TypedefInfo(el) for el in get_typedefs(tr_unit)]
        self.typedef_dict = {t.name : self.name for t in self.typedefs}
        self.forwards = [ForwardInfo(el) for el in get_forward_declarations(tr_unit)]

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
            
        for c in self.class_templates.values():
            self.resolve_inheritance(c)

        return tr_unit

def process_header(path,input_folder,settings,module_name=None):
    '''Main function from this module
    '''

    hi = HeaderInfo()
    hi.parse(path,input_folder,settings,module_name)

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
