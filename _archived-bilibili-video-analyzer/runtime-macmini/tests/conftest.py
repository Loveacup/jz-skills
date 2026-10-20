# -*- coding: utf-8 -*-
"""pytest 共享配置：把 scripts/ 加入 import path，便于直接 import 被测模块。"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
