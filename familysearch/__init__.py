r"""This is a WIP, unofficial SDK for accessing
the FamilySearch API. Based heavily on the official
JavaScript SDK
Currently designed to support Python 3.4. Backporting to come in the futre.

A library to interact with the FamilySearch API

Licensed under the FamilySearch API License Agreement;
see the included LICENSE file for details.

Example usage:

from familysearch import FamilySearch

# Log in in a separate step with Basic Authentication
fs = FamilySearch('ClientApp/1.0', 'developer_key')
fs.login('username', 'password')

# Log in in two steps with Basic Authentication
fs = FamilySearch('ClientApp/1.0', 'developer_key')
fs.initialize()
fs.authenticate('username', 'password')

# Resume a previous session
fs = FamilySearch('ClientApp/1.0', developer_key, session='session_id')

# Use the production system instead of the sandbox system
fs = FamilySearch('ClientApp/1.0', developer_key, base='https://familysearch.org')

# Keep current session active
fs.session()

# Log out
fs.logout()
"""

# Python imports
try:
    # Python 3
    from urllib.request import Request as BaseRequest
    from urllib.request import(build_opener, urlopen)
    from urllib.error import HTTPError
    from urllib.parse import(urlsplit, urlunsplit, parse_qs, urlencode)
except ImportError:
    # Python 2
    from urllib import urlencode
    from urllib2 import Request as BaseRequest
    from urllib2 import(build_opener, HTTPError, urlopen)
    from urlparse import(urlsplit, urlunsplit, parse_qs)

import json

__version__ = '0.3pre'

class Request(BaseRequest):
    """Add ability to the Request object to allow it to handle additional methods.

    The Request object has been enhanced to handle PUT, DELETE, OPTIONS and HEAD request methods."""
    def __init__(self, *args, **kwargs):
        self._method = kwargs.pop('method', None)
        BaseRequest.__init__(self, *args, **kwargs)

    def get_method(self):
        if self._method:
            return self._method
        else:
            return BaseRequest.get_method(self)

class object(object): pass
class FamilySearch(object):

    """
    A FamilySearch API proxy

    The constructor must be called with a user-agent string and a developer key.
    A username, password, session ID, and base URL are all optional.

    Public methods:
    needs to be re-written...
    """

    def __init__(self, agent, key, session=None,
                 base='https://sandbox.familysearch.org'):
        """
        Instantiate a FamilySearch proxy object.

        Keyword arguments:
        agent -- User-agent string to use for requests
        key -- FamilySearch developer key (optional if reusing an existing session ID)
        username (optional)
        password (optional)
        session (optional) -- existing session ID to reuse
        base (optional) -- base URL for the API;
                           defaults to 'https://sandbox.familysearch.org'
        """
        self.agent = '%s Python-FS-Stack/%s' % (agent, __version__)
        self.key = key
        self.session_id = session
        self.base = base
        self.user_base = self.base + "/platform/users/"
        self.tree_base = self.base + "/platform/tree/"
        self.opener = build_opener()
        self.logged_in = bool(self.session_id)

        for mixin in self.__class__.__bases__:
            mixin.__init__(self)


    def __getstate__(self):
        """
        Return a tuple containing the state necessary to pickle this instance.
        """
        return ({'agent': ' '.join(self.agent.split(' ')[:-1]),
                 'key': self.key,
                 'session': self.session_id,
                 'base': self.base},
                dict([(session, secret)
                      for (session, secret)
                      in self.oauth_secrets.items()
                      if session == self.session_id]))

    def __setstate__(self, state):
        """
        Restore the saved state obtained from unpickling this instance.
        """
        self.__init__(**state[0])
        self.oauth_secrets = state[1]
        if self.session_id in self.oauth_secrets:
            self.logged_in = False

    def _request(self, url, data=None, headers={}, method=None, nojson=False):
        """
        Make a request to the FamilySearch API.

        Adds the User-Agent header and sets the response format to JSON.
        If the data argument is supplied, makes a POST request unless specified
        in the Method header.

        Returns a file-like object representing the response.
        """
        
        if not nojson:
            if data:
                data = json.dumps(data)
                data = data.encode('utf-8')
        request = Request(url, data, headers, method=method)
        if not nojson:
            if data or method:
                request.add_header('Content-Type', 'application/x-fs-v1+json')
            else:
                request.add_header('Accept', 'application/json')
        if self.logged_in and not self.cookies:
            # Add sessionId parameter to url if cookie is not set
            request.add_header('Authorization', 'Bearer ' + self.session_id)
        request.add_header('User-Agent', self.agent)
        try:
            return self.opener.open(request)
        except HTTPError as error:
            if error.code == 401:
                self.logged_in = False
            raise
    
    def _add_subpath(self, url, subpath):
        """
        Add a subpath to the path component of the given URL.

        For example, adding sub to http://example.com/path?query
        becomes http://example.com/path/sub?query.

        """
        parts = urlsplit(url)
        path = parts[2] + '/' + subpath
        return urlunsplit((parts[0], parts[1], path, parts[3], parts[4]))


    def _add_query_params(self, url, params={}, **kw_params):
        """
        Add the specified query parameters to the given URL.

        Parameters can be passed either as a dictionary or as keyword arguments.

        """
        parts = urlsplit(url)
        query_parts = parse_qs(parts[3])
        query_parts.update(params)
        query_parts.update(kw_params)
        query = urlencode(query_parts, True)
        return urlunsplit((parts[0], parts[1], parts[2], query, parts[4]))


    def _fs2py(self, response, nojson=False):
        """
        Take JSON from FamilySearch response, and allow Python to handle it.
        """
        if hasattr(response, "read"):
            response = response.read()
            response = response.decode("utf-8")
        if not nojson:
            response = json.loads(response)
        return response


    def _remove_nones(self, arg):
        """
        Remove all None values from a nested dict structure.
        This method exists because the FamilySearch API returns all attributes
        in a JSON response, with empty values set to null instead of being
        hidden from the response.
        """
        if isinstance(arg, dict):
            return dict([(k, self._remove_nones(v)) for (k, v) in arg.iteritems() if v is not None])
        elif isinstance(arg, list):
            return [self._remove_nones(i) for i in arg if i is not None]
        else:
            return arg
        
    def get(self, url, data=None, headers={}, method=None, nojson=False):
        return self._fs2py(self._request(url, data, headers, method, nojson), nojson)

# FamilySearch imports

from . import(discovery, authentication, authorities, changeHistory,
              discussions, memories, notes, parentsAndChildren, pedigree, 
              person, places, records,searchAndMatch, sourceBox, sources,
              spouses, user, utilities, vocabularies)
