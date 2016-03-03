"""Configure the python path to provide access to the biases package."""
import sys
from os.path import dirname, realpath, sep, pardir
    
sys.path.append(sep.join([dirname(realpath(__file__)), pardir, 'src-python']))
