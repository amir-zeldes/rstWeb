#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <nlpbox.programming@arne.cl>

"""
Tests for the rstWeb REST API.
"""

from __future__ import print_function
import base64
import io
import os

import pexpect
import pytest  # pylint: disable=import-error
import requests
from PIL import Image
import imagehash  # pylint: disable=import-error


TEMP_PROJECT = '_temp_convert' # TODO: import it once we have a setup.py

TESTDIR = os.path.dirname(__file__)
RS3_FILEPATH = os.path.join(TESTDIR, 'test1.rs3')
EXPECTED_PNG1 = os.path.join(TESTDIR, 'result1.png')
BASEURL = "http://127.0.0.1:8080/api"


@pytest.fixture(scope="session", autouse=True)
def start_api():
    """This function will start rstWeb in a separate process before the tests are
    run and shut it down afterwards.
    """
    print("starting rstWeb...")
    child = pexpect.spawn('python start_local.py')

    child.expect('Serving on http://127.0.0.1:8080')

    # delete all existing projects and documents before we start testing
    res = requests.delete('{}/projects'.format(BASEURL))
    assert res.status_code == 200

    # 'yield' provides the fixture value (we don't need it, but it marks the
    # point when the 'setup' part of this fixture ends).
    yield res

    print("stopping rstWeb...")
    child.close()


@pytest.fixture(scope="function", autouse=True)
def delete_projects():
    """delete all projects after each test function is finished"""
    # 'yield' provides the fixture value (we don't need it, but it marks the
    # point when the 'setup' part of this fixture ends).
    yield True

    # delete all existing projects and documents before we start testing
    res = requests.delete('{}/projects'.format(BASEURL))
    assert res.status_code == 200


def image_matches(produced_file, expected_files=(EXPECTED_PNG1,)):
    """Return True, iff the average hash of the produced image matches any of the
    expected images.
    """
    produced_hash = imagehash.average_hash(Image.open(produced_file))

    expected_hashes = [imagehash.average_hash(Image.open(ef)) for ef in expected_files]
    return any([produced_hash == expected_hash for expected_hash in expected_hashes])


def get_projects():
    """Retrieve a list of all projects."""
    return requests.get('{}/projects'.format(BASEURL))


def delete_project(project_name):
    """Delete the given project."""
    return requests.delete('{0}/projects/{1}'.format(BASEURL, project_name))


def add_project(project_name):
    """Add a new project."""
    return requests.post('{0}/projects/{1}'.format(BASEURL, project_name))


def get_documents(project_name=None):
    """Retrieve a list of all documents or of all documents from the given project"""
    if project_name is None:
        return requests.get('{}/documents'.format(BASEURL))
    return requests.get('{0}/documents/{1}'.format(BASEURL, project_name))


def get_document(project_name, document_name, output='rs3'):
    """Retrieve a document in the given output format."""
    return requests.get(
        '{0}/documents/{1}/{2}?output={3}'.format(
            BASEURL, project_name, document_name, output))


def add_document(project_name, document_name, rs3_filepath):
    """Add a new document."""
    with open(rs3_filepath, 'rb') as rs3_file:
        return requests.post(
            '{0}/documents/{1}/{2}'.format(BASEURL, project_name, document_name),
            files={'rs3_file': rs3_file})


def update_document(project_name, document_name, rs3_filepath):
    """Replace a stored document."""
    with open(rs3_filepath, 'rb') as rs3_file:
        return requests.put(
            '{0}/documents/{1}/{2}'.format(BASEURL, project_name, document_name),
            files={'rs3_file': rs3_file})


def delete_document(project_name, document_name):
    """Delete a document."""
    return requests.delete(
        '{0}/documents/{1}/{2}'.format(BASEURL, project_name, document_name))


def delete_documents(project_name=None):
    """Delete all documents (or all documents of the given project)."""
    if project_name is None:  # delete all documents
        return requests.delete('{0}/documents'.format(BASEURL))
    return requests.delete('{0}/documents/{1}'.format(BASEURL, project_name))


def test_rs3_to_png():
    """The rstviewer-service API converts an .rs3 file into the expected image."""
    with open(RS3_FILEPATH) as input_file:
        input_text = input_file.read()

    res = requests.post(
        '{}/convert?input_format=rs3&output_format=png'.format(BASEURL),
        files={'input_file': input_text})
    # delete the project used for conversion
    delete_project(TEMP_PROJECT)

    assert image_matches(io.BytesIO(res.content))


def test_rs3_to_png_base64():
    """The rstviewer-service API converts an .rs3 file into the expected base64 encoded image."""
    with open(RS3_FILEPATH) as input_file:
        input_text = input_file.read()

    res = requests.post(
        '{}/convert?input_format=rs3&output_format=png-base64'.format(BASEURL),
        files={'input_file': input_text})
    png_bytes = base64.b64decode(res.content)
    # delete the project used for conversion
    delete_project(TEMP_PROJECT)

    assert image_matches(io.BytesIO(png_bytes))


def test_get_index():
    """GET / works."""
    res = requests.get(BASEURL)
    assert 'rstWeb API' in res.content


def test_projects():
    """Projects can be added, removed and listed."""
    res = get_projects()
    assert res.json() == []

    res = add_project("proj1")
    res = get_projects()
    assert res.json() == ["proj1"]

    res = add_project("proj2")
    res = get_projects()
    assert res.json() == ["proj1", "proj2"]

    res = delete_project("proj1")
    res = get_projects()
    assert res.json() == ["proj2"]

    # delete all projects
    res = requests.delete('{}/projects'.format(BASEURL))
    res = get_projects()
    assert res.json() == []

    # deleting a non-existing project should do nothing
    res = delete_project("nonexisting_project")
    assert res.status_code == 200
    res = get_projects()
    assert res.json() == []


def test_documents():
    """Documents can be added, removed and listed."""
    # there are no documents in any project when we start
    res = get_documents()
    assert res.json() == {'documents': {}}

    # we can add documents to different projects
    res = add_document('project1', 'doc1', RS3_FILEPATH)
    res = add_document('project1', 'doc2', RS3_FILEPATH)
    res = add_document('project2', 'doc3', RS3_FILEPATH)

    # we cannot add a document to a project if a document with the same
    # name exists
    res = add_document('project1', 'doc1', RS3_FILEPATH)
    assert res.status_code == 400

    # we can list the documents we just added
    res = get_documents()
    assert res.json() == {
        'documents': {'project1': ['doc1', 'doc2'],
                      'project2': ['doc3']}}

    res = get_documents('project1')
    assert res.json() == ['doc1', 'doc2']

    # we can retrieve a document we added
    res = get_document('project1', 'doc1')
    # rstWeb parses and reformats uploaded documents, so we can't
    # simply compare the files
    assert 'they accepted the offer' in res.content

    # after we delete a document, we can no longer retrieve it
    delete_document('project1', 'doc1')
    res = get_documents('project1')
    assert res.json() == ['doc2']

    res = get_document('project1', 'doc1')
    assert res.status_code == 404

    # we can delete all documents of a project
    res = delete_documents('project1')
    assert res.status_code == 200
    res = get_documents('project1')
    assert res.json() == []

    # we can delete all documents
    res = get_documents()
    assert res.json() == {'documents': {'project2': ['doc3']}}
    res = delete_documents()
    assert res.status_code == 200
    res = get_documents()
    assert res.json() == {'documents': {}}


def test_open_document():
    """A stored document can be opened in the structure editor."""
    add_document('project1', 'doc1', RS3_FILEPATH)
    res = get_document('project1', 'doc1', output='editor')
    assert res.status_code == 200
    for string in ('Structure editor', 'they accepted the offer'):
        assert string in res.content


def test_update_document():
    """A stored document can be replaced with a newly uploaded one."""
    res = add_document('project1', 'doc1', RS3_FILEPATH)
    res = get_document('project1', 'doc1')
    assert 'they accepted the offer' in res.content

    update_document('project1', 'doc1', 'tests/test2.rs3')
    res = get_document('project1', 'doc1')
    assert 'drive a car' in res.content
