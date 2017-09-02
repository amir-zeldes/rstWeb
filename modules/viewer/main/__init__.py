# -*- coding: UTF-8 -*-
import os

from rstviewer import main, rstweb_classes, rstweb_reader, rstweb_sql
from rstviewer.main import embed_rs3_image, rs3tohtml, rs3topng

SOURCE_ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
PACKAGE_ROOT_DIR = os.path.abspath(os.path.join(SOURCE_ROOT_DIR, '..'))
