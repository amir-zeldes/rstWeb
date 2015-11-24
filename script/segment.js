/**
 * Client side script for editing elementary discourse units (EDUs).
 * After editing and saving the result is submitted to the corresponding
 * Python script for database update.
 * Author: Amir Zeldes
*/

function act(action){

    if (document.getElementById("undo_state").value != "undo"){//do not log undo actions for save in undo_state: let them get popped
        if (document.getElementById("seg_action").value == ''){
            document.getElementById("seg_action").value = action;
            document.getElementById("dirty").value = "dirty";}
        else{
            document.getElementById("seg_action").value += ";" + action;
        }
        if (document.getElementById("undo_state").value == ""){
            document.getElementById("redo_log").value =""; //new non-undo, non-redo action, reset redo_log
        }
    }

    var action_type = action.split(":")[0];
    var action_params = action.split(":")[1];

    action_seg = $('#'+action_params).parent().attr("id")
    document.getElementById("logging").value += action + "," + action_seg.replace("seg","");
    if (document.getElementById("undo_state").value == ""){
        log_undo = "normal";
    }
    else{
        log_undo = document.getElementById("undo_state").value;
    }
    document.getElementById("logging").value += "," + log_undo + ";";


    if (action_type =="ins"){
        insert_segment(action_params);
        append_undo("del:"+action_params);
        }
    else if (action_type =="del"){
        delete_segment(action_params);
        append_undo("ins:"+action_params);
        }
}

function insert_segment(previous_token_id){

    prev_tok = document.getElementById(previous_token_id)
    if ( $('#segend_post_'+previous_token_id).length ){
        document.getElementById("segend_post_" + previous_token_id).style.display="inline";
    }
    else
    {
        $('#'+previous_token_id).after('<div id="segend_post_'+previous_token_id+'" class="seg_end" onclick="act('+"'del:"+previous_token_id+"'"+')">||</div>');
    }
    document.getElementById(previous_token_id).style.display = "none";
}

function delete_segment(seg_last_tok_id){

    document.getElementById("segend_post_"+seg_last_tok_id).style.display = "none";
    document.getElementById(seg_last_tok_id).style.display="inline";

}