#!/usr/bin/python

# (c) 2016 Kevin Coming
# Re-implementation of bigip_monitor using REST interface
# 
# Changes from original work include:
# -SOAP/Bigsuds dependencies removed, only requests in needed
# -All available node options as of BIG-IP v11.5 are supported
# -Number of API calls needed reduced by combining processes into a single request

from ansible.module_utils.basic import *
import requests
import json


class BigIP_REST:
    def __init__(self, hostname, username, password, verify=False):
        self.username = username
        self.password = password
        self.hostname = hostname
        self.isession = requests.session()
        self.isession.auth = (self.username, self.password)
        self.verify = verify
        if self.verify == False:
            requests.packages.urllib3.disable_warnings()
        #self.isession.verify = verify
        self.baseurl = "https://%s/mgmt/tm" % hostname
        self.monitor_params = ['description',
                               'destination',
                               'interval',
                               'ipDscp',
                               'manualResume',
                               'name',
                               'partition',
                               'recv',
                               'reverse',
                               'send',
                               'timeUntilUp',
                               'timeout',
                               'transparent',
                               'upInterval']

    def monitor_create(self, params):
        monitor_data = {}
        for p in self.monitor_params:
            if params[p]:
                monitor_data[p] = params[p]
        r = self.isession.post(self.baseurl + '/ltm/monitor/%s/' %
                params['kind'],
                data=json.dumps(monitor_data),
                verify = self.verify)
        if r.status_code != 200:
            raise requests.HTTPError(r.json()['message'])
        return True

    def monitor_delete(self, name, partition, kind):
        r = self.isession.delete(self.baseurl + '/ltm/monitor/%s/~%s~%s' %
                (kind, partition, name), verify=self.verify)
        if r.status_code == 200:
            return True
        elif r.status_code == 404:
            return False
        else:
            raise requests.HTTPError(r.json()['message'])

    def monitor_get(self, name, partition, kind):
        r = self.isession.get(self.baseurl + '/ltm/monitor/%s/~%s~%s' %
            (kind, partition, name), verify=self.verify)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            return False
        else:
            raise requests.HTTPError(r.json()['message'])

    def monitor_modify(self, name, partition, kind, params):
        r = self.isession.put(self.baseurl + '/ltm/monitor/%s/~%s~%s' %
                    (kind, partition, name), data=json.dumps(params),
                    verify=self.verify)
        if r.status_code == 200:
            return True
        else:
            raise requests.HTTPError(r.json()['message'])



def main():
    module = AnsibleModule(
        argument_spec = dict(
            state = dict(default='present', choices=['present', 'absent']),
            server = dict(type='str', required=True),
            username = dict(type='str', required=True, aliases=['user']),
            password = dict(type='str', required=True, no_log=True),
            cert = dict(type='str'),
            cipherlist = dict(type='str'),
            compatibility = dict(type='str', choices=['enabled',
                                                      'disabled']),
            defaultsFrom = dict(type='str',),
            description = dict(type='str'),
            destination = dict(type='str'),
            interval = dict(type='int'),
            ipDscp = dict(type='int'),
            key = dict(type='str'),
            kind = dict(type='str', required=True),
            manualResume = dict(type='str', choices=['enabled',
                                                    'disabled']),
            name = dict(type='str', required=True),
            partition = dict(type='str', default='Common'),
            recv = dict(type='str', aliases=['receive']),
            reverse = dict(type='str', choices=['enabled',
                                                'disabled']),
            send = dict(type='str'),
            timeUntilUp = dict(type='int'),
            timeout = dict(type='int'),
            transparent = dict(type='str', choices=['enabled',
                                                   'disabled']),
            upInterval = dict(type='int')
            #username
            #password
        )
    )
    server = module.params['server']
    username = module.params['username']
    password = module.params['password']
    state = module.params['state']
    partition = module.params['partition']
    name = module.params['name']
    kind = module.params['kind']
    result = {'changed' : False }
    i = BigIP_REST(server, username, password, False)
    params_to_change = {}
    if state == 'present':
        try:
            monitor = i.monitor_get(name, partition, kind)
            if not monitor:
                i.monitor_create(module.params)
                result['changed'] = True
            else:
                params_to_change = {}
                for p in i.monitor_params:
                    if (module.params[p] != None) and (monitor[p] !=
                                                       module.params[p]):
                        params_to_change[p] = module.params[p]
                if params_to_change:
                    r = i.monitor_modify(name, partition, kind, params_to_change)
                    if r:
                        result['changed'] = True
        except requests.HTTPError as e:
            module.fail_json(msg = "Error: %s" % e)
    else:
        try:
            if i.monitor_delete(name, partition, kind):
                result['changed'] = True
        except requests.HTTPError as e:
            module.fail_json(msg="Error: %s" %e)
    module.exit_json(**result)


if __name__ == '__main__':
    main()
