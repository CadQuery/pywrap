import click
import logzero
import pickle

from path import Path

from . import read_settings, run, parse_modules, render
from .header import parse_tu


@click.group()
@click.option('-v','--verbose',is_flag=True)
@click.pass_context
def main(ctx,verbose):
    
    if not verbose:
        logzero.logger.setLevel(logzero.logging.INFO)
    
    ctx.obj = verbose

@main.command()
@click.argument('configuration')
@click.argument('output')
def parse(configuration,output):
    
    settings,module_mapping,modules = read_settings(configuration)
    result = parse_modules(settings,module_mapping,modules)
    
    with open(output,'wb') as f:
        pickle.dump(result,f)


@main.command()
@click.argument('configuration')
@click.argument('input')
def generate(configuration,input):
    
    settings,module_mapping,modules = read_settings(configuration)
    
    with open(input,'rb') as f:
        parsing_result = pickle.load(f)
        
    render(settings,parsing_result)

@main.command()
@click.argument('folder')
@click.pass_obj
def validate(verbose,folder):
    
    p = Path(folder)
    
    for f in p.files('*.cpp'):
        tu = parse_tu(f)
        if len([d for d in tu.diagnostics if d.severity >2]):
            logzero.logger.error('Validation {}: NOK'.format(f))
            if verbose:
                for d in tu.diagnostics:
                    logzero.logger.warning(d)
        else:
            logzero.logger.info('Validation {}: OK'.format(f))
        
        

@main.command()
@click.argument('configuration')
def all(configuration):
    
    settings,module_mapping,modules = read_settings(configuration)
    logzero.logger.setLevel(logzero.logging.INFO)
    run(settings,module_mapping,modules)
    

if __name__ == '__main__':
    
    main()
    
    