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

import json
try:
    from unittest import mock
except ImportError:
    import mock

from ironic_discoverd.plugins import edeploy
from ironic_discoverd.test import base as test_base


@mock.patch.object(edeploy.swift, 'SwiftAPI', autospec=True)
class TestEdeploy(test_base.NodeTest):

    def setUp(self):
        super(TestEdeploy, self).setUp()
        self.hook = edeploy.eDeployHook()

    def test_data_recieved(self, swift_mock):
        node_info = {'data': [['memory', 'total', 'size', '4294967296'],
                              ['cpu', 'physical', 'number', '1'],
                              ['cpu', 'logical', 'number', '1']]}
        self.hook.before_processing(node_info)
        node_patches, _ = self.hook.before_update(self.node, None, node_info)
        swift_conn = swift_mock.return_value
        name = 'extra_hardware-%s' % self.uuid
        data = json.dumps(node_info['data'])
        swift_conn.create_object.assert_called_once_with(name, data)
        self.assertEqual('add',
                         node_patches[0]['op'])
        self.assertEqual('/extra/hardware_swift_object',
                         node_patches[0]['path'])
        self.assertEqual(name,
                         node_patches[0]['value'])

    def test_no_data_recieved(self, swift_mock):
        node_info = {'cats': 'meow'}
        self.hook.before_processing(node_info)
        node_patches, _ = self.hook.before_update(self.node, None, node_info)
        swift_conn = swift_mock.return_value
        self.assertEqual(0, len(node_patches))
        self.assertFalse(swift_conn.create_object.called)
