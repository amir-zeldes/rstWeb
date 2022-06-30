function get_rs3(){
	reltypes = list_rels().split(",");
	rels = [];
	edus = [];
	groups = [];
	
	let nodes = parse_data();
	nids = Object.keys(nodes);
	nids.sort(function(a,b){
		return parseInt(nodes[a].id.replace("n","")) - parseInt(nodes[b].id.replace("n",""));
	}
	);
	
	for (nid of nids){
		node = nodes[nid];
		if (node.relname.length > 0){
			relname_string = node.relname.replace(/_[rm]/g,'');
		}
		else{
			relname_string = "";
		}
		if (node.parent == "n0"){
			parent_string = ""
			relname_string = ""
		}
		else{
			parent_string = 'parent="'+node.parent.replace('n','')+'" ';
		}
		if (relname_string.length > 0){
			relname_string = 'relname="' + relname_string+'"';
		}
		if (node.kind == "edu"){
			contents = $("#edu" + nid.replace("n","")).find("span.tok").map(function(){return $(this).text();}).get().join(' ');
			// Handle XML escapes
			contents = contents.replace(/&([^ ;]*) /,'&amp;$1 ');
			contents = contents.replace(/&$/,'&amp;');
			contents = contents.replace(/>/,'&gt;').replace(/</,'&lt;');
			contents = contents.replace(">","&gt;").replace("<","&lt;");
			edus.push('\t\t<segment id="'+nid.replace("n","")+'" '+ parent_string + relname_string+'>'+contents+'</segment>');
		}
		else {
			groups.push('\t\t<group id="'+nid.replace("n","")+'" type="'+node.kind+'" ' + parent_string + relname_string+'/>');
		}
	}
		for (rel of reltypes.sort()){
			if (rel=="span" || rel=="none"){continue;}
			relname_string = rel.replace(/_[rm]/,'');
			if (rel.endsWith("_m")){
				reltype = "multinuc";
			}
			else{
				reltype = "rst";
			}
			rels.push('\t\t\t<rel name="' + relname_string + '" type="' + reltype + '"/>');
		}

	rst_out = '<rst>\n\t<header>\n\t\t<relations>\n';
	rst_out += rels.join("\n") + "\n";
	rst_out += "\t\t</relations>\n\t</header>\n\t<body>\n";
	rst_out += edus.join("\n") + "\n";
	rst_out += groups.join("\n") + "\n";
	rst_out += "\t</body>\n</rst>\n";
	return rst_out;
}



$(document).ready(function() {
	
	var get_structure = 'get_structure';
	if (document.getElementById("serve_mode").value == 'server') {get_structure += ".py";}
	if ($("#import_dialog").length == 0){  // quit if not in quick mode
		return true;
	}
	
	// Create quick paste dialog
	$(function () {
		$("#import_dialog").dialog({
			autoOpen: false,
			resizable: true,
			width: "80%",
			height: 400,
			modal: true,
			buttons: {
				"Close": function () {
					// if textarea is not empty do something with the value and close the modal
					if ($(this).find('textarea').val().length) {
						if ($(this).find('textarea').val().includes("<segment")){
							rs3 = $(this).find('textarea').val();
							$.post(get_structure, {
							data: rs3},
								function(newData){
										$("#quick_structure").html(newData);
								}
							);
						}
						$(this).dialog("close");
					}
					$(this).dialog("close");
				}
			}
		});
	});

	// Create export dialog
	$(function () {
		$("#export_dialog").dialog({
			autoOpen: false,
			resizable: true,
			width: "80%",
			height: 440,
			modal: true,
			buttons: {
				"Close": function () {
					$(this).dialog("close");
				}
			},
			open: function( event, ui ) {
				data = get_rs3();
				$(this).find('textarea').val(data);
			}
		});
	});
});

function toggle_ui(){
	if ($(".minibtn").css("display")=="inline-block"){ //switch off
		$(".minibtn").css("display","none");
		$(".rst_rel").css("-webkit-appearance","none");
		$(".rst_rel").css("-moz-appearance","none");
		$(".rst_rel").css("width","100px");
		$(".rst_rel").css("border","0px");
	}else{ //switch on
		$(".minibtn").css("display","inline-block");
		$(".rst_rel").css("-webkit-appearance","initial");
		$(".rst_rel").css("-moz-appearance","initial");
		$(".rst_rel").css("width","70px");
		$(".rst_rel").css("border","");
	}
}