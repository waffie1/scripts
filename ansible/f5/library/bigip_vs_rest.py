#!/usr/bin/python

from ansible.module_utils.basic import *


def fp_name(partition, name):
    return "/%s/%s" % (partition, name)


def main():
    module = AnsibleModule(
        argument_spec = dict(
            state = dict(default='present', choices=['present', 'absent',
                                                     'enabled', 'disabled']),
            bigip_server = dict(type='str', required=True),
            username = dict(type='str', required=True),
            password = dict(type='str', required=True, no_log=True),
            partition = dict(type='str', default='Common')
            name = dict(type='str', required=True),
            destination = dict(type='str'),
            port = dict(type='int'),
            def_pool = dict(type=str)
            def_persistence_profile = dict(type='str')




if __name__ == "__main__":
    main()
