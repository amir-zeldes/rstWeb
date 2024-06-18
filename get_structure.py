#!/usr/bin/python3.5
# -*- coding: utf-8 -*-

from structure import build_canvas
from modules.rstweb_reader import read_rst
from modules.rstweb_sql import get_rst_rels
import io, sys, os
import cgi, cgitb
import codecs
from six import iteritems


def get_structure_main(**kwargs):

    if "data" in kwargs:
        rs3 = kwargs["data"]
    else:
        #infile = "GUM_news_worship.rs3"
        #rs3 = io.open(infile,encoding="utf8").read()
        return ""

    current_doc = "quick"
    current_project = "quick"

    rels = {}
    nodes, signals, signal_type_dict = read_rst(rs3,rels,as_string=True)
    secedges = []
    for nid in nodes:
        node = nodes[nid]
        node.relkind = "rst"
        if node.relname.endswith("_m"):
            node.relkind = "multinuc"
        elif node.relname == "span":
            node.relkind = "span"
        if node.secedges != "":
            secedges += node.secedges.split(";")
    secedge_data = ";".join(secedges)
    rels = sorted([(k,v) for k,v in iteritems(rels)])
    output = build_canvas(current_doc, current_project, rels, nodes, secedge_data=secedge_data, signal_data=signals,
                          validations="validate_empty;validate_flat;validate_mononuc", signal_type_dict=signal_type_dict)
    return output

def get_structure_main_server():
    theform = cgi.FieldStorage()
    kwargs = {}
    for key in theform:
        kwargs[key] = theform[key].value

    output = get_structure_main(**kwargs)
    output = "Content-Type: text/plain\n\n\n" + output

    if sys.version_info[0] < 3:
        print(output)
    else:
        sys.stdout.buffer.write(output.encode("utf8"))


if "/" in os.environ.get('SCRIPT_NAME', ''):
    mode = "server"
else:
    mode = "local"

if mode == "server":
    UTF8Writer = codecs.getwriter('utf8')
    sys.stdout = UTF8Writer(sys.stdout)
    get_structure_main_server()
