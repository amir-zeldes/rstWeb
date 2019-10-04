#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Administration functions and interface to create and delete users, import and export documents,
assign documents to users and set up projects
Author: Amir Zeldes
"""

import cgitb
import cgi
import errno
from os.path import isfile, join
from os import listdir
import _version
from modules.logintools import login, createuser
from modules.rstweb_sql import *
from modules.configobj import ConfigObj
from modules.pathutils import *

try:
	basestring
except NameError:
	basestring = str


def admin_main(user, admin, mode, **kwargs):

	scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
	userdir = scriptpath + "users" + os.sep
	config = ConfigObj(userdir + 'config.ini')
	exportdir = scriptpath + config['exportdir'].replace("/",os.sep)

	theform = kwargs
	cgitb.enable()

	import re
	def is_email(email):
		pattern = '[\.\w]{1,}[@]\w+[.]\w+'
		if re.match(pattern, email):
			return True
		else:
			return False

	config = ConfigObj(userdir + 'config.ini')
	templatedir = scriptpath + config['controltemplates'].replace("/",os.sep)
	template = "main_header.html"
	header = readfile(templatedir+template)
	header = header.replace("**page_title**","Administration")
	header = header.replace("**user**",user)

	importdir = scriptpath + config['importdir'].replace("/",os.sep)
	def_relfile = scriptpath + config['default_rels'].replace("/",os.sep)

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
	else:
		current_doc = ""
		current_project = ""

	edit_bar = "edit_bar.html"
	edit_bar = readfile(templatedir+edit_bar)
	edit_bar = edit_bar.replace("**doc**",current_doc)
	edit_bar = edit_bar.replace("**project**",current_project)
	edit_bar = edit_bar.replace("**structure_disabled**",'')
	edit_bar = edit_bar.replace("**segment_disabled**",'')
	edit_bar = edit_bar.replace("**relations_disabled**",'')
	edit_bar = edit_bar.replace("**submit_target**",'admin.py')
	edit_bar = edit_bar.replace("**action_type**",'')
	edit_bar = edit_bar.replace("**serve_mode**",mode)
	edit_bar = edit_bar.replace("**open_disabled**",'')
	edit_bar = edit_bar.replace("**reset_disabled**",'disabled="disabled"')
	edit_bar = edit_bar.replace("**quickexp_disabled**",'disabled="disabled"')
	edit_bar = edit_bar.replace("**screenshot_disabled**",'disabled="disabled"')
	edit_bar = edit_bar.replace("**save_disabled**",'disabled="disabled"')
	edit_bar = edit_bar.replace("**undo_disabled**",'disabled="disabled"')
	edit_bar = edit_bar.replace("**redo_disabled**",'disabled="disabled"')
	edit_bar = edit_bar.replace("**admin_disabled**",'disabled="disabled"')
	edit_bar = edit_bar.replace('id="nav_admin" class="nav_button"','id="nav_admin" class="nav_button nav_button_inset"')


	if admin == "0":
		cpout += '<p class="warn">User '+ user+' does not have administrator rights!</p></body></html>'
		return cpout
	else:
		edit_bar = edit_bar.replace("**admin_disabled**",'')

	cpout += edit_bar

	help = "help.html"
	help = readfile(templatedir+help)
	help_match = re.search(r'(<div id="help_admin".*?</div>)',help,re.MULTILINE|re.DOTALL)
	help = help_match.group(1)
	cpout += help

	about = "about.html"
	about = readfile(templatedir+about)
	about = about.replace("**version**", _version.__version__)
	cpout += about

	if "wipe" in theform:
		if theform["wipe"] =="wipe":
			setup_db()

	if "create_project" in theform:
		new_project = theform["create_project"]
		if len(new_project)>0:
			create_project(new_project)

	if "doclist" in theform:
		current_doc = theform["doclist"]
	else:
		current_doc = ""

	cpout += '''
	<div id="control">
	<form id="admin_form" name="id_form" action="admin.py" method="post" enctype="multipart/form-data">
		<input type="hidden" name="create_project" id="create_project" value=""/>
		<input type="hidden" name="sel_tab" id="sel_tab" value="project"/>
		<input type="hidden" name="delete" id="delete" value=""/>
		<input type="hidden" name="delete_user" id="delete_user" value=""/>
		<input type="hidden" name="export" id="export" value=""/>
		<input type="hidden" name="wipe" id="wipe" value=""/>
		<input type="hidden" name="switch_signals" id="switch_signals" value=""/>
		<input type="hidden" name="signals_file" id="signals_file" value=""/>
		<input type="hidden" name="switch_logging" id="switch_logging" value=""/>
		<input type="hidden" name="switch_span_buttons" id="switch_span_buttons" value=""/>
		<input type="hidden" name="switch_multinuc_buttons" id="switch_multinuc_buttons" value=""/>
		<input type="hidden" name="update_schema" id="update_schema" value=""/>
		<input type="hidden" name="imp_project" id="imp_project" value=""/>
		<input type="hidden" name="import_file_type" id="import_file_type" value=""/>
		<input type="hidden" name="do_tokenize" id="do_tokenize" value=""/>
		<input type="hidden" name="doclist" id="doclist" value="'''
	cpout += current_doc
	cpout += '''"/>
		<input type="hidden" name="userlist" id="userlist" value=""/>
		<input type="hidden" name="assign_doc" id="assign_doc" value=""/>
		<input type="hidden" name="assign_user" id="assign_user" value=""/>
		<input type="hidden" name="unassign_doc" id="unassign_doc" value=""/>
		<input type="hidden" name="unassign_user" id="unassign_user" value=""/>
		<input type="hidden" name="new_user_data" id="new_user_data" value=""/>
		<input type="hidden" name="edit_validation" id="edit_validation" value=""/>
		<input type="hidden" name="del_project" id="del_project" value=""/>
		<input type="hidden" name="guidelines_url" id="guidelines_url" value=""/>
		<input id="file" type="file" name="file" multiple="multiple"/>
	</form>
	<script src="./script/admin.js"></script>
	<script src="./script/jquery-1.11.3.min.js"></script>
	<script src="./script/jquery-ui.min.js"></script>
	'''


	cpout += '''
	<div class="tab_btn" id="project_btn" onclick="open_tab('project');">Projects</div><div id="project" class="tab">
	<h2>Manage Projects</h2>
	<p>Create a new project named: <input id="new_project"/></p>
	<button onclick="admin('create_project')">Create Project</button>
	'''
	#cpout += theform

	if "update_schema" in theform:
		if theform["update_schema"] == "update_schema":
			update_schema()

	if "del_project" in theform:
		projects_to_delete = theform["del_project"].split(";")
		if len(projects_to_delete)>0:
			if isinstance(projects_to_delete,list):
				for project in projects_to_delete:
					delete_project(project)
			else:
				delete_project(projects_to_delete)

	all_project_list = get_all_projects()

	url_message = ""
	if "guidelines_url" in theform:
		if "::" in theform["guidelines_url"]:
			project_list, guideline_url = theform["guidelines_url"].split("::")
			if len(project_list)>0:
				schema = get_schema()
				if schema < 2:
					update_schema()
				if isinstance(project_list,list):
					for project in project_list:
						set_guidelines_url(project,guideline_url)
				else:
					set_guidelines_url(project_list,guideline_url)
				url_message = '<p class="warn">Added the URL ' + guideline_url + " to the selected projects</p>"


	cpout += '<p>Existing projects:</p>'
	if all_project_list:
		cpout += '<select class="doclist" id="project_select" size="5" multiple="multiple">\n'
		for project in all_project_list:
			cpout += '\t<option value="' + project[0] +'">' +  project[0] + "</option>"
		cpout += '</select>\n'
	else:
		cpout += '<p class="warn">No projects found!</p>'

	cpout += '''<p>
		<p>Add guidelines URL to selected project:</p><p><input id="guidelines_url_input"/></p>
		<button onclick="admin('guidelines_url')">Add URL</button>
		''' + url_message

	cpout += '''

		<p>Delete selected projects:</p>

		<button onclick="admin('delete_project')">Delete Selected</button></p>
	'''


	# Handle validation settings
	validation_message = ""
	val_project = ""
	if "edit_validation" in theform:
		if "::" in theform["edit_validation"]:
			val_project, validations = theform["edit_validation"].split("::")
			schema = get_schema()
			if schema < 5:
				update_schema()
			set_project_validations(val_project,validations)
			validation_message = '<p class="warn">Updated validation settings for project ' + val_project

	cpout += '''<p>Change annotation warning settings for project:</p>'''

	if all_project_list:
		cpout += '''<select class="doclist" id="validate_project_select" onchange="toggle_validation_project();">\n'''
		if val_project == "":
			val_project = all_project_list[0][0]
		for project in all_project_list:
			if project[0] == val_project:
				sel_string = ' selected="selected"'
			else:
				sel_string = ""
			cpout += '\t<option value="' + project[0] + '"' + sel_string +'>' +  project[0] + "</option>\n"
		cpout += '</select>\n'
		for project in all_project_list:
			vals = get_project_validations(project[0])
			cpout += '\t<input id="validations_' + project[0] +'" type="hidden" value="'+vals+'">'
	else:
		cpout += "<p>No projects found with permissions for user: "+ user + "</p>"

	validations = get_project_validations(val_project)
	validation_list = validations.split(";")
	checked = ""
	if "validate_empty" in validation_list:
		checked = " checked"

	cpout += '''<br><br><label class="switch">
	  <input type="checkbox" id="check_empty_span" onclick="admin('toggle_validations');"'''+ checked +'''>
	  <div class="slider round"></div>
		</label><div style="position: relative; top: -3px; left: 3px; display: inline-block">Warn on empty span
		<a class="tooltip" href="">
   <i class="fa fa-question-circle">&nbsp;</i>
   <span><img src="img/empty_span.png" height="100px">

    <i>Highlights spans with single span child</i>
   </span>
</a></div>
		'''
	checked = ""
	if "validate_flat" in validation_list:
		checked = " checked"
	cpout += '''<br><label class="switch">
	  <input type="checkbox" id="check_flat_rst" onclick="admin('toggle_validations');"'''+ checked +'''>
	  <div class="slider round"></div>
		</label><div style="margin-top: 10px; position: relative; top: -3px; left: 3px; display: inline-block">Warn on multiple incoming flat RST relations
		<a class="tooltip" href="">
   <i class="fa fa-question-circle">&nbsp;</i>
   <span><img src="img/flat_rst.png" height="75px">

    <i>Highlights spans with multiple incoming satellites</i>
   </span>
</a></div>
'''
	checked = ""
	if "validate_mononuc" in validation_list:
		checked = " checked"
	cpout += '''<br><label class="switch">
		  <input type="checkbox" id="check_mononuc" onclick="admin('toggle_validations');"''' + checked + '''>
		  <div class="slider round"></div>
			</label><div style="margin-top: 10px; position: relative; top: -3px; left: 3px; display: inline-block">Warn on multinucs with single child
			<a class="tooltip" href="">
	   <i class="fa fa-question-circle">&nbsp;</i>
	   <span><img src="img/mononuc.png" height="75px">

	    <i>Highlights multinucs with a single child</i>
	   </span>
	</a></div>
		<script>
			selproj = document.getElementById("validate_project_select").value;
			validations = document.getElementById("validations_" + selproj).value;
			if (validations.indexOf("validate_flat")>0){
				document.getElementById("check_flat_rst").checked = true;
			}
			if (validations.indexOf("validate_empty")>0){
				document.getElementById("check_empty_span").checked = true;
			}
			if (validations.indexOf("validate_mononuc")>0){
				document.getElementById("check_mononuc").checked = true;
			}
		</script>'''
	cpout += validation_message

	cpout += '''
		</div>'''


	cpout += '''
	<div class="tab_btn" id="import_btn" onclick="open_tab('import');">Import</div><div id="import" class="tab">
	<h2>Import a Document</h2>
	<p>1. Upload .rs3 or plain text file(s): </p>
	<p>2. Choose file type: <select id="import_file_type_select" class="doclist"><option value="rs3">rs3</option><option value="plain">plain text (EDU per line)</option></select> </p>
	<p>3. Tokenize words automatically? <input type="checkbox" name="tokenize" id="tokenize"></p>
	<p>4. Import document(s) into this project:
	'''


	if all_project_list:
		cpout += '<select class="doclist" id="imp_project_select">\n'
		if isinstance(all_project_list,list):
			for project in all_project_list:
				cpout += '\t<option value="' + project[0] +'">' +  project[0] + "</option>"
		else:
			cpout += '\t<option value="' + all_project_list +'">' +  all_project_list + "</option>"
		cpout += '</select>\n'
	else:
		cpout += "<p>No projects found with permissions for user: "+ user + "</p>"
	cpout += '''
	</p>
	<p><button onclick="admin('upload')">Upload</button></p>

	'''

	fail = 0
	if "file" in theform and "imp_project" in theform:
		fileitem = theform['file']
		imp_project = theform["imp_project"]
		do_tokenize = theform["do_tokenize"] == "tokenize"
		if isinstance(fileitem,list):
			message = ""
			for filelist_item in fileitem:
				if filelist_item.filename and len(imp_project) > 0: # Test if the file was uploaded and a project selection exists
					#  strip leading path from file name to avoid directory traversal attacks
					fn = os.path.basename(filelist_item.filename)
					open(importdir + fn, 'wb').write(filelist_item.file.read())
					message += 'The file "' + fn + '" was uploaded successfully<br/>'
					if theform['import_file_type'] == "rs3":
						fail = import_document(importdir + fn,imp_project,user,do_tokenize=do_tokenize)
					elif theform['import_file_type'] == "plain":
						if len(def_relfile) > 0:
							rel_hash = read_relfile(def_relfile)
						else:
							rel_hash = {}
						fail = import_plaintext(importdir + fn,imp_project,user,rel_hash,do_tokenize=do_tokenize)
				else:
					message = 'No file was uploaded'
		else:
			if fileitem.filename and len(imp_project) > 0: # Test if the file was uploaded and a project selection exists
				#  strip leading path from file name to avoid directory traversal attacks
				fn = os.path.basename(fileitem.filename)
				open(importdir + fn, 'wb').write(fileitem.file.read())
				message = 'The file "' + fn + '" was uploaded successfully'
				if theform['import_file_type'] == "rs3":
					fail = import_document(importdir + fn,imp_project,user,do_tokenize=do_tokenize)
				elif theform['import_file_type'] == "plain":
					if len(def_relfile) > 0:
						rel_hash = read_relfile(def_relfile)
					else:
						rel_hash = {}
					fail = import_plaintext(importdir + fn,imp_project,user,rel_hash,do_tokenize=do_tokenize)
			else:
				message = 'No file was uploaded'

		if isinstance(fail,basestring):
			message = fail
		cpout += """
		<p class="warn">%s</p>
		""" % (message,)

	cpout += '</div><div class="tab_btn" id="docs_btn" onclick="open_tab('+"'"+"docs"+"'"+');">Documents</div><div id="docs" class="tab">'
	cpout += "<h2>Current Documents</h2>"

	if "delete" in theform: #execute delete documents before retrieving doclist
		doclist = theform["doclist"]
		if len(doclist) > 0 and theform["delete"] =="delete":
			docs_to_delete = doclist.split(";")

			if len(docs_to_delete) > 0:
				if isinstance(docs_to_delete,list):
					for doc in docs_to_delete:
						delete_document(doc.split("/")[1],doc.split("/")[0])
				else:
					delete_document(docs_to_delete.split("/")[1],docs_to_delete.split("/")[0])
				cpout += '<p class="warn">Deletion complete</p>'


	cpout += '<p>List of documents in the database:</p>'
	docs = get_all_docs_by_project()
	if not docs:
		cpout += "<p>No documents found with permissions for user name: " + user + "</p>"
	else:
		cpout += '<select name="doclist_select" id="doclist_select" class="doclist" size="15" multiple="multiple">\n'
		project_group=""
		for doc in docs:
			if project_group!=doc[1]:
				if project_group !="":
					cpout += '</optgroup>\n'
				project_group = doc[1]
				cpout += '<optgroup label="'+doc[1]+'">\n'
			cpout += '\t<option value="'+doc[1]+"/"+doc[0]+'">'+doc[0]+'</option>\n'

		cpout += '</optgroup>\n</select>\n'

	cpout += '''
	<p>Export selected document(s) to export folder as .rs3 file(s):</p>
	<button onclick="admin('export');">Export</button>
	<p>Delete selected document(s):</p>
	<button onclick="admin('delete_doc');">Delete</button>
	'''
	if "export" in theform:
		export_doc_list = theform["doclist"]
		if len(export_doc_list) > 0 and theform["export"]== "export":
			export_docs = export_doc_list.split(";")
			if isinstance(export_docs,list):
				for doc in export_docs:
					export_document(doc.split("/")[1],doc.split("/")[0],exportdir)
			else:
				export_document(export_docs.split("/")[1],export_docs.split("/")[0],exportdir)
			cpout += '<p class="warn">Export complete</p>'


	# Handle user add and delete before showing user list
	if "delete_user" in theform:
		if len(theform["delete_user"]) > 0:
			users_to_delete = theform["userlist"]
			users = users_to_delete.split(";")
			if isinstance(users,list):
				for user in users:
					try:
						os.remove(userdir+user)
						delete_docs_for_user(user)
						user_del_message = '<p class="warn">Deleted users from selection</p>'
					except OSError as e:
						if e.errno == errno.ENOENT:
							user_del_message = '<p class="warn">File to delete <i>'+user+'</i> not found!</p>'
						else:
							raise
			else:
				try:
					os.remove(userdir+users_to_delete)
					delete_docs_for_user(users_to_delete)
					user_del_message = 'Deleted users from selection'
				except OSError as e:
					if e.errno == errno.ENOENT:
						user_del_message = '<p class="warn">File to delete <i>'+ users_to_delete + '</i> not found!</p>'
					else:
						raise


	# Handle user document assignment
	if "assign_user" in theform:
		if len(theform["assign_user"]) > 0:
			users_to_assign = theform["assign_user"]
			docs_to_assign = theform["assign_doc"]
			users = users_to_assign.split(";") if ";" in users_to_assign else [users_to_assign]
			docs = docs_to_assign.split(";") if ";" in docs_to_assign else [docs_to_assign]
			for user in users:
				for doc in docs:
					user = user.replace(".ini","")
					copy_doc_to_user(doc.split("/")[1],doc.split("/")[0],user)

	if "unassign_user" in theform:
		if len(theform["unassign_user"]) > 0:
			user_to_unassign = theform["unassign_user"]
			doc_to_unassign = theform["unassign_doc"]
			delete_doc_user_version(doc_to_unassign.split("/")[1],doc_to_unassign.split("/")[0],user_to_unassign)

	if "new_user_data" in theform:
		if len(theform["new_user_data"]) >0:
			user_data = theform["new_user_data"].split("/")
			username = user_data[0]
			realname = user_data[1]
			email = user_data[2]
			RESERVEDNAMES = {'config':1, 'default':1, 'temp':1, 'emails':1, 'pending':1, '_orig':1}
			if username in RESERVEDNAMES:
				user_create_message = '<p class="warn">User name cannot be: "config", "default", "temp", "emails", or "pending"</p>'
			else:
				if len(realname)<1:
					user_create_message = '<p class="warn">The real name cannot be empty!</p>'
				else:
					if not is_email(email):
						user_create_message = '<p class="warn">Invalid e-mail address: <b>'+email+'</b></p>'
					else:
						password = user_data[3]
						if len(password)<5:
							user_create_message = '<p class="warn">Password must be at least 5 characters long</p>'
						else:
							administrator = user_data[4]
							if str(administrator) != "3" and str(administrator) != "0":
								user_create_message = '<p class="warn">Invalid administrator setting value for new user</p>'
							else:
								createuser(userdir, realname, username, email, password, administrator)
								user_create_message = '<p class="warn">Created the user ' + username + '</p>'

	if mode=="server":
		cpout += '</div><div class="tab_btn" id="users_btn" onclick="open_tab('+"'"+"users"+"'"+');">Users</div><div id="users" class="tab">'
	else:
		cpout += '''</div><div class="tab_btn disabled_tab" id="users_btn" onclick="alert('User management disabled in local mode');">Users</div><div id="users" class="tab">'''
	cpout += '''<h2>User Management</h2>
	<table id="doc_assign"><tr><td><p>Users:</p>
	<select id="userlist_select" multiple="multiple" size="10" class="doclist">
	'''

	userfiles = [ f for f in listdir(userdir) if isfile(join(userdir,f)) ]
	for userfile in sorted(userfiles):
		if userfile != "config.ini" and userfile != "default.ini" and userfile != "admin.ini" and userfile.endswith(".ini"):
			userfile = userfile.replace(".ini","")
			cpout += '<option value="' + userfile + '.ini">'+userfile+'</option>'
	cpout += '''
	</select></td><td>
	<p>Documents to assign to:</p>'''
	docs = get_all_docs_by_project()
	if not docs:
		cpout += "<p class='warn'>No documents found with permissions for user name: " + user + "</p>"
	else:
		cpout += '<select name="doc_assign_select" id="doc_assign_select" class="doclist" size="10" multiple="multiple">\n'
		project_group=""
		for doc in docs:
			if project_group!=doc[1]:
				if project_group !="":
					cpout += '</optgroup>\n'
				project_group = doc[1]
				cpout += '<optgroup label="'+doc[1]+'">\n'
			cpout += '\t<option value="'+doc[1]+"/"+doc[0]+'">'+doc[0]+'</option>\n'

		cpout += '</optgroup>\n</select>\n'
	cpout += '''
	</td></tr></table>
	<p>Delete selected user files: (annotations will not be deleted)</p>
	<button onclick="admin('delete_user')">Delete user(s)</button>
	'''
	if "delete_user" in theform:
		if len(theform["delete_user"]) > 0:
			cpout += user_del_message
	cpout += '''
	<p>Assign selected users to selected documents:</p>
	<button onclick="admin('assign_user')">Assign</button>
	<p>Delete assignments for user: (annotations will be deleted)</p>
	'''

	assigned_users = get_assigned_users()
	if len(assigned_users)>0:
		cpout += '<select id="assigned_user_sel" name="assigned_user_sel" class="doclist" onchange="update_assignments()">'
		first_user = assigned_users[0][0]
		for user in assigned_users:
			assigned_docs = get_assignments(user[0])
			cpout += '<option value="' # + user[0] +":"
			for doc in assigned_docs:
				cpout += doc[1]+"/"+doc[0]+";"
			cpout += '">'+user[0]+'</option>'
		cpout += '</select>\n'
		assigned_docs = get_assignments(first_user)
		cpout += '<select id="assigned_doc_sel" name="assigned_doc_sel" class="doclist">'
		for doc in assigned_docs:
			cpout += '<option value="' + doc[1]+"/"+doc[0] + '">'+doc[1]+"/"+doc[0]+'</option>'
		cpout += '</select>'
		cpout += '''<p><button onclick="admin('unassign_user')">Delete assignment</button></p>'''
	else:
		cpout += '<p class="warn">No user assignments found</p>'



	cpout += '''<p>Create new user:</p>
	<table class="gray_tab">
	    <tr><td>User name:</td><td><input name="username" id="username"  type="text" value=""></td></tr>
	    <tr><td>Real name:</td><td><input name="realname" id="realname" type="text" value=""></td></tr>
	    <tr><td>Email address:</td><td><input name="email" id="email" type="text" value=""></td></tr>
	    <tr><td>Password:</td><td><input name="pass" id="pass" type="password">
	    <tr><td>Administrator:</td><td><input type="checkbox" id="chk_admin" name="chk_admin">&nbsp;&nbsp;&nbsp;&nbsp;<button onclick="admin('create_user')">Create user</button></td></tr>
	    </td></tr>
	</table>

	'''

	if "new_user_data" in theform:
		if len(theform["new_user_data"]) > 0:
			cpout += user_create_message

	### database
	cpout += '</div><div class="tab_btn" id="database_btn" onclick="open_tab('+"'"+"database"+"'"+');">Database</div><div id="database" class="tab">'

	# signals
	cpout += '''<h2>Signals</h2>
	<p>Turn signal display and editing signals on/off.</p>'''

	try:
		signals_state = get_setting("signals")
	except IndexError:
		signals_state="False"

	if "switch_signals" in theform:
		if theform["switch_signals"] == "switch_signals":

			if signals_state == "True":
				signals_state = "False"
			else:
				signals_state = "True"
			save_setting("signals",signals_state)

	if signals_state == "True":
		opposite_signals = "False"
	else:
		opposite_signals = "True"

	cpout += '''<button onclick="admin('switch_signals')">Turn ''' + ('on' if opposite_signals == "True" else 'off') +'''</button>'''

	if "signals_file" in theform and theform["signals_file"]:
		save_setting("signals_file", theform["signals_file"])

	cpout += '''<div>
	<br>
	<span>Signal types: </span>
	<select name="signals_file_select" id="signals_file_select" class="doclist"
	        onchange="admin('select_signals_file')">'''
	signals_files = [fname for fname in os.listdir('signals')
					 if fname.endswith('.json')]
	signals_file = get_setting("signals_file")
	for fname in signals_files:

		selected_string = (' selected="selected"'
						   if signals_file and signals_file == fname
						   else '')
		cpout += '<option value="' + fname + '"' + selected_string + '>' + fname[:-5] + '</option>'
	cpout += '''</select>
	</div>'''

	# logging
	cpout += '''<h2>Logging</h2>
	<p>Turn detailed action logging on/off.</p>'''

	try:
		logging_state = get_setting("logging")
	except IndexError:
		logging_state="off"

	if "switch_logging" in theform:
		if theform["switch_logging"] == "switch_logging":

			if logging_state == "on":
				logging_state = "off"
			else:
				logging_state = "on"
			save_setting("logging",logging_state)

	if logging_state == "on":
		opposite_logging = "off"
	else:
		opposite_logging = "on"

	cpout += '''<button onclick="admin('switch_logging')">Turn '''+ opposite_logging +'''</button>'''


	# spans/multinucs
	cpout += '''<h2>Disable spans or multinucs</h2>
	<p>Turn on/off add span and multinuc buttons (for non-RST annotation).</p>'''

	try:
		span_state = get_setting("use_span_buttons")
		multinuc_state = get_setting("use_multinuc_buttons")
	except IndexError:
		span_state="True"
		multinuc_state="True"

	if "switch_span_buttons" in theform:
		if int(get_schema()) < 3:
			update_schema()
		if theform["switch_span_buttons"] == "switch_span_buttons":
			if span_state == "True":
				span_state = "False"
			else:
				span_state = "True"
			save_setting("use_span_buttons",span_state)
	if span_state == "True":
		opposite_span = "Disable"
	else:
		opposite_span = "Enable"
	if "switch_multinuc_buttons" in theform:
		if int(get_schema()) < 3:
			update_schema()
		if theform["switch_multinuc_buttons"] == "switch_multinuc_buttons":
			if multinuc_state == "True":
				multinuc_state = "False"
			else:
				multinuc_state = "True"
			save_setting("use_multinuc_buttons",multinuc_state)
	if multinuc_state == "True":
		opposite_multinuc = "Disable"
	else:
		opposite_multinuc = "Enable"

	cpout += '''<button onclick="admin('switch_span_buttons')">'''+ opposite_span +''' span buttons</button><br/><br/>'''
	cpout += '''<button onclick="admin('switch_multinuc_buttons')">'''+ opposite_multinuc +''' multinuc buttons</button>'''

	cpout += '''<h2>Update schema</h2>
	<p>Update the schema without losing data between major schema upgrades.</p>'''

	cpout += '''<button onclick="admin('update_schema')">Update</button>'''

	cpout += '''<h2>Initialize the Database</h2>
	<p>Wipe and restore database structure.</p>
	<p class="warn">Warning:</p> <p>this will delete all imported documents and all edits from the database.</p>
	<button onclick="admin('wipe')">Init DB</button>
	'''

	if "wipe" in theform:
		if theform["wipe"] =="wipe":
			cpout += '<p class="warn">Database has been re-initialized</p>'


	cpout += '''
	</div>
	<script>
		open_tab(document.getElementById("sel_tab").value);
	</script>'''

	if "sel_tab" in theform:
		sel_tab = theform['sel_tab']
		cpout += '<script>open_tab("'+sel_tab+'")</script>'

	cpout += '''
	</div>
	</body>
	</html>
	'''

	if mode != "server":
		cpout = cpout.replace(".py","")
	return cpout

# Main script when running from Apache
def admin_main_server():
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
		if key == 'file':
			kwargs[key] = theform[key]
		else:
			kwargs[key] = theform[key].value
	print(admin_main(user, admin, 'server', **kwargs))


scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
userdir = scriptpath + "users" + os.sep
config = ConfigObj(userdir + 'config.ini')
if "/" in os.environ.get('SCRIPT_NAME', ''):
	mode = "server"
else:
	mode = "local"

if mode == "server":
	admin_main_server()
