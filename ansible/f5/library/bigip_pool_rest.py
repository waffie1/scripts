#!/usr/bin/python

# (c) 2016 Kevin Coming
# Re-implementation of bigip_node using REST interface
# 
# Changes from original work include:
# -SOAP/Bigsuds dependencies removed, only requests in needed
# -All available node options as of BIG-IP v11.5 are supported
# -Number of API calls needed reduced by combining processes into a single request


from ansible.module_utils.basic import *
import requests
import json

class BigIP_REST:
    def __init__(self, hostname, username, password, verify=True):
        self.username = username
        self.password = password
        self.hostname = hostname
        self.isession = requests.session()
        self.isession.auth = (self.username, self.password)
        self.isession.verify = verify
        self.baseurl = "https://%s/mgmt/tm" % hostname
        self.pool_params = ['allowNat',
                       'allowSnat', 'description',
                       'ignorePersistedWeight',
                       'ipTosToClient',
                       'ipTosToServer',
                       'linkQosToClient',
                       'linkQosToServer',
                       'loadBalancingMode',
                       'minActiveMembers',
                       'minUpMembers',
                       'minUpMembersAction',
                       'minUpMembersChecking',
                       'monitor',
                       'name',
                       'partition',
                       'queueDepthLimit',
                       'queueOnConnectionLimit',
                       'queueTimeLimit',
                       'reselectTries',
                       'serviceDownAction',
                       'slowRampTime',
                      ]

    def pool_add_member(self, name, partition, member_name, member_port):
        r = self.isession.post(self.baseurl +
                '/ltm/pool/~%s~%s/members' % (partition, name),
                data=json.dumps({'name' : '/%s/%s:%s' % (partition,
                    member_name, member_port)}))
        if r.status_code == 200:
            return True
        else:
            raise requests.HTTPError(r.json()['message'])

    def pool_get_member(self, name, partition, member_name, member_port):
        r = self.isession.get(self.baseurl +
            '/ltm/pool/~%s~%s/members/~%s~%s:%s' % (partition, name,
                                                    partition,
                                                    member_name,
                                                    member_port))
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            return False
        else:
            raise requests.HTTPError(r.json()['message'])

    def pool_create(self, params):
        pool_data = {}
        for p in self.pool_params:
            if params[p]:
                pool_data[p] = params[p]
        r = self.isession.post(self.baseurl + '/ltm/pool', 
                               data=json.dumps(pool_data))
        if r.status_code != 200:
            raise requests.HTTPError(r.json()['message'])
        return True

    def pool_delete(self, name, partition):
        r = self.isession.delete(self.baseurl + '/ltm/pool/~%s~%s' %
            (partition, name))
        if r.status_code == 200:
            return True
        elif r.status_code == 404:
            return False
        else:
            raise requests.HTTPError(r.json()['message'])

    def pool_get(self, name, partition):
        r = self.isession.get(self.baseurl + '/ltm/pool/~%s~%s' %
                             (partition, name))
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            return False
        else:
            raise requests.HTTPError(r.json()['message'])

    def pool_modify(self, name, partition, pool_data):
        r = self.isession.put(self.baseurl + '/ltm/pool/~%s~%s' %
                (partition, name), data=json.dumps(pool_data))
        if r.status_code != 200:
            raise requests.HTTPError(r.json()['message'])
        return True


def main():
    module = AnsibleModule(
        argument_spec = dict(
            state = dict(default='present', choices=['present', 'absent']),
            server = dict(type='str', required=True),
            username = dict(type='str', required=True),
            password = dict(type='str', required=True, no_log=True),
            allowNat = dict(type='bool'),
            allowSnat = dict(type='bool'),
            description = dict(type='str'),
            ignorePersistedWeight = dict(type='str', choices=['enabled',
                                                             'disabled']),
            ipTosToClient = dict(type='str'),
            ipTosToServer = dict(type='str'),
            linkQosToClient = dict(type='str'),
            linkQosToServer = dict(type='str'),
            loadBalancingMode = dict(type='str',
                    choices = ['round-robin',
                               'ratio-member',
                               'least-connections-member',
                               'observed-member',
                               'predictive-member',
                               'ratio-node',
                               'least-connections-node',
                               'fastest-node',
                               'observed-node',
                               'predictive-node',
                               'dynamic-ratio-node',
                               'fastest-app-response',
                               'least-sessions',
                               'dynamic-ratio-member',
                               'ratio-session',
                               'ratio-least-connections-member',
                               'ratio-least-connections-node',
                              ]),
            minActiveMembers = dict(type='str'),
            minUpMembers = dict(type='str'),
            minUpMembersAction = dict(type='str'),
            minUpMembersChecking = dict(type='str'),
            monitor = dict(type='str'),
            name = dict(type='str', required=True),
            partition = dict(type='str', default='Common'),
            queueDepthLimit = dict(type='int'),
            queueOnConnectionLimit = dict(type='str'),
            queueTimeLimit = dict(type='int'),
            reselectTries = dict(type='int'),
            serviceDownAction = dict(type='str'),
            slowRampTime = dict(type='int'),
            member_name = dict(type='str'),
            member_port = dict(type='int'),
            member_state = dict(type='str', choices=['enabled',
                                                     'disabled',
                                                     'forcedoffline']),
        )
    )

    server = module.params['server']
    username = module.params['username']
    password = module.params['password']
    state = module.params['state']
    partition = module.params['partition']
    name = module.params['name']
    i = BigIP_REST(server, username, password, False)
    result = {'changed' : False }
    params_to_change = {}
    if state == 'present':
        try:
            pool = i.pool_get(name, partition)
            if not pool:
                i.pool_create(module.params)
                result['changed'] = True
            else:
                #Monitor string has a space at the end???
                pool['monitor'] = pool['monitor'].strip()
                params_to_change = {}
                for p in i.pool_params:
                    if module.params[p] and (pool[p] != module.params[p]):
                        params_to_change[p] = module.params[p]
                if params_to_change:
                    i.pool_modify(name, partition, params_to_change)
                    result['changed'] = True
            if (module.params['member_name'] and module.params['member_port']):
                if not i.pool_get_member(name, partition, module.params['member_name'],
                        module.params['member_port']):
                    i.pool_add_member(name, partition, module.params['member_name'],
                        module.params['member_port'])
                    result['changed'] = True
        except requests.HTTPError as e:
            module.fail_json(msg = "Error: %s" % e)
    else:
        try:
            if i.pool_delete(name, partition):
                result['changed'] = True
        except requests.HTTPError as e:
            module.fail_json(msg="Error: %s" % e)
    module.exit_json(**result)



if __name__ == '__main__':
    main()


