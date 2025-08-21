#!/usr/bin/env python
import platform
if not(platform.python_version().startswith('3')):
    raise NameError('Please use python3 and not python %s'%(platform.python_version()))