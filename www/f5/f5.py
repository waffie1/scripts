#!/usr/bin/python


#import mybigsuds as bigsuds
import bigsuds
import sys
sys.path.append("/home/www/f5")
import db
import config
username = config.f5username
password = config.f5password


#Classes
class Common_ltm(object):
    def __init__(self, **kw):
        self.cluster_name = ''
        self.hostname = ''
        self.version = ''
        self.username = ''
        self.password = ''
        self.bigip_obj = ''
        self.pools = ''
        self.virtual_servers = ''
        for k in kw.keys():
            if self.__dict__.has_key(k):
                self.__dict__[k] = kw[k]

    def connect(self):
        self.bigip_obj = bigsuds.BIGIP(
                hostname = self.hostname,
                username = self.username,
                password = self.password
                )
    def get_default_pool_name(self, virtual_servers):
        return self.bigip_obj.LocalLB.VirtualServer.get_default_pool_name(
            virtual_servers)

    def pool_get_list(self):
        self.pools = self.bigip_obj.LocalLB.Pool.get_list()
        return self.pools

    def vs_get_list(self):
        self.virtual_servers = self.bigip_obj.LocalLB.VirtualServer.get_list()
        return self.virtual_servers

class V11ltm(Common_ltm):
    def get_pool_members(self, pools):
        if type(pools) == str:
            pools = [pools]
        return self.bigip_obj.LocalLB.Pool.get_member_v2(pools)
    def get_member_address(self, pools, members):
        return self.bigip_obj.LocalLB.Pool.get_member_address(
            pools, members)
    def get_member_session_status(self, pools, members):
        return self.bigip_obj.LocalLB.Pool.get_member_session_status(
            pools, members)
    def get_member_monitor_status(self, pools, members):
        return self.bigip_obj.LocalLB.Pool.get_member_monitor_status(
            pools, members)
    def get_node_address(self, nodes):
        if type(nodes) == str:
            nodes = [nodes]
        return self.bigip_obj.LocalLB.NodeAddressV2.get_address(nodes)
    def get_node_list(self):
        return self.bigip_obj.LocalLB.NodeAddressV2.get_list()
    def get_node_monitor_status(self, nodes):
        if type(nodes) == str:
            nodes = [nodes]
        return self.bigip_obj.LocalLB.NodeAddressV2.get_monitor_status(nodes)
    def get_node_session_status(self, nodes):
        if type(nodes) == str:
            nodes = [nodes]
        return self.bigip_obj.LocalLB.NodeAddressV2.get_session_status(nodes)
    def toggle_pool_members(self, pools, members, states):
        self.bigip_obj.LocalLB.Pool.set_member_session_enabled_state(
            pools, members, states)
    def toggle_node_session(self, nodes, states):
        if str(nodes):
            nodes = [nodes]
        if str(states):
            states = [states]
        self.bigip_obj.LocalLB.NodeAddressV2.set_session_enabled_state(
            nodes, states)
    def toggle_node_monitor(self, nodes, states):
        if str(nodes):
            nodes = [nodes]
        if str(states):
            states = [states]
        self.bigip_obj.LocalLB.NodeAddressV2.set_monitor_state(
            nodes, states)



#Functions
def bigip(hagroup_id):
    #TODO Check other nodes in cluster and update active node if 
    #primary is no longer primary
    sql = "select hagroup.description, ltm.name, version " \
          "from ltm left join hagroup on hagroup.ID = hagroup_ID "\
          "where hagroup.ID = %s and active_ID = ltm.ID"
    result = db.fetchall(sql,hagroup_id)
    hostname = result[0]['name']
    b = bigip_connect(hostname)
    #Verify this LTM is active
    state = b.System.Failover.get_failover_state()
    if state == "FAILOVER_STATE_STANDBY":
        sql = "select hagroup.description, ltm.name, version, ltm.ID " \
              "from ltm left join hagroup on hagroup.ID = hagroup_ID "\
              "where hagroup.ID = %s and active_ID != ltm.ID"
        result = db.fetchall(sql,hagroup_id)
        hostname = result[0]['name']
        ltm_ID = result[0]['ID']
        b = bigip_connect(hostname)
        state = b.System.Failover.get_failover_state()
        if not state == "FAILOVER_STATE_ACTIVE":
            return False
        #Update DB with new active status
        else:
            sql = "update hagroup set active_id = %s where ID=%s"
            result = db.insert(sql, (ltm_ID, hagroup_id))
    version = result[0]['version']
    cluster_name = result[0]['description']
    if version.startswith('BIG-IP_v11'):
        return V11ltm(bigip_obj=b,
                      version=11,
                      cluster_name=cluster_name,
                      hostname=hostname)
    else:
        return V10ltm(bigip_obj=b,version=10)

def bigip_connect(hostname):
    b = bigsuds.BIGIP(
        hostname = hostname,
        username = username,
        password = password,
        cachedir = '/home/www/f5/cache'
    )
    return b

def get_hagroups():
    sql = "select id, name, description from hagroup";
    result = db.fetchall(sql)
    return result
