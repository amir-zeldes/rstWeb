#!/usr/bin/python
# -*- coding: utf-8 -*-

import cgitb
import sys
import os
from modules.configobj import ConfigObj
from modules.pathutils import *

cgitb.enable()


def quick_main(mode='local'):
    scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
    userdir = scriptpath + "users" + os.sep

    config = ConfigObj(userdir + 'config.ini')
    templatedir = scriptpath + config['controltemplates'].replace("/", os.sep)

    template = "quick.html"
    output = readfile(templatedir + template)
    if mode == "server":
        output = "Content-Type: text/html\n\n\n" + output
    output = output.replace("**page_title**", "Quick edit")
    output = output.replace("**serve_mode**", mode)
    if mode != "server":
        output = output.replace(".py", "")

    return output


def quick_main_server():
    output = quick_main(mode="server")
    if sys.version_info[0] < 3:
        print(output)
    else:
        sys.stdout.buffer.write(output.encode("utf8"))


if "/" in os.environ.get('SCRIPT_NAME', ''):
    mode = "server"
else:
    mode = "local"

if mode == "server":
    quick_main_server()

