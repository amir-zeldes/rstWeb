#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
The main interface for editing RST structures. Reads a document and sets up the initial layout of
HTML elements representing RST nodes and their connections (using calls to jsPlumb). Further
manipulations of the interface are managed by script/structure.js.
Author: Amir Zeldes
"""


import cgitb
from modules.rstweb_sql import *
import codecs
import sys
import cgi
import os
import datetime
import _version
from modules.configobj import ConfigObj
from modules.pathutils import *
from modules.logintools import login


def structure_main(user, admin, mode, **kwargs):

	scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
	userdir = scriptpath + "users" + os.sep
	theform = kwargs

	UTF8Writer = codecs.getwriter('utf8')
	sys.stdout = UTF8Writer(sys.stdout)

	cgitb.enable()

	###GRAPHICAL PARAMETERS###
	top_spacing = 20
	layer_spacing = 60

	config = ConfigObj(userdir + 'config.ini')
	templatedir = scriptpath + config['controltemplates'].replace("/",os.sep)

	template = "main_header.html"
	header = readfile(templatedir+template)
	header = header.replace("**page_title**","Structure editor")
	header = header.replace("**user**",user)

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
	edit_bar = edit_bar.replace("**structure_disabled**",'disabled="disabled"')
	edit_bar = edit_bar.replace("**segment_disabled**",'')
	edit_bar = edit_bar.replace("**relations_disabled**",'')
	edit_bar = edit_bar.replace("**current_guidelines**",current_guidelines)
	if mode == "server":
		edit_bar = edit_bar.replace("**submit_target**",'structure.py')
	else:
		edit_bar = edit_bar.replace("**submit_target**",'structure')
	edit_bar = edit_bar.replace("**action_type**",'action')
	edit_bar = edit_bar.replace("**serve_mode**",mode)
	edit_bar = edit_bar.replace("**open_disabled**",'')
	edit_bar = edit_bar.replace('id="nav_edit" class="nav_button"','id="nav_edit" class="nav_button nav_button_inset"')

	if admin == "3":
		edit_bar = edit_bar.replace("**admin_disabled**",'')
	else:
		edit_bar = edit_bar.replace("**admin_disabled**",'disabled="disabled"')

	cpout += edit_bar

	help = "help.html"
	help = readfile(templatedir+help)
	help_match = re.search(r'(<div id="help_edit".*?</div>)',help,re.MULTILINE|re.DOTALL)
	help = help_match.group(1)
	cpout += help.decode("utf-8")

	about = "about.html"
	about = readfile(templatedir+about)
	about = about.replace("**version**", _version.__version__)
	cpout += about

	if current_guidelines != "":
		cpout += '<script>enable_guidelines();</script>'
	cpout += '<script src="./script/structure.js"></script>'

	if current_doc =="":
		cpout += '<p class="warn">No file found - please select a file to open</p>'
		return cpout

	cpout += '''<div class="canvas">'''
	cpout += '\t<p>Document: <b>'+current_doc+'</b> (project: <i>'+current_project+'</i>)</p>'
	cpout += '''<div id="inner_canvas">'''

	rels = get_rst_rels(current_doc, current_project)
	def_multirel = get_def_rel("multinuc",current_doc, current_project)
	def_rstrel = get_def_rel("rst",current_doc, current_project)
	multi_options =""
	rst_options =""
	rel_kinds = {}
	for rel in rels:
		if rel[1]=="multinuc":
			multi_options += "<option value='"+rel[0]+"'>"+rel[0].replace("_m","")+'</option>'
			rel_kinds[rel[0]] = "multinuc"
		else:
			rst_options += "<option value='"+rel[0]+"'>"+rel[0].replace("_r","")+'</option>'
			rel_kinds[rel[0]] = "rst"
	multi_options += "<option value='"+def_rstrel+"'>(satellite...)</option>"

	# Remove floating non-terminal nodes if found
	# (e.g. due to browsing back and re-submitting old actions or other data corruption)
	clean_floating_nodes(current_doc, current_project, user)

	timestamp = ""
	if "timestamp" in theform:
		if len(theform["timestamp"]) > 1:
			timestamp = theform["timestamp"]

	refresh = check_refresh(user, timestamp)

	if "action" in theform and not refresh:
		if len(theform["action"]) > 1:
			action_log = theform["action"]
			if len(action_log) > 0:
				actions = action_log.split(";")
				set_timestamp(user,timestamp)
				for action in actions:
					action_type = action.split(":")[0]
					action_params = action.split(":")[1]
					params = action_params.split(",")
					if action_type == "up":
						update_parent(params[0],params[1],current_doc,current_project,user)
					elif action_type == "sp":
						insert_parent(params[0],"span","span",current_doc,current_project,user)
					elif action_type == "mn":
						insert_parent(params[0],def_multirel,"multinuc",current_doc,current_project,user)
					elif action_type == "rl":
						update_rel(params[0],params[1],current_doc,current_project,user)
					else:
						cpout += '<script>alert("the action was: " + theform["action"]);</script>'

	if "logging" in theform and not refresh:
		if len(theform["logging"]) > 1:
			if get_setting("logging") == "on":
				logging = theform["logging"]
				if len(logging) > 0:
					update_log(current_doc,current_project,user,logging,"structure",str(datetime.datetime.now()))

	if "reset" in theform or user == "demo":
		if len(theform["reset"]) > 1 or user == "demo":
			reset_rst_doc(current_doc,current_project,user)

	nodes={}
	rows = get_rst_doc(current_doc,current_project,user)
	for row in rows:
		if row[7] in rel_kinds:
			relkind = rel_kinds[row[7]]
		else:
			relkind = "span"
		if row[5] == "edu":
			nodes[row[0]] = NODE(row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],relkind)
		else:
			nodes[row[0]] = NODE(row[0],0,0,row[3],row[4],row[5],row[6],row[7],relkind)

	for key in nodes:
		node = nodes[key]
		get_depth(node,node,nodes)

	for key in nodes:
		if nodes[key].kind == "edu":
			get_left_right(key, nodes,0,0,rel_kinds)

	anchors = {}
	pix_anchors = {}

	# Calculate anchor points for nodes
	# First get proportional position for anchor
	for key in sorted(nodes, key = lambda id: nodes[id].depth, reverse=True):
		node = nodes[key]
		if node.kind=="edu":
			anchors[node.id]= "0.5"
		if node.parent!="0":
			parent = nodes[node.parent]
			parent_wid = (parent.right- parent.left+1) * 100 - 4
			child_wid = (node.right- node.left+1) * 100 - 4
			if node.relname == "span":
				if node.id in anchors:
					anchors[parent.id] = str(((node.left - parent.left)*100)/parent_wid+float(anchors[node.id])*float(child_wid/parent_wid))
				else:
					anchors[parent.id] = str(((node.left - parent.left)*100)/parent_wid+(0.5*child_wid)/parent_wid)
			elif node.relkind=="multinuc" and parent.kind =="multinuc":
				# For multinucs, the anchor is in the middle between leftmost and rightmost of the multinuc children
				# (not including other rst children)
				lr = get_multinuc_children_lr(node.parent,current_doc,current_project,user)
				lr_wid = (lr[0] + lr[1]) /2
				lr_ids = get_multinuc_children_lr_ids(node.parent,lr[0],lr[1],current_doc,current_project,user)
				left_child = lr_ids[0]
				right_child = lr_ids[1]
				if left_child == right_child:
					anchors[parent.id] = "0.5"
				else:
					if left_child in anchors and right_child in anchors: #both leftmost and rightmost multinuc children have been found
						len_left = nodes[left_child].right-nodes[left_child].left+1
						len_right = nodes[right_child].right-nodes[right_child].left+1
						anchors[parent.id] = str(((float(anchors[left_child]) * len_left*100 + float(anchors[right_child]) * len_right * 100 + (nodes[right_child].left - parent.left) * 100)/2)/parent_wid)
					else:
						anchors[parent.id] = str((lr_wid - parent.left+1) / (parent.right - parent.left+1))

			else:
				if not parent.id in anchors:
					anchors[parent.id] = "0.5"

	# Place anchor element to center on proportional position relative to parent
	for key in nodes:
		node = nodes[key]
		pix_anchors[node.id] = str(int(3+node.left * 100 -100 - 39 + float(anchors[node.id])*((node.right- node.left+1) * 100 - 4)))

	# Check that span and multinuc buttons should be used (if the interface is not used for RST, they may be disabled)
	if int(get_schema()) > 2:
		use_span_buttons = True if get_setting("use_span_buttons") == "True" else False
		use_multinuc_buttons = True if get_setting("use_multinuc_buttons") == "True" else False
	else:
		use_span_buttons = True
		use_multinuc_buttons = True

	for key in nodes:
		node = nodes[key]
		if node.kind != "edu":
			g_wid = str(int((node.right- node.left+1) *100 -4 ))
			cpout += '<div id="lg'+ node.id +'" class="group" style="left: ' +str(int(node.left*100 - 100))+ '; width: ' + g_wid + '; top:'+ str(int(top_spacing + layer_spacing+node.depth*layer_spacing)) +'px; z-index:1"><div id="wsk'+node.id+'" class="whisker" style="width:'+g_wid+';"></div></div>'
			cpout += '<div id="g'+ node.id +'" class="num_cont" style="position: absolute; left:' + pix_anchors[node.id] +'px; top:'+ str(int(4+ top_spacing + layer_spacing+node.depth*layer_spacing))+'px; z-index:'+str(int(200-(node.right-node.left)))+'"><table class="btn_tb"><tr><td rowspan="2"><button id="unlink_'+ node.id+'"  title="unlink this node" class="minibtn" onclick="act('+"'up:"+node.id+",0'"+');">X</button></td><td rowspan="2"><span class="num_id">'+str(int(node.left))+"-"+str(int(node.right))+'</span></td>'
			if use_span_buttons:
				cpout += '<td><button id="aspan_'+ node.id+'" title="add span above" class="minibtn" onclick="act('+"'sp:"+node.id+"'"+');">T</button></td>'
			cpout += '</tr>'
			if use_multinuc_buttons:
				cpout += '<tr><td><button id="amulti_'+ node.id+'" title="add multinuc above" class="minibtn" onclick="act('+"'mn:"+node.id+"'"+');">' + "Λ".decode("utf-8") + '</button></td></tr>'
			cpout += '</table></div><br/>'

		elif node.kind=="edu":
			cpout += '<div id="edu'+str(node.id)+'" class="edu" title="'+str(node.id)+'" style="left:'+str(int(node.id)*100 - 100) +'; top:'+str(int(top_spacing +layer_spacing+node.depth*layer_spacing))+'; width: 96px">'
			cpout += '<div id="wsk'+node.id+'" class="whisker" style="width:96px;"></div><div class="edu_num_cont"><table class="btn_tb"><tr><td rowspan="2"><button id="unlink_'+ node.id+'" title="unlink this node" class="minibtn" onclick="act('+"'up:"+node.id+",0'"+');">X</button></td><td rowspan="2"><span class="num_id">&nbsp;'+str(int(node.left))+'&nbsp;</span></td>'
			if use_span_buttons:
				cpout += '<td><button id="aspan_'+ node.id+'" title="add span above" class="minibtn" onclick="act('+"'sp:"+node.id+"'"+');">T</button></td>'
			cpout += '</tr>'
			if use_multinuc_buttons:
				cpout += '<tr><td><button id="amulti_'+ node.id+'" title="add multinuc above" class="minibtn" onclick="act('+"'mn:"+node.id+"'"+');">' + "Λ".decode("utf-8") + '</button></td></tr>'
			cpout += '</table></div>'+node.text+'</div>'


	max_right = get_max_right(current_doc,current_project,user)

	# Serialize data in hidden input for JavaScript
	cpout += '<input id="data" name="data" type="hidden" '
	hidden_val=""
	for key in nodes:
		node = nodes[key]
		if node.relname:
			safe_relname = node.relname
		else:
			safe_relname = "none"
		if node.kind =="edu":
			hidden_val += "n" + node.id +",n" +node.parent+",e,"+ str(int(node.left)) + "," + safe_relname + "," + get_rel_type(node.relname,current_doc,current_project) + ";"
		elif node.kind =="span":
			hidden_val += "n" + node.id +",n" +node.parent+",s,0," + safe_relname + "," + get_rel_type(node.relname,current_doc,current_project) + ";"
		else:
			hidden_val += "n"+node.id +",n" +node.parent+",m,0," + safe_relname + "," + get_rel_type(node.relname,current_doc,current_project) + ";"
	hidden_val = hidden_val[0:len(hidden_val)-1]
	cpout += 'value="' + hidden_val + '"/>'


	cpout += '<input id="def_multi_rel" type="hidden" value="' + get_def_rel("multinuc",current_doc,current_project) +'"/>'
	cpout += '<input id="def_rst_rel" type="hidden" value="' + get_def_rel("rst",current_doc,current_project) +'"/>'
	cpout += '<input id="undo_log" type="hidden" value=""/>'
	cpout += '<input id="redo_log" type="hidden" value=""/>'
	cpout += '<input id="undo_state" type="hidden" value=""/>'
	cpout += '<input id="logging" type="hidden" value=""/>'
	cpout += '<input id="use_span_buttons" type="hidden" value="'+str(use_span_buttons)+'"/>'
	cpout += '<input id="use_multinuc_buttons" type="hidden" value="'+str(use_multinuc_buttons)+'"/>'

	cpout += '''	<script src="./script/jquery.jsPlumb-1.7.5-min.js"></script>

			<script>
			'''

	cpout += 'function select_my_rel(options,my_rel){'
	cpout += 'var multi_options = "' + multi_options +'";'
	cpout += 'var rst_options = "' + rst_options +'";'
	cpout += 'if (options =="multi"){options = multi_options;} else {options=rst_options;}'
	cpout += '		return options.replace("<option value='+"'" +'"' + '+my_rel+'+'"' +"'"+'","<option selected='+"'"+'selected'+"'"+' value='+"'" +'"'+ '+my_rel+'+'"' +"'"+'");'
	cpout += '			}\n'
	cpout += '''function make_relchooser(id,option_type,rel){
	    return $("<select class='rst_rel' id='sel"+id.replace("n","")+"' onchange='crel(" + id.replace("n","") + ",this.options[this.selectedIndex].value);'>" + select_my_rel(option_type,rel) + "</select>");
	}'''
	cpout += '''
			jsPlumb.importDefaults({
			PaintStyle : {
				lineWidth:2,
				strokeStyle: 'rgba(0,0,0,0.5)'
			},
			Endpoints : [ [ "Dot", { radius:1 } ], [ "Dot", { radius:1 } ] ],
			  EndpointStyles : [{ fillStyle:"#000000" }, { fillStyle:"#000000" }],
			  Anchor:"Top",
	            Connector : [ "Bezier", { curviness:50 } ]
			})
			 jsPlumb.ready(function() {

	jsPlumb.setContainer(document.getElementById("inner_canvas"));
	'''

	cpout += "jsPlumb.setSuspendDrawing(true);"


	for key in nodes:
		node = nodes[key]
		if node.kind == "edu":
			node_id_str = "edu" + node.id
		else:
			node_id_str = "g" + node.id
		cpout += 'jsPlumb.makeSource("'+node_id_str+'", {anchor: "Top", filter: ".num_id", allowLoopback:false});'
		cpout += 'jsPlumb.makeTarget("'+node_id_str+'", {anchor: "Top", filter: ".num_id", allowLoopback:false});'


	# Connect nodes
	for key in nodes:
		node = nodes[key]
		if node.parent!="0":
			parent = nodes[node.parent]
			if node.kind == "edu":
				node_id_str = "edu" + node.id
			else:
				node_id_str = "g" + node.id
			if parent.kind == "edu":
				parent_id_str = "edu" + parent.id
			else:
				parent_id_str = "g" + parent.id

			if node.relname == "span":
				cpout += 'jsPlumb.connect({source:"'+node_id_str+'",target:"'+parent_id_str+ '", connector:"Straight", anchors: ["Top","Bottom"]});'
			elif parent.kind == "multinuc" and node.relkind=="multinuc":
				cpout += 'jsPlumb.connect({source:"'+node_id_str+'",target:"'+parent_id_str+ '", connector:"Straight", anchors: ["Top","Bottom"], overlays: [ ["Custom", {create:function(component) {return make_relchooser("'+node.id+'","multi","'+node.relname+'");},location:0.2,id:"customOverlay"}]]});'
			else:
				cpout += 'jsPlumb.connect({source:"'+node_id_str+'",target:"'+parent_id_str+'", overlays: [ ["Arrow" , { width:12, length:12, location:0.95 }],["Custom", {create:function(component) {return make_relchooser("'+node.id+'","rst","'+node.relname+'");},location:0.1,id:"customOverlay"}]]});'


	cpout += '''

		jsPlumb.setSuspendDrawing(false,true);


		jsPlumb.bind("connection", function(info) {
		   source = info.sourceId.replace(/edu|g/,"")
		   target = info.targetId.replace(/edu|g/g,"")
		});

		jsPlumb.bind("beforeDrop", function(info) {
		    $(".minibtn").prop("disabled",true);

	'''

	cpout += '''
			var node_id = "n"+info.sourceId.replace(/edu|g|lg/,"");
			var new_parent_id = "n"+info.targetId.replace(/edu|g|lg/,"");

			nodes = parse_data();
			new_parent = nodes[new_parent_id];
			relname = nodes[node_id].relname;
			new_parent_kind = new_parent.kind;
			if (nodes[node_id].parent != "n0"){
				old_parent_kind = nodes[nodes[node_id].parent].kind;
			}
			else
			{
				old_parent_kind ="none";
			}

			if (info.sourceId != info.targetId){
				if (!(is_ancestor(new_parent_id,node_id))){
					jsPlumb.select({source:info.sourceId}).detach();
					if (new_parent_kind == "multinuc"){
						relname = get_multirel(new_parent_id,node_id,nodes);
						jsPlumb.connect({source:info.sourceId, target:info.targetId, connector:"Straight", anchors: ["Top","Bottom"], overlays: [ ["Custom", {create:function(component) {return make_relchooser(node_id,"multi",relname);},location:0.2,id:"customOverlay"}]]});
					}
					else{
						jsPlumb.connect({source:info.sourceId, target:info.targetId, overlays: [ ["Arrow" , { width:12, length:12, location:0.95 }],["Custom", {create:function(component) {return make_relchooser(node_id,"rst",relname);},location:0.1,id:"customOverlay"}]]});
					}
					new_rel = document.getElementById("sel"+ node_id.replace("n","")).value;
				    act('up:' + node_id.replace("n","") + ',' + new_parent_id.replace("n",""));
					update_rel(node_id,new_rel,nodes);
					recalculate_depth(parse_data());
				}
			}

		    $(".minibtn").prop("disabled",false);

		});

	});

			</script>
			</div>
			</div>
			<div id="anim_catch" class="anim_catch">&nbsp;</div>
	</body>
	</html>

	'''
	if mode != "server":
		cpout = cpout.replace(".py","")
	return cpout

# Main script when running from Apache
def structure_main_server():
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
	print structure_main(user, admin, 'server', **kwargs)


scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
userdir = scriptpath + "users" + os.sep
config = ConfigObj(userdir + 'config.ini')
if "/" in os.environ.get('SCRIPT_NAME', ''):
	mode = "server"
else:
	mode = "local"

if mode == "server":
	structure_main_server()