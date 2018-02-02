#!/usr/bin/python

# RdsSnapshotCopy
# Copyright 2017 Kevin Coming (waffie1@github)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import print_function
import boto3


def get_latest_snapshot(rds_name, region):
    client = boto3.client('rds', region)
    result = client.describe_db_snapshots(DBInstanceIdentifier=rds_name)
    latest = False
    for item in result['DBSnapshots']:
        if not latest:
            latest = item['SnapshotCreateTime']
            latest_arn = item['DBSnapshotArn']
        else:
            if item['SnapshotCreateTime'] > latest:
                latest = item['SnapshotCreateTime']
                latest_arn = item['DBSnapshotArn']
    return latest_arn


def lambda_handler(event, context):
    print("Starting Snapshot Copy")
    print("Event: %s" % event)
    try:
        rds_name = event['rds_name']
        src_region = event['src_region']
        dest_region = event['dest_region']
        dest_option_group = event['dest_option_group']
        kms_key_arn = event['kms_key_arn']
    except KeyError as e:
        print('Missing mandatory value in event: %s' % e)
        print(event)
        return {'Status': 'Failed',
                'Message': 'Event missing mandatory values'}
    src_client = boto3.client('rds', src_region)
    dest_client = boto3.client('rds', dest_region)
    latest_snapshot_arn = get_latest_snapshot(rds_name, src_region)
    src_snapshot = src_client.describe_db_snapshots(
            DBSnapshotIdentifier=latest_snapshot_arn
    )
    dest_snapshot_name = src_snapshot['DBSnapshots'][0]['DBSnapshotArn'].split(':')[-1]
    if src_snapshot['DBSnapshots'][0]['Encrypted'] and not kms_key_arn:
        print('Encryption key not specified for encrypted db')
        return {'Status': 'Failed',
                'Message': 'Encryption key not specified for encrypted db'}
    elif kms_key_arn:
        dest_client.copy_db_snapshot(
                SourceDBSnapshotIdentifier=latest_snapshot_arn,
                TargetDBSnapshotIdentifier=dest_snapshot_name,
                OptionGroupName=dest_option_group,
                SourceRegion=src_region,
                KmsKeyId=kms_key_arn
        )
    else:
        dest_client.copy_db_snapshot(
                SourceDBSnapshotIdentifier=latest_snapshot_arn,
                TargetDBSnapshotIdentifier=dest_snapshot_name,
                OptionGroupName=dest_option_group,
                SourceRegion=src_region
        )
    print("Completed Run")
    return {'Status': 'Success'}
