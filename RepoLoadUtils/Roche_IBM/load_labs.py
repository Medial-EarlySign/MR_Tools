from Configuration import Configuration
import os, sys
from datetime import datetime
import pandas as pd
from load_data import *

cfg=Configuration()
load_labs(cfg, 1)
