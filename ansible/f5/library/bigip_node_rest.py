#!/usr/bin/python

# (c) 2016 Kevin Coming kevcom@gmail.com
# Version 1.0a initial release
# Ansible module for managing F5 BIG-IP nodes using iControl REST
# Required BIG-IP v11.5 or higher
# requires python requests module.


DOCUMENTATION = '''
---
module: bigip_node_rest
short_description: "Manages F5 BIG-IP LTM nodes"
description:
    - "Manages F5 BIG-IP LTM nodes via iControl REST API"
version_added: ".1"
author: "Kevin Coming"
notes:
    - "Requires BIG-IP software version >= 11.5"
    - "Best run as a local_action in your playbook"
requirements:
    - "none"
options:
    state:
        description:
            - Node member state
        required: true
        default: present
        choices: ['present', 'absent']
        aliases: []
    server:
        description:
            - BIG-IP host
        required: true
        default: null
        choices: []
        aliases: []
    username:
        description:
            - BIG-IP Username
        required: true
        default: null
        choices: []
        aliases: []
    password:
        description:
            - BIG-IP Password
        required: true
        default: null
        choices: []
        aliases: []
    partition:
        description:
            - BIG-IP Partition that node resides in
        required: False
        default: Common
        choices: []
        aliases: []
    name:
        description:
            - Node name
        required: True
        default: none
        choices: []
        aliases: []
    address:
        description:
            - Node IP address.
            - Required when you want to create the node(state is present but does not exist on BIG-IP)
        required: False
        default: none
        choices: []
        aliases: []
    description:
        description:
            - Node description
        required: False
        default: none
        choices: []
        aliases: []
    monitor:
        description:
            - Health monitor to associates with the node
            - Multiple monitor support untested
        required: False
        default: none
        choices: []
        aliases: []
    ratio:
        description:
            - The ratio weight to assign to the node
        required: False
        default: none
        choices: []
        aliases: []
    connectionLimit:
        description:
            - Max number of established connections for the node
        required: False
        default: none
        choices: []
        aliases: ['conn_limit']
    rateLimit:
        description:
            - Max number of connections per second for the node
        required: False
        default: none
        choice: []
        aliases: ['rate_limit']
    node_state:
        description:
            - Determines the operational state of the node
        required: False
        default: none
        choices: ['enabled', disabled', 'forcedoffline']
        aliases: []

'''

EXAMPLES = '''
---

  - name: Add a new node
  local_action:
    module: bigip_node_rest
    server: big_hostname
    username: bigip_username
    password: bigip_password
    state: present
    partition: Common
    address: 192.168.0.1
    name: testnode1
    description: test

  - name: Delete a node
  local_action:
    module: bigip_node_rest
    server: big_hostname
    username: bigip_username
    password: bigip_password
    state: absent
    name: testnode1

  - name: Disable a node
  local_action:
    module: bigip_node_rest
    server: big_hostname
    username: bigip_username
    password: bigip_password
    state: present
    name: testnode1
    node_state: disabled

  - name: Multiple node specific monitors, avail requirements: at least 1
  local_action:
    module: bigip_node_rest
    server: big_hostname
    username: bigip_username
    password: bigip_password
    state: present
    name: testnode1
    monitor: "min 1 of /Common/icmp /Common/tcp"

  - name: Multiple node specific monitors, avail requirements: all
  local_action:
    module: bigip_node_rest
    server: big_hostname
    username: bigip_username
    password: bigip_password
    state: present
    name: testnode1
    monitor: "/Common/icmp and /Common/tcp"

'''


from ansible.module_utils.basic import *
import json
try:
    import requests
except ImportError:
    HAS_REQUESTS = False
else:
    HAS_REQUESTS = True



class BigIP_REST:
    def __init__(self, hostname, username, password, verify=True):
        self.username = username
        self.password = password
        self.hostname = hostname
        self.isession = requests.session()
        self.isession.auth = (self.username, self.password)
        self.isession.verify = verify
        self.baseurl = "https://%s/mgmt/tm" % hostname
        self.node_params = ['address',
                            'connectionLimit',
                            'description',
                            'name',
                            'partition',
                            'logging',
                            'monitor',
                            'rateLimit',
                            'ratio']


    def node_create(self, params):
        node_data = {}
        for p in self.node_params:
            if params[p]:
                node_data[p] = params[p]
        if params['node_state'] and params['node_state'] != 'enabled':
            if params['node_state'] == 'disabled':
                node_data['session'] = 'user-disabled'
            elif params['node_state'] == 'forcedoffline':
                node_data['session'] = 'user-disabled'
                node_data['state'] = 'user-down'
        r = self.isession.post(self.baseurl + '/ltm/node',
                           data=json.dumps(node_data))
        if r.status_code != 200:
            raise requests.HTTPError(r.json()['message'])
        return True

    def node_delete(self, name, partition):
        r = self.isession.delete(self.baseurl + '/ltm/node/~%s~%s' %
                            (partition, name))
        if r.status_code == 200:
            return True
        elif r.status_code == 404:
            return False
        else:
            raise requests.HTTPError(r.json()['message'])


    def node_get(self, name, partition):
        r = self.isession.get(self.baseurl + '/ltm/node/~%s~%s' %
                             (partition, name))
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            return False
        else:
            raise requests.HTTPError(r.json()['message'])

    def node_modify(self, name, partition, param_dict):
        r = self.isession.put(self.baseurl + '/ltm/node/~%s~%s' %
            (partition, name), data = json.dumps(param_dict))
        if r.status_code == 200:
            return True
        else:
            raise requests.HTTPError(r.json()['message'])


def main():
    module = AnsibleModule(
        argument_spec = dict(
            state = dict(default='present', choices=['present', 'absent']),
            server = dict(type='str', required=True),
            username = dict(type='str', required=True),
            password = dict(type='str', required=True, no_log=True),
            partition = dict(type='str', default='Common'),
            name = dict(type='str', required=True),
            address = dict(type='str'),
            description = dict(type='str'),
            monitor = dict(type='str'),
            ratio = dict(type='int'),
            connectionLimit = dict(type='int', aliases=['conn_limit']),
            rateLimit = dict(type='str', aliases=['rate_limit']),
            node_state = dict(type='str', choices=['enabled',
                                                      'disabled',
                                                      'forcedoffline']),
            logging = dict(type='str', choices=['enabled', 'disabled']),
        )
    )
    if not HAS_REQUESTS:
        module.fail_json(msg="requests is required for this module")
    server = module.params['server']
    username = module.params['username']
    password = module.params['password']
    state = module.params['state']
    partition = module.params['partition']
    name = module.params['name']
    result = {'changed' : False }
    i = BigIP_REST(server, username, password, False)
    if state == 'present':
        try:
            node = i.node_get(name, partition)
            if not node:
                #Create Node
                if not module.params['address']:
                    module.fail_json(msg="address required to create the "\
                        "the node.  state is present and the node does "\
                        "not exist.")

                i.node_create(module.params)
                result['changed'] = True
            else:
                #Modify Node
                params_to_change = {}
                if module.params['address'] != node['address']:
                    module.fail_json(msg="Changing the IP Address of a node "\
                        "is not supported.")
                # bigip rateLimit is a str for some reason, and sets itself
                # to disabled instead of 0.  I am swapping 0 for disabled
                # here so the script can determine if a change is actually
                # needed
                if module.params['rateLimit'] == "0":
                    module.params['rateLimit'] = 'disabled'
                for p in i.node_params:
                    if (module.params[p] != None) and (node[p] !=
                                                       module.params[p]):
                        params_to_change[p] = module.params[p]
                #Map session and state to easily understood node_state
                if module.params['node_state'] == 'enabled':
                    if 'disabled' in node['session']:
                        params_to_change['session'] = 'user-enabled'
                        params_to_change['state'] = 'user-up'
                elif module.params['node_state'] == 'disabled':
                    if ('enabled' in node['session'] or
                        'user-down' in node['state']):
                        params_to_change['session'] = 'user-disabled'
                        params_to_change['state'] = 'user-up'
                elif module.params['node_state'] == 'forcedoffline':
                    if not (node['session'] == 'user-disabled' and
                            node['state'] == 'user-down'):
                        params_to_change['session'] = 'user-disabled'
                        params_to_change['state'] = 'user-down'
                if 'rateLimit' in params_to_change:
                    if params_to_change['rateLimit'] == 0:
                        params_to_change['rateLimit'] = 'disabled'
                if params_to_change:
                    r = i.node_modify(name, partition, params_to_change)
                    if r:
                        result['changed'] = True
        except requests.HTTPError as e:
            module.fail_json(msg="Error: %s" % e)
    else:
        try:
            if i.node_delete(name, partition):
                result['changed'] = True
        except requests.HTTPError as e:
            module.fail_json(msg="Error: %s" % e)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
