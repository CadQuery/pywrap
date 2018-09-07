import click
import logzero
import pickle

from . import read_settings, run, parse_modules, render


@click.group()
@click.option('-v','--verbose',is_flag=True)
def main(verbose):
    
    if not verbose:
        logzero.logger.setLevel(logzero.logging.INFO)

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
@click.argument('configuration')
def all(configuration):
    
    settings,module_mapping,modules = read_settings(configuration)
    logzero.logger.setLevel(logzero.logging.INFO)
    run(settings,module_mapping,modules)
    

if __name__ == '__main__':
    
    main()
    
    