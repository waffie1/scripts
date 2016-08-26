#!/usr/bin/python

from bottle import abort, default_app, route, request, response, template
from bottle import TEMPLATE_PATH, redirect, app, hook
from beaker.middleware import SessionMiddleware

session_opts = {
    'session.type' : 'file',
    'session.data_dir' : '/home/www/f5/sessions',
    'cookie_expires' : True,
    'session.auto' : True
}
myapp = SessionMiddleware(app() , session_opts)

TEMPLATE_PATH.insert(0,"/home/www/f5/views")
import re
import sys
sys.path.append("/home/www/f5")
import f5
import db
import myhtml

rootpath = "/f5"

#Friendly names for status
status_desc = {'SESSION_STATUS_ENABLED' : 'ENABLED',
               'SESSION_STATUS_FORCED_DISABLED' : 'DISABLED',
               'SESSION_STATUS_ADDRESS_DISABLED' : 'Host Disabled',
               'MONITOR_STATUS_UP' : 'UP',
               'MONITOR_STATUS_CHECKING' : 'Checking',
               'MONITOR_STATUS_DOWN' : 'DOWN',
               'MONITOR_STATUS_ADDRESS_DOWN' : 'DOWN',
               'MONITOR_STATUS_FORCED_DOWN' : 'DISABLED',
               'MONITOR_STATUS_UNCHECKED' : 'UNKNOWN'
               }

#Dict to color statuses 
colorize = {'ENABLED' : ['white', 'green'],
            'UP' : ['white', 'green'],
            'DISABLED' : ['white', 'red'],
            'DOWN' : ['red', 'white'],
            'Checking' : ['white', 'black'],
            'UNKNOWN' : ['white', 'orange'],
            'Disabled' : ['white', 'black'],
            'Host Disabled' : ['white', 'black']
           }



@hook('before_request')
def setup_request():
    request.session = request.environ.get('beaker.session')

@route('/test')
def testcount():
    request.session['count'] = request.session.get('count', 0) + 1
    request.session.save()
    return str(request.session['count'])
@route('/')
def home():
    #Main Homepage
    user = request.auth[0]
    #cap first letter in username, lowercase the rest
    firstname = user.split('.')[0].title()
    hagroups = f5.get_hagroups()
    hagroup_links = ""
    for x in hagroups:
        hagroup_links += myhtml.link(txt = "%s" % x['description'], 
            link = '/f5/poolmain?ha_id=%s' % x['id'], br=True)
    right = template('home_right', name=firstname, hagroups=hagroup_links)
    left = "&nbsp"
    return makepage(user=user, right=right, left=left)

@route('/admin')
def admin():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    left = template('admin_left')
    right = ''
    return makepage(user=user, right=right, left=left)

@route('/admin/ltm_make_primary', method='POST')
def admin_ltm_make_primary():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    b_id = request.forms.get('b_id')
    ha_id = request.forms.get('ha_id')
    if not b_id and ha_id:
        abort(404, "Missing Form Data")
    sql = "update hagroup set active_id = %s where ID = %s"
    result = db.insert(sql, (b_id, ha_id))
    sql = "select ltm.name as ltmname, hagroup.name as haname from ltm " \
          "join hagroup on hagroup_ID = hagroup.ID where ltm.ID = %s"
    result = db.fetchall(sql, b_id)
    logit("LTM: %s promoted to primary in HAGroup %s by %s" % 
         (result[0]['ltmname'], result[0]['haname'], user))
    request.session['msg'] = "BIGIP Promoted to Primary"
    request.session.save()
    redirect('/f5/admin/ltm', code=303)


@route('/admin/ltm')
def admin_ltm():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    sql = "select * from hagroup order by name"
    hagroups = db.fetchall(sql)
    select_options = ''
    hagroup_tables = ''
    for c in hagroups:
        select_options += template('select_options', 
                                      value=c['ID'],
                                      text=c['name'])
        t = myhtml.Table()
        t.caption = "%s %s" % (c['name'], c['description'])
        t.header(['Hostname', 'Primary', 'Delete'])
        #if active_id is 0, then no hosts have been added to the hagroup yet
        sql = "select * from ltm where hagroup_ID = %s"
        ltms = db.fetchall(sql, c['ID'])
        if not ltms:
            t.row(['NONE', 'N/A', 'N/A'])
        else:
            for b in ltms:
                if c['active_id'] == b['ID']:
                    primary = "YES"
                else:
                    f = myhtml.FormButton(
                               action='/f5/admin/ltm_make_primary',
                               button_name = "PROMOTE",
                               button_text = "PROMOTE")
                    f.add_field(ftype='HIDDEN', 
                                fname='b_id', 
                                fvalue=b['ID'])
                    f.add_field(ftype='HIDDEN', 
                                fname='ha_id', 
                                fvalue=c['ID'])
                    primary = f.render()
                delete = 'DELETE'
                t.row([b['name'], primary, delete])
        hagroup_tables += template('hagroup_tables', 
                                   hagroup_table = t.render())
    left = template('admin_left')
    right = template('ltm.tpl',
                     select_options=select_options,
                     hagroup_tables=hagroup_tables)
    return makepage(user=user, right=right, left=left)

@route('/admin/hagroup_add', method='POST')
def admin_hagroup_add():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    name = request.forms.get('name')
    description = request.forms.get('description')
    if not (name and description):
        abort(404, "Form data missing from request")
    else:
        sql = "select name from hagroup"
        usednames = db.getcolumn(sql)
        sql = "select description from hagroup"
        useddesc = db.getcolumn(sql)
        if name in usednames:
            request.session['msg'] = "The name %s is alread in use" % name
        elif description in useddesc:
            request.session['msg'] = "The description %s is alread in use" \
                                     % description
        else:
            sql = "insert into hagroup (name, description, active_id) " \
                  "values (%s, %s, 0)" 
            db.insert(sql, (name, description))
            request.session['msg'] = "Cluster %s Created" % name
        logit("HAGroup %s created by %s" % (name, user))
    redirect('/f5/admin/ltm', code=303)

@route('/admin/groups')
def admin_users():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    #Get a list of usernames, so we can hide groups that match a username
    sql = "select username from users"
    usernames = db.getcolumn(sql)
    #Get a list of groups
    sql = "select * from groups"
    result = db.fetchall(sql)
    t = myhtml.Table()
    t.caption = "Group Management"
    t.width = 400
    t.header(['Groupname', 'Delete'])
    #First field in Table, username
    for g in result:
        if g['groupname'] in usernames:
            continue
        username = myhtml.link(txt=g['groupname'], 
                    link = '/f5/admin/group_perm?g_id=%s' %  g['ID'])
        #seconf table field, delete option
        f = myhtml.FormButton(action='/f5/admin/group_del',
                            button_name = "DELETE",
                            button_text = "DELETE")
        f.add_field(ftype='HIDDEN', fname='g_id', fvalue=g['ID'])
        #set delete field button html
        delete = f.render()
        t.row([username, delete])
    group_table = t.render()
    right = template('group_page', group_table=group_table)
    left = template('admin_left')
    return makepage(user=user, right=right, left=left)

@route('/admin/group_add', method='POST')
def admin_group_add():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    group_to_add = request.forms.get('groupname')
    if not group_to_add:
        request.session['msg'] = "No groupname entered"
    else:
        #verify username matches standard characters
        if not re.match('^[a-zA-Z0-9\.\-\_]+$', group_to_add):
            request.session['msg'] = "Invalid groupname %s " % group_to_add
        else:
            #check if username is already in the db
            sql =  "select ID from groups where groupname = %s"
            result = db.getfield(sql, group_to_add)
            if result:
                right = "Group %s already exists" % group_to_add
            else:
                #create user in users table
                sql = "INSERT INTO groups (groupname) values (%s)"
                g_ID = db.insert(sql, group_to_add)
                request.session['msg'] = "Group %s created" % group_to_add
        logit("Group %s created by %s" % (group_to_add, user))
    request.session.save()
    redirect('/f5/admin/groups', code=303)

@route('/admin/group_del', method='POST')
def admin_group_del():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    group_to_del = request.forms.get('g_id')
    if not group_to_del:
        request.session['msg'] = "Invalid group ID in request"
    else:
        #Get group name for status message
        sql = "select groupname from groups where ID = %s"
        groupname = db.getfield(sql, group_to_del)
        #Safety so Admin group doesn't get delted
        if groupname == 'administrator':
            abort(403, "Cannot delete administrator group")
        #delete group membership
        sql = "delete from users_groups where groups_ID = %s"
        result = db.insert(sql, group_to_del)
        #delete group permissions
        sql = "delete from groups_pools where groups_ID = %s"
        result = db.insert(sql, group_to_del)
        #delete group
        sql = "delete from groups where ID = %s"
        result = db.insert(sql, group_to_del)
        request.session['msg'] = "Group %s deleted" % groupname
        logit("Group %s deleted by %s" % (groupname, user))
    request.session.save()
    redirect('/f5/admin/groups', code=303)

@route('/admin/group_member_change', method='POST')
def group_member_change():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    u_id = request.forms.get('u_id')
    g_id = request.forms.get('g_id')
    action = request.forms.get('action')
    if not (u_id and g_id and action):
        abort(404, "Missing form data in request")
    #Get names for status message
    sql = "select username from users where ID = %s"
    username = db.getfield(sql, u_id)
    sql = "select groupname from groups where ID = %s"
    groupname = db.getfield(sql, g_id)
    if action == "add":
        sql = "insert into users_groups (users_ID, groups_ID) values " \
              "(%s, %s)"
        result = db.insert(sql, (u_id, g_id))
        request.session['msg'] = "Added %s to group %s" % (username, groupname)
        logit("User %s added to Group %s by %s" % (username, groupname, user))
    else:
        sql = "delete from users_groups where users_ID = %s and " \
              "groups_ID = %s"
        result = db.insert(sql, (u_id, g_id))
        request.session['msg'] = "Deleted %s from group %s" % (
                                 username, groupname)
        logit("User %s deleted from Group %s by %s" % (username,
                                                       groupname, user))
    request.session.save()
    redirect (request.headers.get('Referer'), code=303)

@route('/admin/group_perm')
def admin_group_perm():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    g_id = request.query.get('g_id')
    #Get groupname for display
    sql = "select groupname from groups where ID = %s"
    groupname = db.getfield(sql, g_id)
    if not g_id:
        abort(404, "Group ID missing from query string")

    sql = "select ID, username from users"
    users = db.fetchall(sql)
    #Put usernames in a set, and create a dictionary with the username
    #as the key and they ID as a value so we can look them up for the form
    u_set = set()
    usernames_ID = {}
    for u in users:
        u_set.add(u['username'])
        usernames_ID[u['username']] = u['ID']
    #Get usernames that are a member of the group
    sql = "select username from users " \
           "join users_groups on users.ID = users_ID " \
           "where groups_ID = %s"
    groupmembers = db.getcolumn(sql, g_id)
    gm_set = set(groupmembers)
    #Create Table of group members
    t = myhtml.Table()
    t.caption = "Members of Group"
    t.header(['Username', 'Remove'])
    for u in u_set & gm_set:
        f = myhtml.FormButton(action='/f5/admin/group_member_change',
                              button_name = "REMOVE",
                              button_text = "REMOVE")
        f.add_field(ftype='HIDDEN', fname='u_id', fvalue=usernames_ID[u])
        f.add_field(ftype='HIDDEN', fname='g_id', fvalue=g_id)
        f.add_field(ftype='HIDDEN', fname='action', fvalue='delete')
        action = f.render()
        user_link = myhtml.link(txt=u, link='/f5/admin/user_perm?u_id=%s'
                                % usernames_ID[u])
        t.row([user_link,action]) 
    members = t.render()
    #Create Table of group non-members
    t = myhtml.Table()
    t.caption = "Non-Members of Group"
    t.header(['Username', 'Add'])
    for u in u_set - gm_set:
        f = myhtml.FormButton(action='/f5/admin/group_member_change',
                              button_name = "ADD",
                              button_text = "ADD")
        f.add_field(ftype='HIDDEN', fname='u_id', fvalue=usernames_ID[u])
        f.add_field(ftype='HIDDEN', fname='g_id', fvalue=g_id)
        f.add_field(ftype='HIDDEN', fname='action', fvalue='add')
        action = f.render()
        user_link = myhtml.link(txt=u, link='/f5/admin/user_perm?u_id=%s'
                                % usernames_ID[u])
        t.row([user_link,action]) 
    nonmembers = t.render()
    #Create table of pools this group has permission too
    sql = "select pools.ID, pools.name, hagroup.name as hagroup_name " \
          "from groups_pools join pools on pools_ID = pools.ID " \
          "join hagroup on hagroup_ID = hagroup.ID where groups_ID=%s " \
          "order by pools.name"
    pool_perm = db.fetchall(sql, g_id)
    t = myhtml.Table(caption="Pool Permissions for Group")
    t.header(['Group Name', 'HA Group', 'Action'])
    if pool_perm:
        for p in pool_perm:
            f = myhtml.FormButton(action='/f5/admin/pool_group_change',
                                  button_name = "remove",
                                  button_text = "REMOVE")
            f.add_field(ftype='HIDDEN', fname='g_id', fvalue=g_id)
            f.add_field(ftype='HIDDEN', fname='p_id', fvalue=p['ID'])
            f.add_field(ftype='HIDDEN', fname='action', fvalue='del')
            action = f.render()
            pool_link = myhtml.link(txt=p['name'], link='/f5/admin/pool_perm?' \
                                    'p_id=%s' % p['ID'])
            t.row([pool_link, p['hagroup_name'], action])
    pool_table = t.render()
    right = template('group_perm_page',
                     groupname=groupname,
                     member_table=members,
                     nonmember_table=nonmembers,
                     group_pool_table=pool_table)
    left = template('admin_left')
    return makepage(user=user, right=right, left=left)

@route('/admin/ltm_add', method='POST')
def admin_ltm_add():
    valid_versions = ['BIG-IP_v11']
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    ltmname = request.forms.get('ltmname')
    hagroup_id = request.forms.get('hagroup_id')
    version = request.forms.get('version')
    if not (ltmname and hagroup_id and version):
        abort(404, "Missing form data in request")
    if version not in valid_versions:
        abort(404, "Invalid version in form data")
    #verify name is not already in use
    sql = "select ID from ltm where name = %s"
    result = db.getfield(sql, ltmname)
    if result:
        request.session['msg'] = "Name %s alread in use" % ltmname
    #Create ltm in db
    else:
        sql = "insert into ltm (name, version, hagroup_id) " \
              "values (%s, %s, %s)"
        result = db.insert(sql, (ltmname, version, hagroup_id))
        request.session['msg'] = "F5 LTM %s added" % ltmname
        #TODO lookup hagroup name instead of ID
        logit("LTM %s added to HAGroup %s by %s" % (ltmname, hagroup_id,
                                                    user))
    request.session.save()
    redirect('/f5/admin/ltm', code=303)

@route('/admin/pool_add', method='POST')
def admin_pool_add():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    ha_id = request.forms.get('ha_id')
    pool_name= request.forms.get('pool_name')
    if not ha_id and pool_name:
        abort(404, "Form data missing from request")
    sql = "select ID from pools where name = %s and hagroup_id = %s"
    result = db.getfield(sql, (pool_name, ha_id))
    if result:
        request.session['msg'] = "Pool %s already added to the database" \
                                 % pool_name
    else:
        sql = "insert into pools (name, hagroup_id) values (%s, %s)"
        result = db.insert(sql, (pool_name, ha_id))
        request.session['msg'] = "Pool %s added to the database" % pool_name
        logit("Pool %s added to F5 database by %s" % (pool_name, user))
    request.session.save()
    redirect (request.headers.get('Referer'), code=303)

@route('/admin/pool_del', method='POST')
def admin_pool_del():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    ha_id = request.forms.get('ha_id')
    pool_name= request.forms.get('pool_name')
    if not ha_id and pool_name:
        abort(404, "Form data missing from request")
    sql = "select ID from pools where name = %s and hagroup_id = %s"
    p_id = db.getfield(sql, (pool_name, ha_id))
    if not p_id:
        request.session['msg'] = "Pool %s is not in the database" \
                                 % pool_name
    else:
        sql = "delete from users_pools where pools_ID = %s"
        result = db.insert(sql, p_id)
        sql = "delete from groups_pools where pools_ID = %s"
        result = db.insert(sql, p_id)
        sql = "delete from pools where name = %s and hagroup_id = %s"
        result = db.insert(sql, (pool_name, ha_id))
        request.session['msg'] = "Pool %s deleted from the database" % pool_name
        logit("Pool %s deleted from F5 database by %s" % (pool_name, user))
    request.session.save()
    redirect (request.headers.get('Referer'), code=303)


@route('/admin/pools')
def admin_pools():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    #pools = ""
    #sql = "select * from hagroup"
    #hagroups = db.fetchall(sql)
    #for c in hagroups:
    #    pools += myhtml.link(txt='&nbsp' + c['name'],
    #                         link='/f5/admin/pools_manage?ha_id=%s' % c['ID'])
    #left = template('admin_left_pools', pools=pools)
    left = template('admin_left_pools', pools=menu_left_hagroup())
    right = 'F5 LTM Pools'
    return makepage(user=user, right=right, left=left)


@route('/admin/pool_group_change', method='POST')
def admin_pool_group_change():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    g_id = request.forms.get('g_id')
    p_id = request.forms.get('p_id')
    action = request.forms.get('action')
    if not (g_id and p_id and action):
        abort (404, "Form data missing from request")
    sql = "select groupname from groups where ID = %s"
    groupname = db.getfield(sql, g_id)
    sql = "select name from pools where ID = %s"
    poolname = db.getfield(sql, p_id)
    sql = "select groups_ID from groups_pools where groups_ID = %s " \
          "and pools_ID = %s"
    in_db = db.getfield(sql, (g_id, p_id))
    if action == 'add':
        if in_db:
            request.session['msg'] = "Group %s already has permissions to " \
                                     "Pool %s" % (groupname, poolname)
        else:
            sql = "insert into groups_pools (groups_ID, pools_ID) " \
                  "values (%s, %s)"
            result = db.insert(sql, (g_id, p_id))
            request.session['msg'] = "Added permission for group %s to pool " \
                                     "%s " % (groupname, poolname)
            logit("Permission for group %s to pool %s added by %s" %
                  (groupname, poolname, user))
    if action == 'del':
        if not in_db:
            request.session['msg'] = "Group %s doesn't have permissions to " \
                                     "Pool %s.  Nohing to do" \
                                      % (groupname, poolname)
        else:
            sql = "delete from groups_pools where groups_ID = %s and " \
                  "pools_ID = %s"
            result = db.insert(sql, (g_id, p_id))
            request.session['msg'] = "Removed permission for group %s " \
                                     "from pool %s " % (groupname, poolname)
            logit("Permission for group %s to pool %s removed by %s" %
                  (groupname, poolname, user))
    request.session.save()
    redirect (request.headers.get('Referer'), code=303)


@route('/admin/pools_manage')
def admin_pools_manage():
    #TODO Pools not added should not have hyperlinks
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    ha_id = request.query.get('ha_id')
    if not ha_id:
        abort(404, "Cluster ID missing from query string")
    b = f5.bigip(ha_id)
    sql = "select name from pools where hagroup_ID = %s"
    db_pools = set(db.getcolumn(sql, ha_id))
    ltm_pools = set(b.pool_get_list())
    sql = "select name from hagroup where ID = %s"
    ha_name = db.getfield(sql, ha_id)
    t = myhtml.Table(caption="Pools for HA Group %s" % ha_name)
    t.width = 600
    t.header(['Pool Name', 'Action'])
    for x in sorted(db_pools | ltm_pools):
        sql = "select ID from pools where name = %s and hagroup_ID = %s"
        p_id = db.getfield(sql, (x, ha_id))
        pool_name = myhtml.link(txt=x,
                                link='/f5/admin/pool_perm?p_id=%s' % p_id)
        if x in (db_pools & ltm_pools):
            f = myhtml.FormButton(action='/f5/admin/pool_del',
                                  button_name = 'del',
                                  button_text = 'Remove')
            f.add_field(ftype='HIDDEN',
                        fname='pool_name',
                        fvalue = x)
            f.add_field(ftype='HIDDEN',
                        fname='ha_id',
                        fvalue=ha_id)
            action = f.render()
            t.row([pool_name, action])
        elif x in (ltm_pools - db_pools):
            f = myhtml.FormButton(action='/f5/admin/pool_add',
                                  button_name = 'add',
                                  button_text = 'Add')
            f.add_field(ftype='HIDDEN',
                        fname='pool_name',
                        fvalue = x)
            f.add_field(ftype='HIDDEN',
                        fname='ha_id',
                        fvalue=ha_id)
            action = f.render()
            t.row([pool_name, action])
        elif x in (db_pools - ltm_pools):
            f = myhtml.FormButton(action='/f5/admin/pool_del',
                                  button_name = 'del',
                                  button_text = 'Remove')
            f.add_field(ftype='HIDDEN',
                        fname='pool_name',
                        fvalue = x)
            f.add_field(ftype='HIDDEN',
                        fname='ha_id',
                        fvalue=ha_id)
            action = f.render()
            pool_name = myhtml.TableField(text=x)
            pool_name.color = 'red'
            t.row([pool_name, action])
    right = template('pools_manage_right', pool_table=t.render())
    left = template('admin_left_pools', pools=menu_left_hagroup())
    return makepage(user=user, right=right, left=left)

@route('/admin/pool_perm')
def admin_pool_perm():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    p_id = request.query.get('p_id')
    if not p_id:
        abort(404, "Data missing from query string")
    #Get all users from db
    sql = "select * from users"
    users = db.fetchall(sql)
    #Get pool name
    sql = "select pools.name, hagroup.name as hagroup_name from pools " \
          "join hagroup on hagroup_ID = hagroup.ID where pools.ID = %s"
    result = db.fetchall(sql, p_id)
    poolname = result[0]['name']
    hagroup_name = result[0]['hagroup_name']
    #Get a list of users with permissions
    sql = "select username from pools " \
          "join users_pools on pools.ID = pools_ID " \
          "join users on users_ID = users.ID " \
          "where pools.ID = %s"
    users_with_perm = db.getcolumn(sql, p_id)
    #Begin User permission table
    t = myhtml.Table(caption="User Pool Permissions")
    t.header(['Username', 'User Permission', 'Group Permission', 'Action'])
    for u in users:
        user_link = myhtml.link(txt = u['username'],
                                link = '/f5/admin/user_perm?u_id=%s' %
                                      u['ID'])
        #Get a list of users who have permission via a group
        sql = "select username from users " \
              "join users_groups on users.ID = users_ID " \
              "join groups on users_groups.groups_ID = groups.ID " \
              "join groups_pools on groups.ID = " \
              "groups_pools.groups_ID " \
              "join pools on pools_ID = pools.ID " \
              "where pools.ID = %s"
        users_with_group_perm = db.getcolumn(sql, p_id)
        if u['username'] in users_with_group_perm:
            groupperm = "YES"
        else:
            groupperm = "NO"
        if u['username'] in users_with_perm:
            f = myhtml.FormButton(action='/f5/admin/pool_user_change',
                                  button_name = "remove",
                                  button_text = "REMOVE")
            f.add_field(ftype='HIDDEN', fname='u_id', fvalue=u['ID'])
            f.add_field(ftype='HIDDEN', fname='p_id', fvalue=p_id)
            f.add_field(ftype='HIDDEN', fname='action', fvalue='del')
            action = f.render()
            t.row([user_link, 'YES', groupperm, action])
        else:
            f = myhtml.FormButton(action='/f5/admin/pool_user_change',
                                  button_name = "add",
                                  button_text = "ADD")
            f.add_field(ftype='HIDDEN', fname='u_id', fvalue=u['ID'])
            f.add_field(ftype='HIDDEN', fname='p_id', fvalue=p_id)
            f.add_field(ftype='HIDDEN', fname='action', fvalue='add')
            action = f.render()
            t.row([user_link, 'NO', groupperm, action])
    user_perm_table = t.render()
    #Finished with User Permissions
    #Begin Group permission Table
    #Get all groups from db
    t = myhtml.Table(caption="Group Pool Permissions")
    t.header(['Groupname', 'Permission', 'Action'])
    sql = "select * from groups"
    groups = db.fetchall(sql)
    #Get groups with permissions to pool
    sql = "select groupname from pools " \
          "join groups_pools on pools.ID = pools_ID " \
          "join groups on groups_ID = groups.ID " \
          "where pools.ID = %s"
    groups_with_perm = db.getcolumn(sql, p_id)
    for g in groups:
        group_link = myhtml.link(txt = g['groupname'],
                                link = '/f5/admin/group_perm?g_id=%s' %
                                      g['ID'])
        if g['groupname'] in groups_with_perm:
            f = myhtml.FormButton(action='/f5/admin/pool_group_change',
                                  button_name = "remove",
                                  button_text = "REMOVE")
            f.add_field(ftype='HIDDEN', fname='g_id', fvalue=g['ID'])
            f.add_field(ftype='HIDDEN', fname='p_id', fvalue=p_id)
            f.add_field(ftype='HIDDEN', fname='action', fvalue='del')
            action = f.render()
            t.row([group_link, 'YES', action])
        else:
            f = myhtml.FormButton(action='/f5/admin/pool_group_change',
                                  button_name = "add",
                                  button_text = "ADD")
            f.add_field(ftype='HIDDEN', fname='g_id', fvalue=g['ID'])
            f.add_field(ftype='HIDDEN', fname='p_id', fvalue=p_id)
            f.add_field(ftype='HIDDEN', fname='action', fvalue='add')
            action = f.render()
            t.row([group_link, 'NO', action])
    group_perm_table = t.render()
    right = template('pool_perm_page', poolname=poolname,
                                       hagroup_name=hagroup_name,
                                       user_perm_table=user_perm_table, 
                                       group_perm_table=group_perm_table)
    left = template('admin_left')
    return makepage(user=user, right=right, left=left)


@route('/admin/pool_user_change', method='POST')
def admin_pool_user_change():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    u_id = request.forms.get('u_id')
    p_id = request.forms.get('p_id')
    sql = "select username from users where ID = %s"
    username = db.getfield(sql, u_id)
    sql = "select name from pools where ID = %s"
    poolname = db.getfield(sql, p_id)
    action = request.forms.get('action')
    if not (u_id and p_id and action):
        abort (404, "Form data missing from request")
    sql = "select users_ID from users_pools where users_ID = %s " \
          "and pools_ID = %s"
    in_db = db.getfield(sql, (u_id, p_id))
    if action == 'add':
        if in_db:
            request.session['msg'] = "User %s already has permissions to " \
                                     "Pool %s" % (username, poolname)
        else:
            sql = "insert into users_pools (users_ID, pools_ID) values (%s, %s)"
            result = db.insert(sql, (u_id, p_id))
            request.session['msg'] = "Added permission for user %s to pool " \
                                     "%s " % (username, poolname)
            logit("Permission for user %s to pool %s added by %s" %
                  (username, poolname, user))
    if action == 'del':
        if not in_db:
            request.session['msg'] = "User %s doesn't have permissions to " \
                                     "Pool %s.  Nohing to do" \
                                      % (username, poolname)
        else:
            sql = "delete from users_pools where users_ID = %s and " \
                  "pools_ID = %s"
            result = db.insert(sql, (u_id, p_id))
            request.session['msg'] = "Removed permission for user %s " \
                                     "from pool %s " % (username, poolname)
            logit("Permission for user %s to pool %s removed by %s" %
                  (username, poolname, user))
    request.session.save()
    redirect (request.headers.get('Referer'), code=303)


@route('/admin/users')
def admin_users():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    right = template('user_page', user_table=user_table())
    left = template('admin_left')
    return makepage(user=user, right=right, left=left)

@route('/admin/user_add', method='POST')
def admin_user_add():
    #Add a user to the DB
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    user_to_add = request.forms.get('username')
    if not user_to_add:
        request.session['msg'] = "No username entered"
    else:
        #verify username matches standard characters
        if not re.match('^[a-zA-Z0-9\.\-\_]+$', user_to_add):
            request.session['msg'] = "Invalid username %s " % user_to_add
        else:
            #check if username is already in the db
            sql =  "select ID from users where username = %s"
            result = db.getfield(sql, user_to_add)
            if result:
                right = "User %s already exists" % user_to_add
            else:
                #create user in users table
                sql = "INSERT INTO users (username) values (%s)"
                u_ID = db.insert(sql, user_to_add)
                request.session['msg'] = "User %s created" % user_to_add
                logit("User %s created by %s" % (user_to_add, user))
    request.session.save()
    redirect('/f5/admin/users', code=303)

@route('/admin/user_del', method='POST')
def admin_user_del():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    user_to_del = request.forms.get('u_id')
    if not user_to_del:
        request.session['msg'] = "Invalid user ID in request"
    else:
        #Get username for status message
        sql = "select username from users where ID = %s"
        username = db.getfield(sql, user_to_del)
        #Delete user pool permissions
        sql = "delete from users_pools where users_ID = %s"
        result = db.insert(sql, user_to_del)
        #Delete user group membership
        sql = "delete from users_groups where users_ID = %s"
        result = db.insert(sql, user_to_del)
        #Delete user
        sql = "delete from users where ID = %s"
        result = db.insert(sql, user_to_del)
        request.session['msg'] = "User %s deleted" % username 
        logit("User %s delete by %s" % (username, user))
    request.session.save()
    redirect('/f5/admin/users', code=303)

@route('/admin/user_perm')
def admin_user_perm():
    user = request.auth[0]
    if not is_admin(user):
        abort(403, "Your account does not have Administrative privleges")
    u_id = request.query.u_id
    if not u_id:
        abort(404, "User ID Query String missing from request")
    #Get list of groups
    sql = "select * from groups order by groupname"
    groups = db.fetchall(sql)
    #Get a list of groups this user is a member of
    sql = "select groups.ID from groups join " \
          "users_groups on groups.ID = groups_ID where users_ID = %s"
    member_of = db.getcolumn(sql, u_id)
    #Get username for display
    sql = "select username from users where ID = %s"
    username = db.getfield(sql, u_id)
    t = myhtml.Table()
    t.caption = "Group Membership for %s" % username
    t.header(['GroupName', 'Member', 'Action'])
    for g in groups:
        if g['ID'] in member_of:
            member = "YES"
            f = myhtml.FormButton(action='/f5/admin/group_member_change',
                                  button_name = "REMOVE",
                                  button_text = "REMOVE")
            f.add_field(ftype='HIDDEN', fname='u_id', fvalue=u_id)
            f.add_field(ftype='HIDDEN', fname='g_id', fvalue=g['ID'])
            f.add_field(ftype='HIDDEN', fname='action', fvalue='delete')
            action = f.render()
        else:
            member = "NO"
            f = myhtml.FormButton(action='/f5/admin/group_member_change',
                                  button_name = "ADD",
                                  button_text = "ADD")
            f.add_field(ftype='HIDDEN', fname='u_id', fvalue=u_id)
            f.add_field(ftype='HIDDEN', fname='g_id', fvalue=g['ID'])
            f.add_field(ftype='HIDDEN', fname='action', fvalue='add')
            action = f.render()
        grouplink = myhtml.link(txt=g['groupname'],
                                link='/f5/admin/group_perm?g_id=%s' % g['ID'])
        t.row([grouplink, member, action])
    user_member_table = t.render()
    #Get pools that a user has direct permissions on
    sql = "select pools.ID, pools.name, hagroup.name as hagroup_name " \
          "from pools join users_pools on pools_ID = pools.ID "  \
          "join hagroup on hagroup_ID = hagroup.ID " \
          "where users_ID = %s order by pools.name"
    user_perm = db.fetchall(sql, u_id) 
    t = myhtml.Table(caption="User Permission")
    t.header(['Pool Name', 'HA Group', 'Action'])
    if user_perm:
        for u in user_perm:
            f = myhtml.FormButton(action='/f5/admin/pool_user_change',
                                  button_name = "remove",
                                  button_text = "REMOVE")
            f.add_field(ftype='HIDDEN', fname='u_id', fvalue=u_id)
            f.add_field(ftype='HIDDEN', fname='p_id', fvalue=u['ID'])
            f.add_field(ftype='HIDDEN', fname='action', fvalue='del')
            action = f.render()
            poollink = myhtml.link(txt=u['name'],
                                   link='/f5/admin/pool_perm?p_id=%s' % u['ID'])
            t.row([poollink, u['hagroup_name'], action])
    user_pool_table = t.render()
    #Get pools that the user has permission on via group membership
    sql = "select pools.ID, pools.name, hagroup_ID, " \
          "hagroup.name as hagroup_name from pools " \
          "join groups_pools on pools.ID = pools_ID " \
          "join groups on groups_pools.groups_ID = groups.ID " \
          "join users_groups on groups.ID = users_groups.groups_ID " \
          "join hagroup on hagroup_ID = hagroup.ID " \
          "where users_ID = %s order by pools.name "
    group_perm = db.fetchall(sql, u_id)
    t = myhtml.Table(caption="Group Permission")
    t.header(['Pool Name', 'HA Group'])
    if group_perm:
        for g in group_perm:
            poollink = myhtml.link(txt=g['name'],
                              link='/f5/admin/pool_perm?p_id=%s' % g['ID'])
            t.row([poollink, g['hagroup_name']])
    group_pool_table = t.render()
    right = template('user_perm_page',
                     username = username,
                     user_member_table=user_member_table,
                     user_pool_table=user_pool_table,
                     group_pool_table=group_pool_table)
    left = template('admin_left')
    return makepage(user=user, right=right, left=left)

@route('/logout')
def logout():
    abort(403, "You are logged out")

@route('/nodemain')
def nodemain():
    user = request.auth[0]
    hagroup_id = request.query.get('ha_id')
    left = left_node_menu(hagroup_id)
    right = "Pick a Node to Manage"
    return makepage(user=user, right=right, left=left)

@route('/node_manage')
def node_manage():
    #TODO pool names should be links
    #TODO Display status and buttons for each member?
    user = request.auth[0]
    nodename = request.query.get('n')
    hagroup_id = request.query.get('ha_id')
    partition = request.query.get('p')
    node = "/%s/%s" % (partition, nodename)
    if not all((nodename, hagroup_id, partition)):
        abort(404, "Data missing from query string")
    b = f5.bigip(hagroup_id)
    ltm_pools = b.pool_get_list()
    members = b.get_pool_members(ltm_pools)
    pools_with_node = []
    for k, v in enumerate(members):
        for n in v:
            if n['address'] == node:
                pools_with_node.append(ltm_pools[k])
    t = myhtml.Table(caption="Pools that %s is a member of" % node)
    t.width=600
    t.cellpadding=4
    t.header(['Pool Name', 'Permission'])
    has_all_perm = True
    for p in pools_with_node:
        sql = "select ID from pools where name = %s and hagroup_ID = %s"
        p_id = db.getfield(sql, (p, hagroup_id))
        if has_pool_perm(user, p_id):
            perm = "YES"
            poolname = myhtml.link(txt=p,
                                   link="/f5/pool_manage?p_id=%s" % p_id)
        else:
            poolname = p
            perm = "NO"
            has_all_perm = False
        t.row([poolname, perm])
    if has_all_perm:
        t2 = myhtml.Table()
        t2.width = 600
        t2.header(['Node Name', 'Node Address', 'Session Status', 
                  'Monitor Status', 'Action'])
        node_ipaddr = b.get_node_address(node)[0]
        node_ses_stat = b.get_node_session_status(node)[0]
        node_mon_stat = b.get_node_monitor_status(node)[0]
        s_stat = myhtml.TableField(text= status_desc[node_ses_stat])
        s_stat.bgcolor = colorize[s_stat.text][0]
        s_stat.color = colorize[s_stat.text][1]
        m_stat = myhtml.TableField(text= status_desc[node_mon_stat])
        m_stat.bgcolor = colorize[m_stat.text][0]
        m_stat.color = colorize[m_stat.text][1]
        if s_stat.text == "ENABLED" and m_stat.text in ['UP', 'DOWN']:
            f = myhtml.FormButton(action='/f5/node_toggle',
                                  button_name = "disable",
                                  button_text = "DISABLE")
            f.add_field(ftype='HIDDEN', fname='action',
                        fvalue='disable')
            f.add_field(ftype='HIDDEN', fname='node',
                        fvalue=node)
            f.add_field(ftype='HIDDEN', fname='hagroup_id',
                        fvalue=hagroup_id)
            action = f.render()
            f = myhtml.FormButton(action='/f5/node_toggle',
                                  button_name = "disable",
                                  button_text = "FORCE DOWN")
            f.add_field(ftype='HIDDEN', fname='action',
                        fvalue='force_disable')
            f.add_field(ftype='HIDDEN', fname='node',
                        fvalue=node)
            f.add_field(ftype='HIDDEN', fname='hagroup_id',
                        fvalue=hagroup_id)
            action += f.render()
        elif s_stat.text == "DISABLED" and m_stat.text in ['UP', 'DOWN']:
            f = myhtml.FormButton(action='/f5/node_toggle',
                                  button_name = "enable",
                                  button_text = "ENABLE")
            f.add_field(ftype='HIDDEN', fname='action',
                        fvalue='enable_ses')
            f.add_field(ftype='HIDDEN', fname='node',
                        fvalue=node)
            f.add_field(ftype='HIDDEN', fname='hagroup_id',
                        fvalue=hagroup_id)
            action = f.render()
        elif s_stat.text == "DISABLED" and m_stat.text == "DISABLED":
            f = myhtml.FormButton(action='/f5/node_toggle',
                                  button_name = "enable",
                                  button_text = "ENABLE")
            f.add_field(ftype='HIDDEN', fname='action',
                        fvalue='enable_sesmon')
            f.add_field(ftype='HIDDEN', fname='node',
                        fvalue=node)
            f.add_field(ftype='HIDDEN', fname='hagroup_id',
                        fvalue=hagroup_id)
            action = f.render()
        else:
            action = "Unavailable"
        t2.row([node, node_ipaddr, s_stat, m_stat, action])
        right = template('toggle_node', nodename=nodename,
                         pool_table=t.render(),
                         node_table=t2.render())
    else:
        request.session['msg']= "INSUFFICIENT PERMISSIONS"
        right = template('insufficient_pool_perm', 
                         nodename=nodename,
                         pool_table=t.render())
    left = left_node_menu(hagroup_id)
    return makepage(user=user, right=right, left=left)

@route('/node_toggle', method='POST')
def node_toggle():
    user = request.auth[0]
    node = request.forms.get('node')
    hagroup_id = request.forms.get('hagroup_id')
    action = request.forms.get('action')
    if not all((node, hagroup_id, action)):
        abort(404, "Data missing from query string")
    b = f5.bigip(hagroup_id)
    ltm_pools = b.pool_get_list()
    members = b.get_pool_members(ltm_pools)
    pools_with_node = []
    for k, v in enumerate(members):
        for n in v:
            if n['address'] == node:
                pools_with_node.append(ltm_pools[k])
    has_all_perm = True
    for p in pools_with_node:
        sql = "select ID from pools where name = %s and hagroup_ID = %s"
        p_id = db.getfield(sql, (p, hagroup_id))
        if not has_pool_perm(user, p_id):
            has_all_perm = False
    if not has_all_perm:
        abort(403, "You do not have permission to modify this node")
    if action == "disable":
        b.toggle_node_session(node, 'STATE_DISABLED')
        logit("Node %s disabled by %s" % (node, user))
    elif action == "force_disable":
        b.toggle_node_session(node, 'STATE_DISABLED')
        b.toggle_node_monitor(node, 'STATE_DISABLED')
        logit("Node %s FORCE disabled by %s" % (node, user))
    elif action == "enable_ses":
        b.toggle_node_session(node, 'STATE_ENABLED')
        logit("Node %s enabled by %s" % (node, user))
    elif action == "enable_sesmon":
        b.toggle_node_session(node, 'STATE_ENABLED')
        b.toggle_node_monitor(node, 'STATE_ENABLED')
        logit("Node %s enabled by %s" % (node, user))
    else:
        abort(404, "Invalid Action in Form")
    redirect (request.headers.get('Referer'), code=303)


@route('/pool_manage')
def pool_manage():
    #TODO Links on pool names
    #TODO Status and Enable/Disable buttons 
    #Disable node button
    user = request.auth[0]
    p_id = request.query.get('p_id')
    if not p_id:
        abort(404, "Data missing from query string")
    if not has_pool_perm(user, p_id):
        abort(403, "You do not have permission to this pool")
    sql = "select hagroup_ID, name from pools where ID = %s"
    result = db.fetchall(sql, p_id)
    hagroup_id = result[0]['hagroup_ID']
    poolname = result[0]['name']
    pools = [poolname]
    b = f5.bigip(hagroup_id)
    ltm_pools = b.pool_get_list()
    if not poolname in ltm_pools:
        right = "Pool does not exist on this LTM"
    else:
        members = b.get_pool_members(pools)
        member_ip = b.get_member_address(pools, members)
        monitor_status = b.get_member_monitor_status(pools, members)
        session_status = b.get_member_session_status(pools, members)
        for k, v in enumerate(pools):
            t = myhtml.Table(caption=friendly_name(v))
            t.width=600
            t.header(['Node Name', 'Node Address', 'Port', 'Session Status', 
                      'Monitor Status', 'Action'])
            for k1, v1 in enumerate(members[k]):
                ipaddr = member_ip[k][k1]
                name = myhtml.link(txt=friendly_name(v1['address']),
                                   link='/f5/node_manage?n=%s&p=%s&ha_id=%s'
                                   % (v1['address'].split('/')[-1],
                                   v1['address'].split('/')[1],
                                   hagroup_id))
                port = v1['port']
                s_stat = myhtml.TableField(text=
                                           status_desc[session_status[k][k1]])
                s_stat.bgcolor = colorize[s_stat.text][0]
                s_stat.color = colorize[s_stat.text][1]
                s_stat.align = 'center'
                m_stat = myhtml.TableField(text=
                                           status_desc[monitor_status[k][k1]])
                m_stat.bgcolor = colorize[m_stat.text][0]
                m_stat.color = colorize[m_stat.text][1]
                m_stat.align = 'center'
                if s_stat.text == 'ENABLED':
                    f = myhtml.FormButton(action='/f5/pool_member_toggle',
                                          button_name = "disable",
                                          button_text = "DISABLE")
                    f.add_field(ftype='HIDDEN', fname='action',
                                fvalue='disable')
                    f.add_field(ftype='HIDDEN', fname='membername',
                                fvalue=v1['address'])
                    f.add_field(ftype='HIDDEN', fname='memberport',
                                fvalue=v1['port'])
                    f.add_field(ftype='HIDDEN', fname='poolname',
                                fvalue=v)
                    f.add_field(ftype='HIDDEN', fname='hagroup_id',
                                fvalue=hagroup_id)
                    action = f.render()
                elif s_stat.text == 'DISABLED':
                    f = myhtml.FormButton(action='/f5/pool_member_toggle',
                                          button_name = "enable",
                                          button_text = "ENABLE")
                    f.add_field(ftype='HIDDEN', fname='action',
                                fvalue='enable')
                    f.add_field(ftype='HIDDEN', fname='membername',
                                fvalue=v1['address'])
                    f.add_field(ftype='HIDDEN', fname='memberport',
                                fvalue=v1['port'])
                    f.add_field(ftype='HIDDEN', fname='poolname',
                                fvalue=v)
                    f.add_field(ftype='HIDDEN', fname='hagroup_id',
                                fvalue=hagroup_id)
                    action = f.render()
                else:
                    action = 'Unavailable'

                t.row([name, ipaddr, port, s_stat, m_stat, action])
        right = t.render()
        vs_with_pool = []
        vs_txt = ''
        vs = b.vs_get_list()
        vs_def_pool = b.get_default_pool_name(vs)
        for k, v in enumerate(vs_def_pool):
            if v == poolname:
                vs_with_pool.append(vs[k])
        if not vs_with_pool:
            vs_with_pool.append('NONE')
        ULList = myhtml.ULList()
        ULList.items = vs_with_pool
        right += template('pools_vs_right', vs_list=ULList.render())
    left = left_pool_menu(user, hagroup_id)
    return makepage(user=user, right=right, left=left)

@route('/poolmain')
def poolmain():
    user = request.auth[0]
    u_id = username_to_id(user)
    hagroup_id = request.query.get('ha_id')
    #sql = "select name, description from hagroup where ID = %s"
    #hagroup = db.fetchall(sql, hagroup_id)
    left = left_pool_menu(user, hagroup_id)
    right = "Pick a pool from the left to manage it"
    return makepage(user=user, right=right, left=left)

@route('/pool_member_toggle', method='POST')
def pool_member_toggle():
    user = request.auth[0]
    action = request.forms.get('action')
    membername = request.forms.get('membername')
    memberport = request.forms.get('memberport')
    poolname = request.forms.get('poolname')
    hagroup_id = request.forms.get('hagroup_id')
    if not all((action, membername, memberport, poolname, hagroup_id)):
        abort(404, "Form data missing from request")
    sql = "select ID from pools where name = %s and hagroup_ID = %s"
    p_id = db.getfield(sql, (poolname, hagroup_id))
    if not has_pool_perm(user, p_id):
        abort (403, 'You do not have permission to modify this pool')
    if action == 'enable':
        state = 'STATE_ENABLED'
    elif action == 'disable':
        state = 'STATE_DISABLED'
    else:
        abort (404, "Invalid action variable value")
    b = f5.bigip(hagroup_id)
    b.toggle_pool_members([poolname], 
                          [[{'address' : membername, 
                          'port' : memberport}]], 
                          [[state]])
    logit("Node:%s set to %s in Pool: %s by %s" % (membername,
                action, poolname, user))
    request.session['msg'] = "Node:%s %s in Pool:%s" % (
                             friendly_name(membername),
			     action,
                             friendly_name(poolname))
    request.session.save()
    redirect (request.headers.get('Referer'), code=303)




### Functions that are not webpages

def email_alert(msg):
    import smtplib
    from email.mime.text import MIMEText
    mailto = 'kevin.coming@safelite.com'
    mailfrom = 'root@windex.sag.asn'
    email = MIMEText(msg)
    email['Subject'] = "F5 Self Service Portal Alert"
    email['To'] = mailto
    email['From'] = mailfrom
    s = smtplib.SMTP('smtp.safelite.net')
    s.sendmail(mailfrom, [mailto], email.as_string())
    s.quit()

def friendly_name(name):
    return name.split('/')[-1]

def has_pool_perm(user, p_id):
    #if 1 == 2:
    if is_admin(user):
        return True
    else:
        sql = "select pools.name from pools " \
              "join users_pools on pools_ID = pools.ID " \
              "join users on users_ID = users.ID " \
              "where username = %s and pools.ID = %s UNION " \
              "select pools.name from pools " \
              "join groups_pools on pools.ID = pools_ID " \
              "join groups on groups_pools.groups_ID = groups.ID " \
              "join users_groups on groups.ID = users_groups.groups_ID " \
              "join users on users_ID = users.ID " \
              "where username = %s and pools.ID = %s"
        result = db.fetchall(sql, [user, p_id, user, p_id])
        if result:
            return True
        else:
            return False

def is_admin(user):
    sql = "select users.ID from users " \
          "join users_groups on users.ID = users_ID " \
          "join groups on groups_ID = groups.ID " \
          "where username = %s and groupname = 'administrator'"
    result = db.getfield(sql, user)
    if result:
        return True
    else:
        return False

def left_node_menu(hagroup_id):
    b = f5.bigip(hagroup_id)
    nodes = b.get_node_list()
    nodes.sort()
    sql = "select name, description from hagroup where ID = %s"
    result = db.fetchall(sql, hagroup_id)
    txt = ''
    for n in nodes:
        nodename = n.split('/')[-1]
        partition = n.split('/')[1]
        txt += myhtml.link(txt=nodename,
                           link="/f5/node_manage?n=%s&p=%s&ha_id=%s" %
                           (nodename,partition, hagroup_id))
    return template('node_left',
                    hagroup_name=result[0]['name'],
                    hagroup_desc=result[0]['description'],
                    nodes=txt)

def left_pool_menu(user, hagroup_id):
    sql = "select name, description from hagroup where ID = %s"
    hagroup = db.fetchall(sql, hagroup_id)
    sql = "select ID from users where username = %s"
    u_id = db.getfield(sql, user)
    if is_admin(user):
    #if 1 == 2:
        sql = "select pools.ID, pools.name from pools where hagroup_ID = %s " \
              "order by name"
        pools = db.fetchall(sql, hagroup_id)
    else:
        sql = "select pools.ID, pools.name from pools " \
              "join users_pools on pools_ID = pools.ID " \
              "where users_ID = %s and hagroup_ID = %s UNION " \
              "select pools.ID, pools.name from pools " \
              "join groups_pools on pools.ID = pools_ID " \
              "join groups on groups_pools.groups_ID = groups.ID " \
              "join users_groups on groups.ID = users_groups.groups_ID " \
              "where users_ID = %s and hagroup_ID = %s order by name"
        pools = db.fetchall(sql, (u_id, hagroup_id, u_id, hagroup_id))
    if not pools:
        return 'NONE'
    else:
        txt = ''
        for p in pools:
            poolname = p['name'].split('/')[-1]
            link = myhtml.link(txt=poolname, link='/f5/pool_manage?p_id=%s' %
                               p['ID'])
            txt += link
    return template('ltm_left', hagroup_name=hagroup[0]['name'],
                        hagroup_desc=hagroup[0]['description'],
                        pools=txt)

def logit(msg):
   import syslog
   syslog.syslog(syslog.LOG_INFO | syslog.LOG_LOCAL5, msg)

def makepage(user, left="", right=""):
    menu_txt = menu(user)
    if 'msg' in request.session:
        msg = request.session['msg']
        right = template('msg', msg=msg) + right
    request.session['msg'] = ''
    request.session.save()
    return template('main', menu=menu_txt, left=left, right=right)

def menu(user):
    #build top menu
    hagroups = f5.get_hagroups()
    menu = myhtml.Menu()
    menu.add_title(title="HOME", url=rootpath)
    menu.add_title(title="Pools", url="#")
    menu.add_title(title="Nodes", url="#")
    #Build a drop down of all configured hagroups
    #TODO? only list hagroups that the user has permissions for a vs
    for x in hagroups:
        menu.add_item(title="Pools", item=x['description'],
                      url='/f5/poolmain?ha_id=%s' % x['id'])
        menu.add_item(title="Nodes", item=x['description'],
                      url='/f5/nodemain?ha_id=%s' % x['id'])
    #Build Admin portion of menu
    if is_admin(user):
        menu.add_title(title="Admin", url="/f5/admin")
        menu.add_item(title="Admin", item="Users", url="/f5/admin/users")
        menu.add_item(title="Admin", item="Groups", url="/f5/admin/groups")
        menu.add_item(title="Admin", item="Pools", url="/f5/admin/pools")
        menu.add_item(title="Admin", item="F5 LTMs", 
                      url="/f5/admin/ltm")
    return menu.render()

def menu_left_hagroup():
    pools = ""
    sql = "select * from hagroup"
    hagroups = db.fetchall(sql)
    for c in hagroups:
        pools += myhtml.link(txt='&nbsp' + c['name'],
                             link='/f5/admin/pools_manage?ha_id=%s' % c['ID'])
    return pools

def username_to_id(username):
    sql = "select ID from users where username = %s"
    u_id = db.getfield(sql, username)
    return u_id

def user_table():
    #return an HTML table of users, and option to delete
    #Get all user info from db
    sql = "select * from users order by username"
    result = db.fetchall(sql)
    t = myhtml.Table()
    t.caption = "User Management"
    t.width = 400
    t.header(['Username', 'Delete'])
    #First field in Table, username
    for u in result:
        username = myhtml.link(txt=u['username'], 
                    link = '/f5/admin/user_perm?u_id=%s' %  u['ID'])
        #seconf table field, delete option
        f = myhtml.FormButton(action='/f5/admin/user_del',
                            button_name = "DELETE",
                            button_text = "DELETE")
        f.add_field(ftype='HIDDEN', fname='u_id', fvalue=u['ID'])
        #set delete field button html
        delete = f.render()
        t.row([username, delete])
    return t.render()


application = myapp

