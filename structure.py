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
import _version
from modules.configobj import ConfigObj
from modules.pathutils import *
from modules.logintools import login

thisscript = os.environ.get('SCRIPT_NAME', '')
action = None
scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
userdir = scriptpath + "users" + os.sep
theform = cgi.FieldStorage()
action, userconfig = login(theform, userdir, thisscript, action)
user = userconfig["username"]

UTF8Writer = codecs.getwriter('utf8')
sys.stdout = UTF8Writer(sys.stdout)

cgitb.enable()

###GRAPHICAL PARAMETERS###
top_spacing = 20
layer_spacing = 60

config = ConfigObj(userdir + 'config.ini')
importdir = config['importdir']
templatedir = scriptpath + config['controltemplates'].replace("/",os.sep)

template = "main_header.html"
header = readfile(templatedir+template)
header = header.replace("**page_title**","Structure editor")
header = header.replace("**user**",user)


print "Content-Type: text/html\n\n\n"
print header

if "current_doc" in theform:
	current_doc = theform["current_doc"].value
	current_project = theform["current_project"].value
else:
	current_doc = ""
	current_project = ""

edit_bar = "edit_bar.html"
edit_bar = readfile(templatedir+edit_bar)
edit_bar = edit_bar.replace("**doc**",current_doc)
edit_bar = edit_bar.replace("**project**",current_project)
edit_bar = edit_bar.replace("**structure_disabled**",'disabled="disabled"')
edit_bar = edit_bar.replace("**segment_disabled**",'')
edit_bar = edit_bar.replace("**relations_disabled**",'')
edit_bar = edit_bar.replace("**submit_target**",'structure.py')
edit_bar = edit_bar.replace("**action_type**",'action')
edit_bar = edit_bar.replace("**open_disabled**",'')
edit_bar = edit_bar.replace('id="nav_edit" class="nav_button"','id="nav_edit" class="nav_button nav_button_inset"')

if userconfig["admin"] == "3":
	edit_bar = edit_bar.replace("**admin_disabled**",'')
else:
	edit_bar = edit_bar.replace("**admin_disabled**",'disabled="disabled"')

print edit_bar

help = "help.html"
help = readfile(templatedir+help)
help_match = re.search(r'(<div id="help_edit".*?</div>)',help,re.MULTILINE|re.DOTALL)
help = help_match.group(1)
print help.decode("utf-8")

about = "about.html"
about = readfile(templatedir+about)
about = about.replace("**version**", _version.__version__)
print about

print '<script src="./script/structure.js"></script>'

if current_doc =="":
	print '<p class="warn">No file found - please select a file to open</p>'
	sys.exit()


print '''<div class="canvas">'''
print '\t<p>Document: <b>'+current_doc+'</b> (project: <i>'+current_project+'</i>)</p>'
print '''<div id="inner_canvas">'''

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


if "action" in theform:
	if len(theform.getvalue("action")) > 1:
		action_log = theform["action"].value
		if len(action_log) > 0:
			actions = action_log.split(";")
			for action in actions:
				action_type = action.split(":")[0]
				action_params = action.split(":")[1]
				params = action_params.split(",")
				if action_type =="up":
					update_parent(params[0],params[1],current_doc,current_project,user)
				elif action_type =="sp":
					insert_parent(params[0],"span","span",current_doc,current_project,user)
				elif action_type =="mn":
					insert_parent(params[0],def_multirel,"multinuc",current_doc,current_project,user)
				elif action_type =="rl":
					update_rel(params[0],params[1],current_doc,current_project,user)
				else:
					print '<script>alert("the action was: " + theform["action"].value);</script>'

if "reset" in theform or user=="demo":
	if len(theform.getvalue("reset")) > 1 or user=="demo":
		reset_rst_doc(current_doc,current_project,user)

nodes={}
rows = get_rst_doc(current_doc,current_project,user)
for row in rows:
	if row[7] in rel_kinds:
		relkind = rel_kinds[row[7]]
	else:
		relkind = "span"
	if row[5] =="edu":
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

for key in nodes:
	node = nodes[key]
	if node.kind!="edu":
		g_wid = str(int((node.right- node.left+1) *100 -4 ))
		print '<div id="lg'+ node.id +'" class="group" style="left: ' +str(int(node.left*100 - 100))+ '; width: ' + g_wid + '; top:'+ str(int(top_spacing + layer_spacing+node.depth*layer_spacing)) +'px; z-index:1"><div id="wsk'+node.id+'" class="whisker" style="width:'+g_wid+';"></div></div>'
		print '<div id="g'+ node.id +'" class="num_cont" style="position: absolute; left:' + pix_anchors[node.id] +'px; top:'+ str(int(4+ top_spacing + layer_spacing+node.depth*layer_spacing))+'px; z-index:'+str(int(200-(node.right-node.left)))+'"><table class="btn_tb"><tr><td rowspan="2"><button id="unlink_'+ node.id+'"  title="unlink this node" class="minibtn" onclick="act('+"'up:"+node.id+",0'"+');">X</button></td><td rowspan="2"><span class="num_id">'+str(int(node.left))+"-"+str(int(node.right))+'</span></td><td><button id="aspan_'+ node.id+'" title="add span above" class="minibtn" onclick="act('+"'sp:"+node.id+"'"+');">T</button></td></tr><tr><td><button id="amulti_'+ node.id+'" title="add multinuc above" class="minibtn" onclick="act('+"'mn:"+node.id+"'"+');">' + "Λ".decode("utf-8") + '</button></td></tr></table></div><br/>'

	elif node.kind=="edu":
		print '<div id="edu'+str(node.id)+'" class="edu" title="'+str(node.id)+'" style="left:'+str(int(node.id)*100 - 100) +'; top:'+str(int(top_spacing +layer_spacing+node.depth*layer_spacing))+'; width: 96px">'
		print '<div id="wsk'+node.id+'" class="whisker" style="width:96px;"></div><div class="edu_num_cont"><table class="btn_tb"><tr><td rowspan="2"><button id="unlink_'+ node.id+'" title="unlink this node" class="minibtn" onclick="act('+"'up:"+node.id+",0'"+');">X</button></td><td rowspan="2"><span class="num_id">&nbsp;'+str(int(node.left))+'&nbsp;</span></td><td><button id="aspan_'+ node.id+'" title="add span above" class="minibtn" onclick="act('+"'sp:"+node.id+"'"+');">T</button></td></tr><tr><td><button id="amulti_'+ node.id+'" title="add multinuc above" class="minibtn" onclick="act('+"'mn:"+node.id+"'"+');">' + "Λ".decode("utf-8") + '</button></td></tr></table></div>'+node.text+'</div>'

max_right = get_max_right(current_doc,current_project,user)

# Serialize data in hidden input for JavaScript
print '<input id="data" name="data" type="hidden" '
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
print 'value="' + hidden_val + '"/>'

print '<input id="def_multi_rel" type="hidden" value="' + get_def_rel("multinuc",current_doc,current_project) +'"/>'
print '<input id="def_rst_rel" type="hidden" value="' + get_def_rel("rst",current_doc,current_project) +'"/>'
print '<input id="undo_log" type="hidden" value=""/>'
print '<input id="redo_log" type="hidden" value=""/>'
print '<input id="undo_state" type="hidden" value=""/>'

print '''	<script src="./script/jquery.jsPlumb-1.7.5-min.js"></script>

		<script>
		'''

print 'function select_my_rel(options,my_rel){'
print 'var multi_options = "' + multi_options +'";'
print 'var rst_options = "' + rst_options +'";'
print 'if (options =="multi"){options = multi_options;} else {options=rst_options;}'
print '		return options.replace("<option value='+"'" +'"' + '+my_rel+'+'"' +"'"+'","<option selected='+"'"+'selected'+"'"+' value='+"'" +'"'+ '+my_rel+'+'"' +"'"+'");'
print '			}\n'
print '''function make_relchooser(id,option_type,rel){
    return $("<select class='rst_rel' id='sel"+id.replace("n","")+"' onchange='crel(" + id.replace("n","") + ",this.options[this.selectedIndex].value);'>" + select_my_rel(option_type,rel) + "</select>");
}'''
print '''
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

print "jsPlumb.setSuspendDrawing(true);"


for key in nodes:
	node = nodes[key]
	if node.kind == "edu":
		node_id_str = "edu" + node.id
	else:
		node_id_str = "g" + node.id
	print 'jsPlumb.makeSource("'+node_id_str+'", {anchor: "Top", filter: ".num_id", allowLoopback:false});'
	print 'jsPlumb.makeTarget("'+node_id_str+'", {anchor: "Top", filter: ".num_id", allowLoopback:false});'


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
			print 'jsPlumb.connect({source:"'+node_id_str+'",target:"'+parent_id_str+ '", connector:"Straight", anchors: ["Top","Bottom"]});'
		elif parent.kind == "multinuc" and node.relkind=="multinuc":
			print 'jsPlumb.connect({source:"'+node_id_str+'",target:"'+parent_id_str+ '", connector:"Straight", anchors: ["Top","Bottom"], overlays: [ ["Custom", {create:function(component) {return make_relchooser("'+node.id+'","multi","'+node.relname+'");},location:0.2,id:"customOverlay"}]]});'
		else:
			print 'jsPlumb.connect({source:"'+node_id_str+'",target:"'+parent_id_str+'", overlays: [ ["Arrow" , { width:12, length:12, location:0.95 }],["Custom", {create:function(component) {return make_relchooser("'+node.id+'","rst","'+node.relname+'");},location:0.1,id:"customOverlay"}]]});'


print '''

	jsPlumb.setSuspendDrawing(false,true);


	jsPlumb.bind("connection", function(info) {
	   source = info.sourceId.replace(/edu|g/,"")
	   target = info.targetId.replace(/edu|g/g,"")
	});

	jsPlumb.bind("beforeDrop", function(info) {
	    $(".minibtn").prop("disabled",true);

'''

print '''
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