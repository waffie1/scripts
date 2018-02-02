# Cloudwatch_to_ElasticSeach_WinEventLogs
# Version 1.0.4
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


import zlib
from base64 import b64decode
import datetime
import json
import re
import boto3
import requests
import os
import logging
from requests_aws4auth import AWS4Auth


logger = logging.getLogger()
logging_map = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG
}
if os.environ.get('LOG_LEVEL') in logging_map:
    logger.setLevel(logging_map[os.environ.get('LOG_LEVEL')])
else:
    logger.setLevel(logging.WARNING)


if os.environ.get('ENABLE_XRAY') == 'true':
    try:
        from aws_xray_sdk.core import xray_recorder
        from aws_xray_sdk.core import patch
        patch(['boto3', 'requests'])
    except ImportError:
        logger.warning('Unable to load aws_xray_sdk module.  Xray '
                       'functionality may be limited')


def lambda_handler(event, context):
    host = os.environ['ES_ENDPOINT']
    region = os.environ['REGION']
    access_key = boto3.client('kms').decrypt(CiphertextBlob=b64decode(
            os.environ['ACCESS_KEY']))['Plaintext']
    secret_key = boto3.client('kms').decrypt(CiphertextBlob=b64decode(
            os.environ['SECRET_KEY']))['Plaintext']
    auth = AWS4Auth(
            access_key,
            secret_key,
            region,
            'es',
    )
    logdata = event['awslogs']['data']
    decoded = b64decode(logdata)
    log_string = zlib.decompress(decoded, 16+zlib.MAX_WBITS)
    log = json.loads(log_string)
    instance_id = log['logStream'].split('_')[-1]
    aws_account = log['owner']
    ec2_resource = boto3.resource('ec2')
    instance = ec2_resource.Instance(instance_id)
    logger.info('%s log entries in this event' % len(log['logEvents']))
    session = requests.Session()
    for item in log['logEvents']:
        timestamp = datetime.datetime.fromtimestamp(
                    item['timestamp'] / 1000.0).strftime(
                    '%Y-%m-%dT%H:%M:%S.%fZ')
        msg_format = {
            'message': item['message'],
            '@timestamp': timestamp,
            'instance-id': instance_id,
            'aws-account': aws_account
        }
        for tag in instance.tags:
            msg_format['tag.%s' % tag['Key']] = tag['Value']
        msg_format['type'] = 'bootstraplog'
        event_date = datetime.datetime.fromtimestamp(
                item['timestamp'] / 1000).strftime('%Y-%m-%dT%H:%M:%SZ').split(
                'T')[0].replace('-', '.')
        url = 'https://'+host+'/logstash-'+event_date+'/bootstraplog/'
        amz_date = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        headers = {
                'Content-Type': 'application/json',
                'X-Amz-Date': amz_date
        }
        response = session.post(
                url,
                data=json.dumps(msg_format),
                headers=headers,
                auth=auth
        )
        try:
            response.raise_for_status()
        except Exception as e:
            logger.warning('Error Reponse Code Received: %s',
                           response.status_code)
            logger.warning('Text: %s', response.content)
            logger.warning('This message was not inserted into elasticsearch')
        else:
            logger.info('Log Event sent to Elastic Search')
    session.close()
