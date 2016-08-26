#!/usr/bin/python


import MySQLdb

import sys
sys.path.append("/home/www/f5")
import config
dbuser = config.dbuser
dbpass = config.dbpass
dbhost = config.dbhost
dbname = config.dbname

#Connection def
def dbconn():
   #try:
   conn = MySQLdb.connect (host = dbhost,
      user = dbuser,
      passwd = dbpass,
      db = dbname)
   #except MySQLdb.Error, e:
   #   die("%d: %s" % (e.args[0], e.args[1]))
   return conn

#Return only the first field of the first row on a select
def getfield(sql, values=''):
   conn = dbconn()
   db = conn.cursor()
   if values:
      result_set = db.execute(sql, values)
   else:
      result_set = db.execute(sql)
   if result_set:
      result = db.fetchone()[0]
   else:
      result = False
   db.close()
   conn.close()
   return result

#Return entire dictionary on select
def fetchall(sql, values=''):
   conn = dbconn()
   db = conn.cursor (MySQLdb.cursors.DictCursor)
   if values:
      result_set = db.execute(sql, values)
   else:
      result_set = db.execute(sql)
   if result_set:
      result = db.fetchall()
   else:
      result = False
   db.close()
   conn.close()
   return result

def insert(sql, values=''):
   conn = dbconn()
   db = conn.cursor()
   if values:
      result_set = db.execute(sql, values)
   else:
      result_set = db.execute(sql)
   return conn.insert_id()

#Return a list that is an entire column from a select
def getcolumn(sql, values=''):
   l = []
   conn = dbconn()
   db = conn.cursor()
   if values:
      result_set = db.execute(sql, values)
   else:
      result_set = db.execute(sql)
   if result_set:
      result = db.fetchall()
   else:
      result = False
   if result:
      for value in result:
         l.append(value[0])
   db.close()
   conn.close()
   return l 

