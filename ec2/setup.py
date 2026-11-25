"""Everything a notebook needs:  from ec2.setup import *"""
import math

import matplotlib.pyplot as plt
import numpy as np
from IPython.display import Markdown, display

from . import columns as C
from . import design as D
from . import foundations as F
from . import plots as P
from . import project as PJ
from . import slabs as SL
from .analysis import UDL, UVL, ContinuousBeam, DeterminateBeam, Moment, Point, Span, joint_moments
from .codes import DEFL_K, EN, PSI, UK
from .project import BRIEF
from .report import Sheet, convert, mdm_table, num, photo, table
