#!/usr/bin/python

# TODO: test cert/key/chain modification

# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
module: bigip_ssl_profile
short_description: A module to manage BigIP LTM SSL Profiles
description:
  - This module will add/delete or modify client and server SSL
    profiles on an F5 BigIP LTM device.
  - This profiles takes the approach of only modifying values that are
    explicitly present.  If you do not specify an option in your playbook,
    it will be inherited from the parent on creation, or left as is on modify.
  - All option values can be set to 'default-value' to set the profile
    back to inherit the attribute from the parent profile.
  - See BigIP Manual for a complete description of options below.  I have
    provided the tmsh name for each option for easy reference.
version_added: 2.2
options:
  state:
    description:
      - ssl profile state, determines if certificate is imported or deleted
    required: true
    default: present
    choices:
      - present
      - absent
  server:
    description:
      - BIG-IP host
    required: true
  server_port:
    description:
      - BIG-IP server port
    required: false
    default: 443
  user:
    description:
      - BIG-IP Username
    required: true
  password:
    description:
      - BIG-IP Password
    required: true
  partition:
    description:
      - BIG-IP partition to use when adding/deleting certificate
    required: false
    default: Common
  profile_type:
    description:
      - Specifies if this is a client or server ssl profile
    required: true
    choices:
      - clientssl
      - serverssl
  description:
    description:
      - Set the description on the profile.
    required: false
    default: none
  alertTimeout:
    description:
      - ClientSSL Option
      - tmsh = alert-timeout
    required: false
    choices:
      - intteger (seconds)
      - indefinite
      - default-value
    default: none
  allowDynamicRecordSizing:
    description:
      - ClientSSL Option
    required: false
    choices:
      - enabled
      - disabled
      - default-value
    default: none
  allowExpiredCrl:
    description:
      - ClientSSL Option
      - tmsh = allow-expired-crl
    required: false
    choices:
      - enabled
      - disabled
      - default-value
    default: none
  allowNonSsl:
    description:
      - ClientSSL Option
      - tmsh = allow-non-ssl
    required: false
    choices:
      - enabled
      - disabled
      - default-value
    default: none
  authenticate:
    description:
      - ClientSSL Option
      - tmsh = authenticate
    required: false
    choices:
      - once
      - always
      - default-value
    default: none
  authenticateDepth:
    description:
      - ClientSSL Option
      - tmsh = authenticate-depth
    required: false
    choices:
      - integer
      - default-value
    default: none
  caFile:
    description:
      - ClientSSL Option
      - tmsh = ca-file
    required: false
    choices:
      - string
      - default-value
    default: none
  cacheSize:
    description:
      - ClientSSL Option
      - tmsh = cache-size
    required: false
    choices:
      - integer (sessions)
      - default-value
    default: none
  cacheTimeout:
    description:
      - ClientSSL Option
      - tmsh = cache-timeout 
    required: false
    choices:
      - integer (seconds)
      - default-value
    default: none
  cert:
    description:
      - ClientSSL Option
      - tmsh = cert
    required: false
    choices:
      - filename
    default: none
  certExtensionIncludes:
    description:
      - ClientSSL Option
      - tmsh = cert-extension-includes
    required: false
    choices:
      - list of extensions
      - default-value
    default: none
  certLifespan:
    description:
      - ClientSSL Option
      - tmsh = proxy-ca-lifespan
    required: false
    choices:
      - integer (days)
      - default-value
    default: none
  certLookupByIpaddrPort:
    description:
      - ClientSSL Option
      - tmsh = cert-lookup-by-ipaddr-port
    required: false
    choices:
      - enabled
      - disabled
      - default-value
    default: none
  chain:
    description:
      - ClientSSL Option
      - tmsh = chain
    required: false
    choices:
      - filename
    default: none
  ciphers:
    description:
      - ClientSSL Option
      - tmsh = ciphers
    required: false
    choices:
      - string
      - default-value
    default: none
  clientCertCa:
    description:
      - ClientSSL Option
      - tmsh = client-cert-ca
    required: false
    choices:
      - filename
      - default-value
    default: none
  crlFile:
    description:
      - ClientSSL Option
      - tmsh = crl-file
    required: false
    choices:
      - filename
      - default-value
    default: none
  defaultsFrom:
    description:
      - ClientSSL Option
      - tmsh = defaults-from
    required: false
    choices:
      - sslprofile
      - default-value
    default: none
  destinationIpBlacklist:
    description:
      - ClientSSL Option
      - tmsh = destination-ip-blacklist
    required: false
    choices:
      - name
      - default-value
    default: none
  destinationIpWhitelist:
    description:
      - ClientSSL Option
      - tmsh = destination-ip-whitelist
    required: false
    choices:
      - name
      - default-value
    default: none
  forwardProxyBypassDefaultAction:
    description:
      - ClientSSL Option
      - tmsh = forward-proxy-bypass-default-action
    required: false
    choices:
      - intercept
      - bypass
      - default-value
    default: none
  genericAlert:
    description:
      - ClientSSL Option
      - tmsh = generic-alert
    required: false
    choices:
      - enabled
      - disabled
      - default-value
    default: none
  handshakeTimeout:
    description:
      - ClientSSL Option
      - tmsh = handshake-timeout
    required: false
    choices:
      - integer
      - indefinite
      - default-value
    default: none
  hostnameBlacklist:
    description:
      - ClientSSL Option
      - tmsh = hostname-blacklist
    required: false
    choices:
      - name
      - default-value
    default: none
  hostnameWhitelist:
    description:
      - ClientSSL Option
      - tmsh = hostname-whitelist
    required: false
    choices:
      - name
      - default-value
    default: none
  key:
    description:
      - ClientSSL Option
      - tmsh = key
    required: false
    choices:
      - filename
    default: none
  maxActiveHandshakes:
    description:
      - ClientSSL Option
      - tmsh = ???
    required: false
    choices:
      - integer
      - indefinite
      - default-value
    default: none
  maxAggregateRenegotiationPerMinute:
    description:
      - ClientSSL Option
      - tmsh = max-aggregate-renegotiation-per-minute
    required: false
    choices:
      - integer
      - default-value
    default: none
  maxRenegotiationsPerMinute:
    description:
      - ClientSSL Option
      - tmsh = max-renegotiations-per-minute
    required: false
    choices:
      - integer
      - default-value
    default: none
  maximumRecordSize:
    description:
      - ClientSSL Option
      - tmsh = ???
    required: false
    choices:
      - integer
      - default-value
    default: none
  modSslMethods:
    description:
      - ClientSSL Option
      - tmsh = mod-ssl-methods
    required: false
    choices:
      - enabled
      - disabled
      - default-value
    default: none
  mode:
    description:
      - ClientSSL Option
      - tmsh = mode
    required: false
    choices:
      - enabled
      - disabled
      - default-value
    default: none
  name:
    description:
      - The name of the ssl profile
    required: false
    choices:
      - name
    default: none
  passphrase:
    description:
      - ClientSSL Option
      - tmsh = passphrase
    required: false
    choices:
      - none
      - passphrase
      - default-value
    default: none
  peerCertMode:
    description:
      - ClientSSL Option
      - tmsh = peer-cert-mode
    required: false
    choices:
      - auto
      - ignore
      - request
      - require
      - default-value
    default: none
  peerNoRenegotiateTimeout:
    description:
      - ClientSSL Option
      - tmsh = peer-no-renegotiate-timeout
    required: false
    choices:
      - integer
      - indefinite
      - default-value
    default: none
  proxyCaCert:
    description:
      - ClientSSL Option
      - tmsh = proxy-ca-cert
    required: false
    choices:
      - filename
      - default-value
    default: none
  proxyCaKey:
    description:
      - ClientSSL Option
      - tmsh = proxy-ca-key
    required: false
    choices:
      - filename
      - default-value
    default: none
  proxyCaPassphrase:
    description:
      - ClientSSL Option
      - tmsh = proxy-ca-passphrase
    required: false
    choices:
      - string
      - default-value
    default: none
  proxySsl:
    description:
      - ClientSSL Option
      - tmsh = proxy-ssl
    required: false
    choices:
      - enabled
      - disabled
      - default-value
    default: none
  proxySslPassthrough:
    description:
      - ClientSSL Option
      - tmsh = proxy-ssl-passthrough
    required: false
    choices:
      - enabled
      - disabled
      - default-value
    default: none



10yy
  option:
    description:
      - ClientSSL Option
      - tmsh = 
    required: false
    choices:
      - enabled
      - disabled
      - default-value
    default: none



'''

try:
    from f5.bigip import ManagementRoot
    from icontrol.session import iControlUnexpectedHTTPError
    HAS_F5SDK = True
except ImportError:
    HAS_F5SDK = False

CHOICES = ['enabled', 'disabled', 'default-value']
BOOL_CHOICES = ['true', 'True', 'false', 'False', 'default-value']

class BigIpSslProfile(object):
    def __init__(self, **kwargs):
        self.api = ManagementRoot(kwargs['server'],
                                  kwargs['user'],
                                  kwargs['password'],
                                  port=kwargs['server_port'])
        if kwargs['profile_type'] == 'clientssl':
            self.apiroot = self.api.tm.ltm.profile.client_ssls.client_ssl
            profile_options = [
                'alertTimeout',
                'allowDynamicRecordSizing',
                'allowExpiredCrl',
                'allowNonSsl',
                'authenticate',
                'authenticateDepth',
                'caFile',
                'cacheSize',
                'cacheTimeout',
                'cert',
                'certExtensionIncludes',
                'certLifespan',
                'certLookupByIpaddrPort',
                'chain',
                'ciphers',
                'clientCertCa',
                'crlFile',
                'defaultsFrom',
                'description',
                'destinationIpBlacklist',
                'destinationIpWhitelist',
                'forwardProxyBypassDefaultAction',
                'genericAlert',
                'handshakeTimeout',
                'hostnameBlacklist',
                'hostnameWhitelist',
                'key',
                'maxActiveHandshakes',
                'maxAggregateRenegotiationPerMinute',
                'maxRenegotiationsPerMinute',
                'maximumRecordSize',
                'modSslMethods',
                'mode',
                'name',
                'passphrase',
                'peerCertMode',
                'peerNoRenegotiateTimeout',
                'proxyCaCert',
                'proxyCaKey',
                'proxyCaPassphrase',
                'proxySsl',
                'proxySslPassthrough',
                'renegotiateMaxRecordDelay',
                'renegotiatePeriod',
                'renegotiateSize',
                'renegotiation',
                'retainCertificate',
                'secureRenegotiation',
                'serverName',
                'sessionMirroring',
                'sessionTicket',
                'sessionTicketTimeout',
                'sniDefault',
                'sniRequire',
                'sourceIpBlacklist',
                'sourceIpWhitelist',
                'sslForwardProxy',
                'sslForwardProxyBypass',
                'sslSignHash',
                'strictResume',
                'tmOptions',
                'uncleanShutdown',
            ]
        elif kwargs['profile_type'] == 'serverssl':
            self.apiroot = self.api.tm.ltm.profile.server_ssls.server_ssl
            profile_options = ['name']
        self.params = {}
        for o in profile_options:
            if o in kwargs and kwargs[o]:
                self.params[o] = kwargs[o]
        self.kwargs = kwargs

    def flush(self):
        result = {'changed': False}
        if self.kwargs['state'] == 'present':
            if self.profile_exists():
                r = self.profile_modify()
                if r:
                    result['changed'] = True
            else:
                r = self.profile_create()
                if r:
                    result['changed'] = True
        else:
            pass
        return result

    def profile_create(self):
        self.apiroot.create(**self.params)

    def profile_delete(self):
        p = self.apiroot.load(name=self.params['name'])
        p.delete()

    def profile_exists(self):
        return self.apiroot.exists(name=self.params['name'])

    def profile_modify(self):
        p = self.apiroot.load(name=self.params['name'])
        for o in self.params.keys():
            if self.params[o] == p.__dict__[o]:
                del(self.params[o])
        if self.params:
            p.modify(**self.params)
            return True

def main():
    argument_spec = f5_argument_spec()
    meta_args = dict(
        alertTimeout=dict(type='str'),
        allowDynamicRecordSizing=dict(type='str', choices=CHOICES),
        allowExpiredCrl=dict(type='str', choices=CHOICES),
        allowNonSsl=dict(type='str', choices=CHOICES),
        authenticate=dict(type='str', choices=['once', 'always']),
        authenticateDepth=dict(type='str'),
        caFile=dict(type='str'),
        cacheSize=dict(type='str'),
        cacheTimeout=dict(type='str'),
        cert=dict(type='str'),
        certExtensionIncludes=dict(type='list'),
        certLifespan=dict(type='str'),
        certLookupByIpaddrPort=dict(type='str', choices=CHOICES),
        chain=dict(type='str'),
        ciphers=dict(type='str'),
        clientCertCa=dict(type='str'),
        crlFile=dict(type='str'),
        defaultsFrom=dict(type='str'),
        destinationIpBlacklist=dict(type='str'),
        destinationIpWhitelist=dict(type='str'),
        forwardProxyBypassDefaultAction=dict(type='str', choices=['intercept',
                                                                  'bypass']),
        genericAlert=dict(type='str', choices=CHOICES),
        handshakeTimeout=dict(type='str'),
        hostnameBlacklist=dict(type='str'),
        hostnameWhitelist=dict(type='str'),
        key=dict(type='str'),
        maxActiveHandshakes=dict(type='str'),
        maxAggregateRenegotiationPerMinute=dict(type='str'),
        maxRenegotiationsPerMinute=dict(type='str'),
        maximumRecordSize=dict(type='str'),
        modSslMethods=dict(type='str', choices=CHOICES),
        mode=dict(type='str', choices=CHOICES),
        name=dict(type='str', required=True),
        passphrase=dict(type='str'),
        peerCertMode=dict(type='str', choices=['ignore',
                                               'require',
                                               'request',
                                               'default-value']),
        peerNoRenegotiateTimeout=dict(type='str'),
        proxyCaCert=dict(type='str'),
        proxyCaKey=dict(type='str'),
        proxyCaPassphrase=dict(type='str'),
        proxySsl=dict(type='str', choices=CHOICES),
        proxySslPassthrough=dict(type='str', choices=CHOICES),
        renegotiateMaxRecordDelay=dict(type='str'),
        renegotiatePeriod=dict(type='str'),
        renegotiation=dict(type='str', choices=CHOICES),
        retainCertificate=dict(type='str', choices=BOOL_CHOICES),
        secureRenegotiation=dict(type='str', choices=['default-value',
                                                      'request',
                                                      'require',
                                                      'require-strict']),
        serverName=dict(type='str'),
        sessionMirroring=dict(type='str', choices=CHOICES),
        sessionTicket=dict(type='str', choices=CHOICES),
        sessionTicketTimeout=dict(type='str'),
        sniDefault=dict(type='str', choices=BOOL_CHOICES),
        sniRequire=dict(type='str', choices=BOOL_CHOICES),
        sourceIpBlacklist=dict(type='str'),
        sourceIpWhitelist=dict(type='str'),
        sslForwardProxy=dict(type='str', choices=CHOICES),
        sslForwardProxyBypass=dict(type='str', choices=CHOICES),
        sslSignHash=dict(type='str', choices=['any',
                                              'sha1',
                                              'sha256',
                                              'sha384',
                                              'default-value']),
        strictResume=dict(type='str', choices=CHOICES),
        tmOptions=dict(type='list'),
        uncleanShutdown=dict(type='str', choices=CHOICES),
        profile_type=dict(type='str', choices=['clientssl',
                                               'serverssl'])
    )
    argument_spec.update(meta_args)
    module = AnsibleModule(argument_spec=argument_spec)
    try:
        obj = BigIpSslProfile(**module.params)
        result = obj.flush()
    except F5ModuleError as e:
        module.fail_json(msg=str(e))
    module.exit_json(**result)


from ansible.module_utils.basic import *
from ansible.module_utils.f5 import *

if __name__ == '__main__':
    main()
