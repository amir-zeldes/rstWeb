#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module provides a REST-based API for rstWeb. Meant for local use only
(i.e. by running 'python start_local.py'), since the user 'local' is
automatically logged in and authentication is skipped.

Author: Arne Neumann
"""

from __future__ import print_function
import base64
from collections import defaultdict
import json
import os
from tempfile import mkdtemp, NamedTemporaryFile

import cherrypy  # pylint: disable=import-error

from modules import rstweb_sql
from modules.rstweb_sql import generic_query as sql
from quick_export import quickexp_main
from screenshot import get_png


TEMP_PROJECT = '_temp_convert'


def get_all_docs(user, project):
    """Returns a list of all documents of the given user in the given project."""
    return [elem[0] for elem in sql(
        "SELECT doc FROM docs WHERE user=? AND project=?", (user, project))]

def get_screenshot(file_name, project_name, user, output_format='png'):
    """Produces a screenshot of the rhetorical structure tree of a document from
    the given user in the given project and returns it.

    If `output_format` is `png`, return the image as a download (which will trigger
    the "save file" dialog on the client side.
    If `output_format` is `png-base64`, return a base64-encoded string of the png
    image.
    """
    png_bytes = get_png(file_name, project_name, user=user, mode='local')

    if output_format == 'png':
        cherrypy.response.headers['Content-Type'] = "application/download"
        cherrypy.response.headers['Content-Disposition'] = \
            'attachment; filename="{0}.png"'.format(file_name)
        return png_bytes
    elif output_format == 'png-base64':
        cherrypy.response.headers['Content-Type'] = "data:image/png;base64"
        return base64.b64encode(png_bytes)
    else:
        raise cherrypy.HTTPError(
            400, ("Unknown screenshot format '{0}'. Supported formats: "
                  "png, png-base64.").format(output_format))

def get_rs3_file(file_name, project_name, user):
    """Returns a .rs3 file as a download."""
    kwargs = {'quickexp_doc': file_name, 'quickexp_project': project_name}
    cherrypy.response.headers['Content-Type'] = "application/download"
    cherrypy.response.headers['Content-Disposition'] = \
        'attachment; filename="{0}"'.format(file_name)
    return quickexp_main(user=user, admin='3', mode='local', **kwargs)

def edit_document(file_name, project_name):
    """Opens a document in the rstWeb structure editor."""
    kwargs = {
        'current_doc': file_name,
        'current_guidelines': u'**current_guidelines**',
        'current_project': project_name,
        'serve_mode': u'local'
    }
    url_params = kwargs2urlparams(kwargs)
    raise cherrypy.HTTPRedirect('/structure?{0}'.format(url_params))

def kwargs2urlparams(kwargs):
    """Converts a key-value dict into a string of URL parameters.
    Dict entries with empty values will be ignored. This is used when
    redirecting API requests to existing methods of the rstWeb app.

    Example:

        >>> kwargs2urlparams({'foo': 'bar', 'ham': 'egg', 'a': ''})
        'foo=bar&ham=egg'
    """
    return '&'.join('{0}={1}'.format(k, v) for k, v in kwargs.items() if v)


class APIController(object):
    """REST API for rstWeb"""
    def __init__(self):
        # create a temporary folder for importing files uploaded via the API
        self.import_dir = mkdtemp()

    def import_rs3_file(self, rs3_file, file_name, project_name):
        """Import an .rs3 file into rstWeb's database."""
        # upload the POSTed file into the import directory
        # rs3_file: cherrypy._cpreqbody.Part
        file_content = rs3_file.file.read()
        import_filepath = os.path.join(self.import_dir, file_name)
        with open(import_filepath, 'w') as import_file:
            import_file.write(file_content)

        # create project if it doesn't exist yet
        if project_name not in self.get_projects():
            self.add_project(project_name)

        # import the file into the database, then remove the temporary file
        error = rstweb_sql.import_document(import_filepath, project_name, 'local')
        os.remove(import_file.name)
        return error

    @cherrypy.expose
    def get_index(self):  # pylint: disable=no-self-use
        """Handler for / (GET).
        List all available routes and methods of the rstWeb API.
        """
        response = "<pre>\nrstWeb API\n\nAvailable endpoints:\n\n"

        app = cherrypy.tree.apps['/api']
        dispatcher = app.config['/']['request.dispatch']

        routemap = defaultdict(list)

        for route in dispatcher.mapper.matchlist:
            if route.routepath:
                routemap[route.routepath].extend(route.conditions.get('method'))

        for path in sorted(routemap):
            response += "{base_url}{api_path}{endpoint} ({methods})\n".format(
                base_url=cherrypy.request.base,
                api_path=cherrypy.request.script_name,
                endpoint=path,
                methods=", ".join(routemap[path]))

        cherrypy.response.headers['Content-Type'] = 'text/html;charset=utf-8'
        response += "</pre>\n"
        return response

    @cherrypy.tools.json_out()
    def get_projects(self):  # pylint: disable=no-self-use
        """Handler for /projects (GET).
        Returns a list of all projects.
        """
        return [elem[0] for elem in rstweb_sql.get_all_projects()]

    @cherrypy.expose
    def delete_projects(self):
        """Handler for /projects (DELETE).
        Deletes all projects.
        """
        for project in self.get_projects():
            rstweb_sql.delete_project(project)

        projects = self.get_projects()
        if projects:
            raise cherrypy.HTTPError(
                500, ("Could not delete all projects. Remaining projects: '{0}'.").format(projects))

    @cherrypy.tools.json_out()
    def get_project(self, project_name):  # pylint: disable=no-self-use
        """Handler for /projects/{project_name} (GET).
        Returns metadata about a project (incl. a list of all documents in that project
        of the user 'local').
        """
        return {'documents': get_all_docs('local', project_name)}

    @cherrypy.expose
    def add_project(self, project_name):
        """Handler for /projects/{project_name} (POST).
        Adds a new project to the user 'local'. (Adding a project that already
        exists has no effect.)
        """
        rstweb_sql.create_project(project_name)

        if project_name not in self.get_projects():
            raise cherrypy.HTTPError(500, "Could not add project '{0}'".format(project_name))

    @cherrypy.expose
    def delete_project(self, project_name):
        """Handler for /projects/{project_name} (DELETE).
        Deletes a project. (Deleting a non-existing project has no effect.)

        NOTE: Projects are not linked to users. Any user can delete all projects.
        """
        rstweb_sql.delete_project(project_name)

        if project_name in self.get_projects():
            raise cherrypy.HTTPError(500, "Could not delete project '{0}'".format(project_name))

    @cherrypy.tools.json_out()
    def get_documents(self, project_name=None):  # pylint: disable=no-self-use
        """Handler for /documents (GET) and /documents/{project_name} (GET).
        Returns a JSON struct containing all documents in all projects from the
        user 'local'.
        """
        if project_name is None:
            all_documents = sql(
                "SELECT doc, project FROM docs WHERE user=?", ('local',))
            docs_dict = defaultdict(list)
            for file_name, project in all_documents:
                docs_dict[project].append(file_name)
            return {'documents': docs_dict}
        return get_all_docs('local', project_name)

    @cherrypy.expose
    def delete_documents(self, project_name=None):
        """Handler for /documents (DELETE) and /documents/{project_name} (DELETE).
        Delete all documents (of the user 'local') or delete all documents of
        the given project.
        """
        if project_name is None:
            rstweb_sql.delete_docs_for_user('local')
            assert self.get_documents() == {'documents': {}}
        else:  # delete all documents of a project, but keep the project itself
            # do nothing if project doesn't exist
            if project_name in self.get_projects():
                sql("DELETE FROM rst_nodes WHERE project=?", (project_name,))
                sql("DELETE FROM rst_relations WHERE project=?", (project_name,))
                sql("DELETE FROM docs WHERE project=?", (project_name,))
                assert project_name in self.get_projects()
                assert self.get_documents(project_name) == []

    @cherrypy.expose
    def get_document(self, project_name, file_name, output='rs3'):
        """Handler for /documents/{project_name}/{file_name} (GET).
        Returns a document either as an `rs3` file, a `png` image of an RST tree,
        a base64-encoded png image or opens it in the structure editor.
        """
        # only proceed if the project and file exist (for the user 'local')
        documents = self.get_project(project_name).get('documents')
        if documents is None or file_name not in documents:
            raise cherrypy.HTTPError(
                404, ("File '{0}' not available in project '{1}' for the current user. "
                      "Available files: {2}").format(file_name, project_name, documents))

        if output == 'rs3':
            return get_rs3_file(file_name, project_name, 'local')
        elif output == 'png':
            return get_screenshot(file_name, project_name, 'local', output_format='png')
        elif output == 'png-base64':
            return get_screenshot(file_name, project_name, 'local', output_format='png-base64')
        elif output == 'editor':
            edit_document(file_name, project_name)
        else:
            raise cherrypy.HTTPError(
                400, 'Unknown output format: {0}'.format(output))

    @cherrypy.expose
    def add_document(self, project_name, file_name, rs3_file):
        """Handler for /documents/{project_name}/{file_name} (POST)
        Adds a new document to the given project of the user 'local'.

        Adding a document to a non-existent project will create that project
        and then add the document to it.

        Adding a document under a file_name (that already exists in the given
        project for the user 'local') will also raise an error. To update
        an existing document, use the `update_document` method.

        Parameters
        ----------
        project_name : str
            project that the document will be added to
        file_name : str
            file name under which the document will be stored in the project
        rs3_file : cherrypy._cpreqbody.Part
            a cherrypy representation of the content of the uploaded rs3 file

        Usage example:

        To upload the document 'source.rs3' into the project 'my-project' and
        store it under the name 'target.rs3', run this command in your shell.

            curl -XPOST http://localhost:8080/api/documents/my-project/target.rs3 \
                -F rs3_file=@source.rs3
        """
        # do not overwrite existing document with the same file name
        project_docs = self.get_documents(project_name)
        if file_name in project_docs:
            raise cherrypy.HTTPError(
                400, (("File '{0}' already exists in project '{1}'. "
                       "Use PUT to overwrite it.")).format(file_name, project_name))

        # import rs3 file
        error = self.import_rs3_file(rs3_file, file_name, project_name)

        # check if document was imported
        project_docs = self.get_documents(project_name)
        if error is not None or file_name not in project_docs:
            raise cherrypy.HTTPError(
                500, ("Cannot import document into project '{0}' with "
                      "filename '{1}'. Reason: '{2}'").format(
                          project_name, file_name, error))

    @cherrypy.expose
    def update_document(self, project_name, file_name, rs3_file):
        """Handler for /documents/{project_name}/{file_name} (PUT).
        Updates a document in the given project of the user 'local'.

        Updating a non-existing document is the same as adding a new document.
        """
        # import rs3 file
        error = self.import_rs3_file(rs3_file, file_name, project_name)

        # check if document exists
        project_docs = self.get_documents(project_name)
        if error is not None or file_name not in project_docs:
            raise cherrypy.HTTPError(
                500, ("Cannot update document '{0}' in project '{1}' "
                      "Reason: '{2}'").format(file_name, project_name, error))
        else:
            return "Updated document '{0}' in project '{1}'".format(
                project_name, file_name)

    @cherrypy.expose
    def delete_document(self, project_name, file_name):
        """Handler for /documents/{project_name}/{file_name} (DELETE)
        Deletes a document from a project.
        """
        rstweb_sql.delete_document(file_name, project_name)

        # check if document was deleted
        project_docs = self.get_documents(project_name)
        if file_name in project_docs:
            raise cherrypy.HTTPError(
                500, "Cannot delete document '{0}' from project '{1}' ".format(
                    file_name, project_name))

    @cherrypy.expose
    def convert_file(self, input_file, input_format='rs3', output_format='png'):
        """Handler for /convert (POST).
        Converts an RST document into another format without (permanently)
        storing it in the database.

        Parameters
        ----------
        input_file : cherrypy._cpreqbody.Part
            a cherrypy representation of the content of the uploaded rs3 file
        input_format : str
            format of the input file
        output_format : str
            format that the input file should be converted into

        Usage example:

            curl -XPOST "http://localhost:8080/api/convert?input_format=rs3&output_format=png" \
                -F input_file=@test.rs3 > test.png
        """
        error = None

        if input_format == 'rs3':
            # create temp file, fill it with POSTed file content, import into db,
            # remove temp file.
            temp_file = NamedTemporaryFile(suffix='.rs3', dir=self.import_dir, delete=False)
            input_filepath = temp_file.name
            input_filename = os.path.basename(input_filepath)
            try:
                self.add_document(TEMP_PROJECT, input_filename, input_file)
            except cherrypy.HTTPError as err:
                error = err
            finally:
                if os.path.isfile(input_filepath):
                    os.remove(input_filepath)

            # check if document was imported
            project_docs = self.get_documents(TEMP_PROJECT)
            if error is not None or input_filename not in project_docs:
                raise cherrypy.HTTPError(
                    500, ("Cannot import temp file '{0}'. Reason: '{1}'").format(
                        input_filepath, error))

            # convert to given output format
            if output_format in ('png', 'png-base64'):
                response = self.get_document(TEMP_PROJECT, input_filename, output_format)
            else:
                raise cherrypy.HTTPError(
                    400, "Unknown output format: '{0}'".format(output_format))

            # delete document from database
            self.delete_document(project_name=TEMP_PROJECT, file_name=input_filename)
            return response
        else:
            raise cherrypy.HTTPError(
                400, "Unknown input format: '{0}'".format(input_format))


def jsonify_error(status, message, traceback, version):  #pylint: disable=unused-argument
    """JSONify all CherryPy error responses (created by raising the
    cherrypy.HTTPError exception).
    This is used in the API configuration.
    """
    cherrypy.response.headers['Content-Type'] = 'application/json'
    response_body = json.dumps(
        {
            'error': {
                'http_status': status,
                'message': message,
            }
        })

    cherrypy.response.status = status
    return response_body


def create_api_dispatcher():
    """define all routes of the rstWeb API"""
    dispatcher = cherrypy.dispatch.RoutesDispatcher()

    # / (GET)
    dispatcher.connect(name='api',
                       route='',
                       action='get_index',
                       controller=APIController(),
                       conditions={'method': ['GET']})

    # /projects (GET)
    dispatcher.connect(name='projects',
                       route='/projects',
                       action='get_projects',
                       controller=APIController(),
                       conditions={'method': ['GET']})

    # /projects (DELETE)
    dispatcher.connect(name='projects',
                       route='/projects',
                       action='delete_projects',
                       controller=APIController(),
                       conditions={'method': ['DELETE']})

    # /projects/{project_name} (GET)
    dispatcher.connect(name='projects',
                       route='/projects/{project_name}',
                       action='get_project',
                       controller=APIController(),
                       conditions={'method': ['GET']})

    # /projects/{project_name} (POST)
    dispatcher.connect(name='projects',
                       route='/projects/{project_name}',
                       action='add_project',
                       controller=APIController(),
                       conditions={'method': ['POST']})

    # /projects/{project_name} (DELETE)
    dispatcher.connect(name='projects',
                       route='/projects/{project_name}',
                       action='delete_project',
                       controller=APIController(),
                       conditions={'method': ['DELETE']})

    # /documents (GET)
    dispatcher.connect(name='documents',
                       route='/documents',
                       action='get_documents',
                       controller=APIController(),
                       conditions={'method': ['GET']})

    # /documents (DELETE)
    dispatcher.connect(name='documents',
                       route='/documents',
                       action='delete_documents',
                       controller=APIController(),
                       conditions={'method': ['DELETE']})

    # /documents/{project_name} (GET)
    dispatcher.connect(name='documents',
                       route='/documents/{project_name}',
                       action='get_documents',
                       controller=APIController(),
                       conditions={'method': ['GET']})

    # /documents/{project_name} (DELETE)
    dispatcher.connect(name='documents',
                       route='/documents/{project_name}',
                       action='delete_documents',
                       controller=APIController(),
                       conditions={'method': ['DELETE']})


    # /documents/{project_name}/{file_name} (GET)
    dispatcher.connect(name='documents',
                       route='/documents/{project_name}/{file_name}',
                       action='get_document',
                       controller=APIController(),
                       conditions={'method': ['GET']})

    # /documents/{project_name}/{file_name} (POST)
    dispatcher.connect(name='documents',
                       route='/documents/{project_name}/{file_name}',
                       action='add_document',
                       controller=APIController(),
                       conditions={'method': ['POST']})

    # /documents/{project_name}/{file_name} (PUT)
    dispatcher.connect(name='documents',
                       route='/documents/{project_name}/{file_name}',
                       action='update_document',
                       controller=APIController(),
                       conditions={'method': ['PUT']})

    # /documents/{project_name}/{file_name} (DELETE)
    dispatcher.connect(name='documents',
                       route='/documents/{project_name}/{file_name}',
                       action='delete_document',
                       controller=APIController(),
                       conditions={'method': ['DELETE']})

    # /convert (POST)
    dispatcher.connect(name='documents',
                       route='/convert',
                       action='convert_file',
                       controller=APIController(),
                       conditions={'method': ['POST']})

    return dispatcher
