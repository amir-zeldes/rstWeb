#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Basic logout page.
Author: Amir Zeldes
"""

import cgi
import os
from modules.logintools import logout
from modules.configobj import ConfigObj
from modules.pathutils import *

theform = cgi.FieldStorage()
scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
userdir = scriptpath + "users" + os.sep
config = ConfigObj(userdir + 'config.ini')

print(logout(userdir)) # printing cookie header. important!
print("Content-Type: text/html\n\n\n") # blank line: end of headers

templatedir = scriptpath + config['controltemplates'].replace("/",os.sep)
template = "main_header.html"
header = readfile(templatedir+template)
header = header.replace("**page_title**","Logged out")
header = header.replace('Logged in as: **user** (<a href="logout.py">log out</a>)',"")
header = header.replace("**open_disabled**",'')
header = header.replace("**user**",'(none)')
header = header.replace("**logout_control**",'')
print(header)

logout_footer = '''
<div id="control">
<p>You are now logged out</p>
<p><a href="open.py">Return to rstWeb</a></p>
		</div>

</body>
</html>
'''

print(logout_footer)
