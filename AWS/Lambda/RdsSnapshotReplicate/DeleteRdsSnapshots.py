#!/usr/bin/python

from __future__ import print_function
import datetime
from dateutil.tz import tzlocal
import boto3

def lambda_handler(event, context):
    expiration = datetime.datetime.now(tzlocal()) + datetime.timedelta(-7)
    client = boto3.client('rds', 'us-east-2')
    snapshots = client.describe_db_snapshots()
    for item in snapshots['DBSnapshots']:
        if item['SnapshotCreateTime'] < expiration:
            print('%s has expired. Deleting' % item['DBSnapshotIdentifier'])
            # client.delete_db_snapshot(DBSnapshotIdentifier=item['DBSnapshotIdentifier']
    print('RDS snapshot cleanup complete')
    return {'Status': 'Success'}


