# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import argparse
import json

from oslo_utils import netutils
import requests
import six

from ironic_discoverd.common.i18n import _


_DEFAULT_URL = 'http://' + netutils.get_my_ipv4() + ':5050/v1'
_ERROR_ENCODING = 'utf-8'


def _prepare(base_url, auth_token):
    base_url = (base_url or _DEFAULT_URL).rstrip('/')
    if not base_url.endswith('v1'):
        base_url += '/v1'
    headers = {'X-Auth-Token': auth_token} if auth_token else {}
    return base_url, headers


class ClientError(requests.HTTPError):
    """Error returned from a server."""
    def __init__(self, response):
        # discoverd returns error message in body
        msg = response.content.decode(_ERROR_ENCODING)
        super(ClientError, self).__init__(msg, response=response)

    @classmethod
    def raise_if_needed(cls, response):
        """Raise exception if response contains error."""
        if response.status_code >= 400:
            raise cls(response)


def introspect(uuid, base_url=None, auth_token=None,
               new_ipmi_password=None, new_ipmi_username=None):
    """Start introspection for a node.

    :param uuid: node uuid
    :param base_url: *ironic-discoverd* URL in form: http://host:port[/ver],
                     defaults to ``http://<current host>:5050/v1``.
    :param auth_token: Keystone authentication token.
    :param new_ipmi_password: if set, *ironic-discoverd* will update IPMI
                              password to this value.
    :param new_ipmi_username: if new_ipmi_password is set, this values sets
                              new IPMI user name. Defaults to one in
                              driver_info.
    """
    if not isinstance(uuid, six.string_types):
        raise TypeError(_("Expected string for uuid argument, got %r") % uuid)
    if new_ipmi_username and not new_ipmi_password:
        raise ValueError(_("Setting IPMI user name requires a new password"))

    base_url, headers = _prepare(base_url, auth_token)
    params = {'new_ipmi_username': new_ipmi_username,
              'new_ipmi_password': new_ipmi_password}
    res = requests.post("%s/introspection/%s" % (base_url, uuid),
                        headers=headers, params=params)
    ClientError.raise_if_needed(res)


def get_status(uuid, base_url=None, auth_token=None):
    """Get introspection status for a node.

    New in ironic-discoverd version 1.0.0.
    :param uuid: node uuid.
    :param base_url: *ironic-discoverd* URL in form: http://host:port[/ver],
                     defaults to ``http://<current host>:5050/v1``.
    :param auth_token: Keystone authentication token.
    :raises: *requests* library HTTP errors.
    """
    if not isinstance(uuid, six.string_types):
        raise TypeError(_("Expected string for uuid argument, got %r") % uuid)

    base_url, headers = _prepare(base_url, auth_token)
    res = requests.get("%s/introspection/%s" % (base_url, uuid),
                       headers=headers)
    ClientError.raise_if_needed(res)
    return res.json()


def discover(uuids, base_url=None, auth_token=None):
    """Post node UUID's for discovery.

    DEPRECATED. Use introspect instead.
    """
    if not all(isinstance(s, six.string_types) for s in uuids):
        raise TypeError(_("Expected list of strings for uuids argument, "
                          "got %s") % uuids)

    base_url, headers = _prepare(base_url, auth_token)
    headers['Content-Type'] = 'application/json'
    res = requests.post(base_url + "/discover",
                        data=json.dumps(uuids), headers=headers)
    ClientError.raise_if_needed(res)


if __name__ == '__main__':  # pragma: no cover
    parser = argparse.ArgumentParser(description='Discover nodes.')
    parser.add_argument('cmd', metavar='cmd',
                        choices=['introspect', 'get_status'],
                        help='command: introspect or get_status.')
    parser.add_argument('uuid', metavar='UUID', type=str,
                        help='node UUID.')
    parser.add_argument('--base-url', dest='base_url', action='store',
                        default=_DEFAULT_URL,
                        help='base URL, default to localhost.')
    parser.add_argument('--auth-token', dest='auth_token', action='store',
                        default='',
                        help='Keystone token.')
    args = parser.parse_args()
    func = globals()[args.cmd]
    try:
        res = func(uuid=args.uuid, base_url=args.base_url,
                   auth_token=args.auth_token)
    except Exception as exc:
        print('Error:', exc)
    else:
        if res:
            print(json.dumps(res))
