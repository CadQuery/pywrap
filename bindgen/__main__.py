import click
import logzero
import pickle

from types import SimpleNamespace
from path import Path

from . import read_settings, run, parse_modules, transform_modules, render, validate_result


@click.group()
@click.option('-n','--njobs', default=-2,type=int)
@click.option('-v','--verbose',is_flag=True)
@click.option('-c','--clean',is_flag=True)
@click.pass_context
def main(ctx,clean,verbose,njobs):
    
    if not verbose:
        logzero.logger.setLevel(logzero.logging.INFO)
    
    ctx.obj = SimpleNamespace(verbose=verbose,njobs=njobs,clean=clean)

@main.command()
@click.argument('configuration')
@click.argument('output')
@click.pass_obj
def parse(obj,configuration,output):
    
    settings,module_mapping,module_settings = read_settings(configuration)
    result = parse_modules(obj.verbose,obj.njobs,settings,module_mapping,module_settings)
    
    with open(output,'wb') as f:
        pickle.dump(result,f)
        
@main.command()
@click.argument('configuration')
@click.argument('input')
@click.argument('output')
@click.pass_obj
def transform(obj,configuration,input,output):
    
    with open(input,'rb') as f:
        modules = pickle.load(f)
    
    settings,module_mapping,module_settings = read_settings(configuration)
    modules,class_dict,enum_dict = transform_modules(obj.verbose,obj.njobs,settings,module_mapping,module_settings,modules)
    
    with open(output,'wb') as f:
        pickle.dump((modules,class_dict,enum_dict),f)


@main.command()
@click.argument('configuration')
@click.argument('input')
@click.pass_obj
def generate(obj,configuration,input):
    
    settings,module_mapping,module_settings = read_settings(configuration)
    out = Path(settings['output_folder'])
    
    if obj.clean:
        out.rmtree_p()
    
    with open(input,'rb') as f:
        modules,class_dict,enum_dict = pickle.load(f)
        
    render(settings,module_settings,modules,class_dict)
    
    pre = settings['Extras']['include_pre']
    post = settings['Extras']['include_pre']
    
    if pre: Path(pre).copy(out)
    if post: Path(post).copy(out)

@main.command()
@click.argument('folder')
@click.pass_obj
def validate(obj,folder):
    
    validate_result(obj.verbose,obj.njobs,folder)
      

@main.command()
@click.argument('configuration')
@click.pass_obj
def all(obj,configuration):
    
    settings,module_mapping,modules = read_settings(configuration)
    logzero.logger.setLevel(logzero.logging.INFO)
    run(settings,module_mapping,modules)
    

if __name__ == '__main__':
    
    main()
    
    