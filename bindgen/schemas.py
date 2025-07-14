from schema import Schema, Optional

method_schema = Schema(
    {
        "body": str,
        Optional("help", default=None): str,
        Optional("arguments", default=[]): [str],
        Optional("return_policy", default=None): str,
    }
)

function_schema = method_schema

class_schema = Schema(
    {
        Optional("exclude_constructors", default=[]): [int],
        Optional("additional_constructors", default=[]): [method_schema],
        Optional("additional_methods", default={}): {str: method_schema},
        Optional("additional_static_methods", default={}): {str: method_schema},
    }
)

template_schema = Schema({Optional("exclude_constructors", default=[]): [int]})

module_schema = Schema(
    {
        Optional("module_parsing_header", default=""): str,
        Optional("parsing_headers", default={}): {str: str},
        Optional("include_header_pre_top", default=None): str,
        Optional("include_header_pre", default=None): str,
        Optional("include_body_pre", default=None): str,
        Optional("exclude_functions", default=[]): [str],
        Optional("exclude_classes", default=[]): [str],
        Optional("exclude_class_templates", default=[]): [str],
        Optional("exclude_methods", default=[]): [str],
        Optional("exclude_class_template_methods", default=[]): [str],
        Optional("exclude_typedefs", default=[]): [str],
        Optional("include_body_post", default=None): str,
        Optional("include_body_template_post", default=None): str,
        Optional("include_header_post", default=None): str,
        Optional("template_specializations", default=[]): [str],
        Optional("Classes", default={}): {str: class_schema},
        Optional("Templates", default={}): {str: template_schema},
        Optional("additional_functions", default={}): {str: function_schema},
    }
)

platform_settings = Schema(
    {
        "symbols": str,
        Optional("modules", default=[]): [str],
        Optional("includes", default=[]): [str],
        Optional("prefix", default=None): str,
        Optional("parsing_header", default=""): str,
        Optional("exclude_classes", default=[]): [str],
    }
)

global_schema = Schema(
    {
        "name": str,
        "input_folder": str,
        "output_folder": str,
        "pats": [str],
        "modules": [str],
        Optional("exclude", default=[]): [str],
        Optional("exceptions", default=[]): [str],
        Optional("additional_files", default=[]): [str],
        Optional("template_path", default=None): str,
        Optional("exclude_namespaces", default=[]): [str],
        "module_mapping": str,
        "Operators": {str: [str]},
        "Extras": {
            Optional("include_pre", default=None): str,
            Optional("include_post", default=None): str,
        },
        Optional("byref_types", default=[]): [str],
        Optional("byref_types_smart_ptr", default=[]): [str],
        Optional("parsing_header", default=""): str,
        Optional("Linux", default=None): platform_settings,
        Optional("Windows", default=None): platform_settings,
        Optional("OSX", default=None): platform_settings,
        Optional("FreeBSD", default=None): platform_settings,
        Optional("Attributes", default={}): {str: str},
        Optional("Modules", default=None): {str: module_schema},
    }
)
