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

"""eDeploy hardware detection and classification plugin.

See https://blueprints.launchpad.net/ironic-discoverd/+spec/edeploy for
details on how to use it. Note that this plugin requires a special ramdisk.
"""

import json
import logging

from oslo_config import cfg

from ironic_discoverd.common.i18n import _LW
from ironic_discoverd.common import swift
from ironic_discoverd.plugins import base

CONF = cfg.CONF


LOG = logging.getLogger('ironic_discoverd.plugins.edeploy')


class eDeployHook(base.ProcessingHook):
    """Interact with eDeploy ramdisk for discovery data processing hooks."""

    def before_update(self, node, ports, node_info):
        """Stores the 'data' key from introspection_data in Swift.

        If the 'data' key exists, updates Ironic extra column
        'hardware_swift_object' key to the name of the Swift object, and stores
        the data in the 'ironic-discoverd' container in Swift.

        Otherwise, it does nothing.
        """

        if 'data' not in node_info:
            LOG.warning(_LW('No eDeploy data was received from the ramdisk'))
            return [], {}

        name = 'extra_hardware-%s' % node.uuid
        self._store_extra_hardware(name,
                                   json.dumps(node_info['data']))
        return [{'op': 'add',
                 'path': '/extra/hardware_swift_object',
                 'value': name}], {}

    def _store_extra_hardware(self, name, data):
        """Handles storing the extra hardware data from the ramdisk"""
        swift_api = swift.SwiftAPI()
        swift_api.create_object(name, data)
