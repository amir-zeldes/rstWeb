/**
 * Basic functions for the navigation toolbar, used by all top level Python
 * scripts, including undo and redo for the structurer and segmenter.
 * Author: Amir Zeldes
*/


function save(){
    disable_buttons();
    $("#nav_save").addClass("nav_button_inset");
    document.getElementById("timestamp").value = Date();
    document.getElementById("edit_form").submit();

}

function open_segment(){
    if (document.getElementById("dirty").value=="dirty"){
        var r = confirm("You have unsaved work - really leave this page without saving?");
        if (r == false) {
            return;
        }
    }
    document.getElementById("edit_form").action="segment";
    if(document.getElementById("serve_mode").value=="server"){document.getElementById("edit_form").action="segment.py";}
    document.getElementById("edit_form").submit();
}

function open_structure(){
    if (document.getElementById("dirty").value=="dirty"){
        var r = confirm("You have unsaved work - really leave this page without saving?");
        if (r == false) {
            return;
        }
    }
    document.getElementById("edit_form").action="structure";
    if(document.getElementById("serve_mode").value=="server"){document.getElementById("edit_form").action="structure.py";}
    document.getElementById("edit_form").submit();
}

function open_open(){
    if (document.getElementById("dirty").value=="dirty"){
        var r = confirm("You have unsaved work - really leave this page without saving?");
        if (r == false) {
            return;
        }
    }
    if(document.getElementById("serve_mode").value=="server"){
		document.getElementById("edit_form").action="open.py";
	}
	else{
		document.getElementById("edit_form").action="open";	
	}
    document.getElementById("edit_form").submit();
}

function open_admin(){
    if (document.getElementById("dirty").value=="dirty"){
        var r = confirm("You have unsaved work - really leave this page without saving?");
        if (r == false) {
            return;
        }
    }
    document.getElementById("edit_form").action="admin";
    if(document.getElementById("serve_mode").value=="server"){document.getElementById("edit_form").action="admin.py";}
    document.getElementById("edit_form").submit();
}

function show_help(){
    if( $(".help")[0].style.display!="block"){
        $(".help")[0].style.display="block";
        $('body, .tab_btn, .tab, .tab button, .doclist, ._jsPlumb_overlay, #segment_canvas, .minibtn, .num_id, .nav_button').toggleClass("blackout");
        $('.tab_btn, .tab, .tab button, .doclist, ._jsPlumb_overlay, #segment_canvas, .minibtn, .num_id, .nav_button').toggleClass("no_events");
    }
    else {
        hide_help();
    }

}

function hide_help(){
    $(".help")[0].style.display="none";
    $('body, .tab_btn, .tab, .tab button, .doclist, ._jsPlumb_overlay, #segment_canvas, .minibtn, .num_id, .nav_button').toggleClass("blackout");
    $('.tab_btn, .tab, .tab button, .doclist, ._jsPlumb_overlay, #segment_canvas, .minibtn, .num_id, .nav_button').toggleClass("no_events");
}

function show_about(){
    if( $(".about")[0].style.display!="block"){
        $(".about")[0].style.display="block";
        $('body, .tab_btn, .tab, .tab button, .doclist, ._jsPlumb_overlay, #segment_canvas, .minibtn, .num_id, .nav_button').toggleClass("blackout");
        $('.tab_btn, .tab, .tab button, .doclist, ._jsPlumb_overlay, #segment_canvas, .minibtn, .num_id, .nav_button').toggleClass("no_events");
    }
    else {
        hide_about();
    }

}

function hide_about(){
    $(".about")[0].style.display="none";
    $('body, .tab_btn, .tab, .tab button, .doclist, ._jsPlumb_overlay, #segment_canvas, .minibtn, .num_id, .nav_button').toggleClass("blackout");
    $('.tab_btn, .tab, .tab button, .doclist, ._jsPlumb_overlay, #segment_canvas, .minibtn, .num_id, .nav_button').toggleClass("no_events");
}


function do_reset(){
    var r = confirm("Really reset this document? All of your annotations will be deleted and the original imported state of this file will be restored!");
    if (r == false) {
        return;
    }
    disable_buttons();
    $("#nav_reset").addClass("nav_button_inset");
    document.getElementById('reset').value='reset';
    document.getElementById('logging').value += 'reset;';
    document.getElementById('edit_form').submit()
}

function do_open(project_doc){
    if (project_doc =="") {alert("No document has been selected!");return;}
    document.getElementById('current_project').value = project_doc.split('/')[0];
    document.getElementById('current_doc').value = project_doc.split('/')[1];
    document.getElementById('edit_form').submit();
}


function do_quickexp(){
    if (document.getElementById("dirty").value=="dirty"){
        var r = confirm("You have unsaved work - really export without saved work? Changes will be omitted.");
        if (r == false) {
            return;
        }
    }
    document.getElementById("quickexp_form").action="quick_export";
    if(document.getElementById("serve_mode").value=="server"){document.getElementById("quickexp_form").action="quick_export.py";}
    document.getElementById("quickexp_form").submit();
}

function do_screenshot(){
    // create a deep copy of the canvas (the root html element of the rst tree)
    // so that we can change and discard it once we're done without affecting
    // the real html elements
    var canvasDivCopy = $("#canvas").clone();
    var offscreenDiv = $('<div></div>');
    offscreenDiv.append(canvasDivCopy);
    offscreenDiv.insertAfter($("#canvas"));

    // need to replace svg elements with canvas elements or else they won't show up in html2canvas
    // https://github.com/niklasvh/html2canvas/issues/1179
    var elements = canvasDivCopy.find('svg').map(function() {
        var svg = $(this);
        var canvas = $('<canvas></canvas>').css({position: 'absolute', left:svg.css('left'), top: svg.css('top')});

        svg.replaceWith(canvas);

        // Get the raw SVG string and curate it
        var content = svg.wrap('<p></p>').parent().html();
        svg.unwrap();

        canvg(canvas[0], content);

        return {
            svg: svg,
            canvas: canvas
        };
    });

    // remove ui elements that we don't want in the picture
    canvasDivCopy.find("#document_name").remove();
    canvasDivCopy.find("#show-all-signals").remove();
    canvasDivCopy.find(".minibtn").remove();
    canvasDivCopy.find(".rst_rel").replaceWith(function(i, htmlStr) {
        var select = $(htmlStr);
        var text = select.filter('option:selected').text();
        return '<div class="select_replacement">' + text + '</div>';
    });

    // workaround for html2canvas bug
    canvasDivCopy.find(".tok").css("font-size", "9pt");

    // since the contents of #inner_canvas are positioned absolutely, it does not
    // scale its width and height automatically to the content. we have to
    // detect this rather crudely: for the width we find the left offsets of
    // EDU's, and for height we use toks
    var width = 100;
    var canvasDivLeftOffset = canvasDivCopy.offset().left;
    canvasDivCopy.find(".edu").each(function() {
        var div = $(this);
        // 16 gives some padding on the right
        var divWidth = (div.offset().left - canvasDivLeftOffset) + div.outerWidth() + 16;
        if (divWidth > width) {
            width = divWidth;
        }
    });

    var height = 100;
    var canvasDivTopOffset = canvasDivCopy.offset().top;
    canvasDivCopy.find(".tok").each(function() {
        var tok = $(this);
        // 100 is an arbitrarily chosen number that worked when toks were highlighted and
        // when they were not highlighted. 
        var tokHeight = (tok.offset().top - canvasDivTopOffset) + tok.outerHeight() + 100;
        if (tokHeight > height) {
            height = tokHeight;
        }
    });

    html2canvas(canvasDivCopy[0], {height: height, width: width, scale: 2})
    .then(function(canvas){
        elements.each(function() {
            canvas.replaceWith(this.svg);
        });

        var url = canvas.toDataURL("image/png");

        // use anchor to download it
        var a = document.createElement('a');
        var filename = document.getElementById('current_doc').value.replace(".rs3","");
        a.setAttribute('href', url);
        a.setAttribute('download', filename + ".png");
        $(a).insertAfter($("#canvas"));
        a.click();

        $(a).remove();
        offscreenDiv.remove();
    });
}

function undo(){

    //document.getElementById("undo_log").value = reorder_undo_log(document.getElementById("undo_log").value);
    if (document.getElementById("undo_log").value =="") {alert("Nothing to undo!");return;}
    document.getElementById("undo_state").value = "undo";
    actions = pop_undo();
    action_array = actions.split("+")
    action_array = action_array.reverse();
    for (action in action_array){
        act(action_array[action]);
    }
    pop_action();
    //recalculate_depth();
    document.getElementById("undo_state").value = "";

}

function pop_undo(){

    undo_log = document.getElementById("undo_log").value;
    myRegexp = /([^;]+);$/g;
    last_action = myRegexp.exec(undo_log);
    document.getElementById("undo_log").value = undo_log.replace(/[^;]+;$/,"");
    if (document.getElementById("undo_log").value==""){
            document.getElementById("dirty").value = "";
    }
    return last_action[1];
}

function append_undo(undo_action){

    // each undo click should correspond to a series of actions ending in a semicolon
    if (document.getElementById("undo_state").value!="undo"){ //only append undo actions if we are not during an undo state
        if (undo_action.length >0){
            if (undo_action.startsWith("+")){//plus appended plus actions should be inserted before the semi-colon
                document.getElementById("undo_log").value = document.getElementById("undo_log").value.replace(/;$/,"");
            }
            document.getElementById("undo_log").value += undo_action;
            if (!(undo_action.endsWith("+"))){ //prepended plus actions should not receive a semicolon
                document.getElementById("undo_log").value += ";";
            }
        }
    }

}

function pop_action(){

    if ($("#action").length >0){
        hidden_action = document.getElementById("action"); //for structure.py script
    }
    else {
        hidden_action = document.getElementById("seg_action"); //for segment.py script
    }

    if (hidden_action.value!=""){
        //put last action into redo
        myRegexp = /([^;]+)$/g;
        last_action = myRegexp.exec(hidden_action.value);
        append_redo(last_action[1]);

        //delete the action from the action field to remove from next save
        hidden_action.value = hidden_action.value.replace(/;?[^;]+$/,"")
    }

}


function modify_undo(find, replace){

    undo_log = document.getElementById("undo_log").value;
    n = undo_log.lastIndexOf(find);
    undo_log = undo_log.slice(0, n) + undo_log.slice(n).replace(find, replace);
    document.getElementById("undo_log").value = undo_log;

}

function redo(){

    if (document.getElementById("redo_log").value =="") {alert("Nothing to redo!");return;}
    document.getElementById("undo_state").value = "redo";
    action = pop_redo();
    act(action);

}

function append_redo(redo_action){

    // each redo click should correspond to an action ending in a semicolon
    if (redo_action.length >0){
        document.getElementById("redo_log").value += redo_action + ";";
    }

}

function pop_redo(){

    redo_log = document.getElementById("redo_log").value;
    myRegexp = /([^;]+);$/g;
    redo_action = myRegexp.exec(redo_log);
    document.getElementById("redo_log").value = redo_log.replace(/[^;]+;$/,"");
    return redo_action[1];

}

function disable_buttons(){
    $(".minibtn").prop("disabled",true);
    $(".nav_button").prop("disabled",true);
}

function enable_buttons(){
    $(".minibtn").prop("disabled",false);
    $(".nav_button").prop("disabled",false);
}

function enable_guidelines(url){
    if ((document.getElementById("current_guidelines").value).length > 1 && document.getElementById("current_guidelines").value != "**current_guidelines**"){
        $("#guidelines").prop("disabled",false);
    }
}

function show_guidelines(){
    window.open(document.getElementById("current_guidelines").value,'_blank');
}
