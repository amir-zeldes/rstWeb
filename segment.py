#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Interface to segment a document into elementary discourse units (EDUs). These are the basis for
the EDU nodes in the structurer script's layout. Dynamic editing of the segments is handled
by script/segment.js, and once saved this script updates the database and renders the saved
segmentation.
Author: Amir Zeldes
"""

import _version
import cgitb
from modules.rstweb_sql import *
import codecs
import sys
import re
from modules.configobj import ConfigObj
from modules.pathutils import *
import cgi
import os
from modules.logintools import login
import datetime

def segment_main(user, admin, mode, **kwargs):

	cpout = ""
	theform = kwargs

	scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
	userdir = scriptpath + "users" + os.sep

	UTF8Writer = codecs.getwriter('utf8')
	sys.stdout = UTF8Writer(sys.stdout)

	cgitb.enable()

	config = ConfigObj(userdir + 'config.ini')
	templatedir = scriptpath + config['controltemplates'].replace("/",os.sep)
	template = "main_header.html"
	header = readfile(templatedir+template)
	header = header.replace("**page_title**","Segmentation editor")
	header = header.replace("**user**",user)
	header = header.replace("**open_disabled**",'')

	if admin == "0":
		header = header.replace("**admin_disabled**",'disabled="disabled"')
	else:
		header = header.replace("**admin_disabled**",'')

	cpout = ""
	if mode == "server":
		cpout += "Content-Type: text/html\n\n\n"
		header = header.replace("**logout_control**",'(<a href="logout.py">log out</a>)')
	else:
		header = header.replace("**logout_control**",'')
	cpout += header


	if "current_doc" in theform:
		current_doc = theform["current_doc"]
		current_project = theform["current_project"]
		current_guidelines = get_guidelines_url(current_project)
	else:
		current_doc = ""
		current_project = ""
		current_guidelines = ""


	edit_bar = "edit_bar.html"
	edit_bar = readfile(templatedir+edit_bar)
	edit_bar = edit_bar.replace("**doc**",current_doc)
	edit_bar = edit_bar.replace("**project**",current_project)
	edit_bar = edit_bar.replace("**structure_disabled**",'')
	edit_bar = edit_bar.replace("**quickexp_disabled**",'')
	edit_bar = edit_bar.replace("**screenshot_disabled**",'disabled="disabled"')
	edit_bar = edit_bar.replace("**save_disabled**",'')
	edit_bar = edit_bar.replace("**reset_disabled**",'')
	edit_bar = edit_bar.replace("**segment_disabled**",'disabled="disabled"')
	edit_bar = edit_bar.replace("**submit_target**",'segment.py')
	edit_bar = edit_bar.replace("**action_type**",'seg_action')
	edit_bar = edit_bar.replace("**current_guidelines**",current_guidelines)
	edit_bar = edit_bar.replace("**serve_mode**",mode)
	edit_bar = edit_bar.replace("**open_disabled**",'')
	edit_bar = edit_bar.replace('id="nav_segment" class="nav_button"','id="nav_segment" class="nav_button nav_button_inset"')

	if admin == "0":
		edit_bar = edit_bar.replace("**admin_disabled**",'disabled="disabled"')
	else:
		edit_bar = edit_bar.replace("**admin_disabled**",'')

	cpout += edit_bar

	help = "help.html"
	help = readfile(templatedir+help)
	help_match = re.search(r'(<div.*?help_seg.*?</div>)',help,re.MULTILINE|re.DOTALL)
	help = help_match.group(1)
	cpout += help

	about = "about.html"
	about = readfile(templatedir+about)
	about = about.replace("**version**", _version.__version__)
	cpout += about

	if current_doc =="":
		cpout += '<p class="warn">No file found - please select a file to open</p>'
		return cpout

	cpout += '<input id="undo_log" type="hidden" value=""/>'
	cpout += '<input id="redo_log" type="hidden" value=""/>'
	cpout += '<input id="undo_state" type="hidden" value=""/>'

	cpout += '''<div class="canvas">
	<div id="inner_canvas">'''

	# Remove floating non-terminal nodes if found
	# (e.g. due to browsing back and re-submitting old actions or other data corruption)
	clean_floating_nodes(current_doc, current_project, user)

	timestamp = ""
	if "timestamp" in theform:
		if len(theform["timestamp"]) > 1:
			timestamp = theform["timestamp"]

	refresh = check_refresh(user, timestamp)

	if "reset" in theform or user=="demo":
		if len(theform["reset"]) > 1 or user=="demo":
			reset_rst_doc(current_doc,current_project,user)

	if "logging" in theform and not refresh:
		if len(theform["logging"]) > 1:
			if get_setting("logging") == "on":
				logging = theform["logging"]
				if len(logging) > 0:
					update_log(current_doc,current_project,user,logging,"segment",str(datetime.datetime.now()))

	if "seg_action" in theform and not refresh:
		if len(theform["seg_action"]) > 1:
			action_log = theform["seg_action"]
			if len(action_log) > 0:
				actions = action_log.split(";")
				set_timestamp(user,timestamp)
				for action in actions:
					action_type = action.split(":")[0]
					action_params = action.split(":")[1]
					if action_type =="ins":
						insert_seg(int(action_params.replace("tok","")),current_doc,current_project,user)
					elif action_type =="del":
						merge_seg_forward(int(action_params.replace("tok","")),current_doc,current_project,user)

	segs={}


	rows = get_rst_doc(current_doc,current_project,user)

	if current_guidelines != "":
		cpout += '<script>enable_guidelines();</script>'

	cpout += '\t<script src="script/segment.js"></script>'
	cpout += '<h2>Edit segmentation</h2>'
	cpout += '**warning**'
	cpout += '\t<div id="control">'
	cpout += '\t<p>Document: <b>'+current_doc+'</b> (project: <i>'+current_project+'</i>)</p>'
	cpout += '\t<div id="segment_canvas">'

	for row in rows:
		if row[5] == "edu":
			segs[int(row[0])] = SEGMENT(row[0],row[6])

	seg_counter = 0
	tok_counter = 0

	segs = collections.OrderedDict(sorted(segs.items()))
	del_token_to_seg = {}
	first_seg = True
	for seg_id in segs:
		first_tok = True
		seg = segs[seg_id]
		seg_counter += 1
		if first_seg:
			first_seg = False
		else:
			cpout += '<div class="tok_space" id="tok'+str(tok_counter)+'" style="display:none" onclick="act('+"'ins:"+'tok'+str(tok_counter)+"'"+')">&nbsp;</div>'
			cpout += '\t\t\t<div id="segend_post_tok'+str(tok_counter)+'" class="seg_end" onclick="act('+"'del:"+'tok'+str(tok_counter)+"'"+')">||</div>'
			del_token_to_seg[tok_counter] = seg_counter
			cpout += '\t\t</div>'
		cpout += '\t\t<div id="seg'+ str(seg_counter) + '" class="seg">'
		for token in seg.tokens:
			tok_counter+=1
			if first_tok:
				first_tok = False
			else:
				cpout += '<div class="tok_space" id="tok'+str(tok_counter-1)+'" onclick="act('+"'ins:"+'tok'+str(tok_counter-1)+"'"+')">&nbsp;</div>'
			cpout += '\t\t\t<div class="token" id="string_tok'+str(tok_counter)+'">' + token + '</div>'
	cpout += '\t\t</div>'
	cpout += '''\t</div></div>
	</body>
	</html>

	'''

	tok_seg_map = get_tok_map(current_doc,current_project,user)
	incorrect_segs = [token_key for token_key in del_token_to_seg if int(tok_seg_map[token_key])+1 != del_token_to_seg[token_key]]
	warning = ''
	if len(incorrect_segs) > 0:
		warning = '<p class="warn">Attention! Empty segments detected - markup may be broken! Please contact your administrator.</p>'

	cpout = cpout.replace("**warning**",warning)

	if mode != "server":
		cpout = cpout.replace(".py","")
	return cpout


# Main script when running from Apache
def segment_main_server():
	thisscript = os.environ.get('SCRIPT_NAME', '')
	action = None
	theform = cgi.FieldStorage()
	scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
	userdir = scriptpath + "users" + os.sep
	action, userconfig = login(theform, userdir, thisscript, action)
	user = userconfig["username"]
	admin = userconfig["admin"]
	kwargs={}
	for key in theform:
		kwargs[key] = theform[key].value
	print(segment_main(user, admin, 'server', **kwargs))


scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
userdir = scriptpath + "users" + os.sep
config = ConfigObj(userdir + 'config.ini')
if "/" in os.environ.get('SCRIPT_NAME', ''):
	mode = "server"
else:
	mode = "local"

if mode == "server":
	segment_main_server()
