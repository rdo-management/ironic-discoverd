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

import unittest

import eventlet
from ironicclient import exceptions
from keystonemiddleware import auth_token
import mock
from oslo_config import cfg

from ironic_discoverd.test import base
from ironic_discoverd import utils

CONF = cfg.CONF


class TestCheckAuth(base.BaseTest):
    def setUp(self):
        super(TestCheckAuth, self).setUp()
        CONF.set_override('authenticate', True, 'discoverd')

    @mock.patch.object(auth_token, 'AuthProtocol')
    def test_middleware(self, mock_auth):
        CONF.set_override('os_username', 'admin', 'discoverd')
        CONF.set_override('os_tenant_name', 'admin', 'discoverd')
        CONF.set_override('os_password', 'password', 'discoverd')

        app = mock.Mock(wsgi_app=mock.sentinel.app)
        utils.add_auth_middleware(app)

        mock_auth.assert_called_once_with(
            mock.sentinel.app,
            {'admin_user': 'admin', 'admin_tenant_name': 'admin',
             'admin_password': 'password', 'delay_auth_decision': True,
             'auth_uri': 'http://127.0.0.1:5000/v2.0',
             'identity_uri': 'http://127.0.0.1:35357'}
        )

    def test_ok(self):
        request = mock.Mock(headers={'X-Identity-Status': 'Confirmed',
                                     'X-Roles': 'admin,member'})
        utils.check_auth(request)

    def test_invalid(self):
        request = mock.Mock(headers={'X-Identity-Status': 'Invalid'})
        self.assertRaises(utils.Error, utils.check_auth, request)

    def test_not_admin(self):
        request = mock.Mock(headers={'X-Identity-Status': 'Confirmed',
                                     'X-Roles': 'member'})
        self.assertRaises(utils.Error, utils.check_auth, request)

    def test_disabled(self):
        CONF.set_override('authenticate', False, 'discoverd')
        request = mock.Mock(headers={'X-Identity-Status': 'Invalid'})
        utils.check_auth(request)


@mock.patch('ironic_discoverd.node_cache.NodeInfo')
class TestGetIpmiAddress(base.BaseTest):
    def test_ipv4_in_resolves(self, mock_node):
        node = mock_node.return_value
        node.driver_info.get.return_value = '192.168.1.1'
        ip = utils.get_ipmi_address(node)
        self.assertEqual(ip, '192.168.1.1')

    @mock.patch('socket.gethostbyname')
    def test_good_hostname_resolves(self, mock_socket, mock_node):
        node = mock_node.return_value
        node.driver_info.get.return_value = 'www.example.com'
        mock_socket.return_value = '192.168.1.1'
        ip = utils.get_ipmi_address(node)
        mock_socket.assert_called_once_with('www.example.com')
        self.assertEqual(ip, '192.168.1.1')

    def test_bad_hostname_errors(self, mock_node):
        node = mock_node.return_value
        node.driver_info.get.return_value = 'meow'
        self.assertRaises(utils.Error, utils.get_ipmi_address, node)


@mock.patch.object(eventlet.greenthread, 'sleep', lambda _: None)
class TestRetryOnConflict(unittest.TestCase):
    def test_retry_on_conflict(self):
        call = mock.Mock()
        call.side_effect = ([exceptions.Conflict()] * (utils.RETRY_COUNT - 1)
                            + [mock.sentinel.result])
        res = utils.retry_on_conflict(call, 1, 2, x=3)
        self.assertEqual(mock.sentinel.result, res)
        call.assert_called_with(1, 2, x=3)
        self.assertEqual(utils.RETRY_COUNT, call.call_count)

    def test_retry_on_conflict_fail(self):
        call = mock.Mock()
        call.side_effect = ([exceptions.Conflict()] * (utils.RETRY_COUNT + 1)
                            + [mock.sentinel.result])
        self.assertRaises(exceptions.Conflict, utils.retry_on_conflict,
                          call, 1, 2, x=3)
        call.assert_called_with(1, 2, x=3)
        self.assertEqual(utils.RETRY_COUNT, call.call_count)


class TestCapabilities(unittest.TestCase):

    def test_capabilities_to_dict(self):
        capabilities = 'cat:meow,dog:wuff'
        expected_output = {'cat': 'meow', 'dog': 'wuff'}
        output = utils.capabilities_to_dict(capabilities)
        self.assertEqual(expected_output, output)

    def test_dict_to_capabilities(self):
        capabilities_dict = {'cat': 'meow', 'dog': 'wuff'}
        output = utils.dict_to_capabilities(capabilities_dict)
        self.assertIn('cat:meow', output)
        self.assertIn('dog:wuff', output)
