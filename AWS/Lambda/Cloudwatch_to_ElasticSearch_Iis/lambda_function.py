# Cloudwatch_to_ElasticSeach_IisLogs
# Version 1.1.4
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
        logger.warning('Unable to load aws_xray_sdk module.  '
                       'Xray functionality may be limited')


logs_per_request = 500


def lambda_handler(event, context):
    url = 'https://%s/_bulk' % os.environ['ES_ENDPOINT']
    region = os.environ['REGION']
    access_key = boto3.client('kms').decrypt(CiphertextBlob=b64decode(
            os.environ['ACCESS_KEY']))['Plaintext']
    secret_key = boto3.client('kms').decrypt(CiphertextBlob=b64decode(
            os.environ['SECRET_KEY']))['Plaintext']

    decoded = b64decode(event['awslogs']['data'])
    log = json.loads(
            zlib.decompress(
                    b64decode(event['awslogs']['data']),
                    16+zlib.MAX_WBITS
            )
    )
    instance_id = log['logStream']
    aws_account = log['owner']
    auth = AWS4Auth(
            access_key,
            secret_key,
            region,
            'es',
    )
    try:
        ec2_resource = boto3.resource('ec2')
        tags = ec2_resource.Instance(instance_id).tags
    except Exception as e:
        logger.warning('Unable to get tags for instance: %s' % e)
        tags = []
    logger.info('%s log entries in this event' % len(log['logEvents']))
    session = requests.Session()

    logchunk = list(log['logEvents'][i:i+logs_per_request] for i in xrange(
            0, len(log['logEvents']), logs_per_request))
    for chunk in logchunk:
        bulk_txt = ''
        for item in chunk:
            timestamp = datetime.datetime.fromtimestamp(
                    item['timestamp'] / 1000).strftime(
                    '%Y-%m-%dT%H:%M:%S.%fZ')
            event_date = datetime.datetime.fromtimestamp(
                    item['timestamp'] / 1000).strftime(
                    '%Y-%m-%dT%H:%M:%SZ').split('T')[0].replace('-', '.')
            index_dict = {
                    'index': {
                            '_index': 'logstash-%s' % event_date,
                            '_type': 'iislog'
                            }
            }
            index_str = '%s\n' % json.dumps(index_dict)
            fields = item['message'].split()
            if not fields:
                logger.warning('%s did not match Iis EventLog Pattern: %s'
                               % item['message'])
                logger.warning('Skipping this message')
                continue
            if fields[0].startswith('#'):
                logger.info('Skipping comment line')
                continue

            try:
                msg_format = {
                    's-ip': fields[0],
                    'cs-method': fields[1],
                    'cs-uri-stem': fields[2],
                    'cs-uri-query': fields[3],
                    's-port': int(fields[4]),
                    'cs-username': fields[5],
                    'c-ip': fields[6],
                    'cs(User-Agent)': fields[7],
                    'cs(Referer)': fields[8],
                    'sc-status': int(fields[9]),
                    'sc-substatus': fields[10],
                    'sc-win32-status': fields[11],
                    'time-taken': float(fields[12]) / 1000,
                    '@timestamp': timestamp,
                    'instance-id': instance_id,
                    'aws-account': aws_account,
                    'type': 'iislog'
                }
                for tag in tags:
                    msg_format['tag.%s' % tag['Key']] = tag['Value']
            except (IndexError, ValueError):
                logger.warning('Invalid Message Format: %s' % item['message'])
                logger.warning('Skipping this message')
            else:
                bulk_txt += index_str
                bulk_txt += json.dumps(msg_format)
                bulk_txt += '\n'
        amz_date = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        headers = {
                'Content-Type': 'application/x-ndjson',
                'X-Amz-Date': amz_date
        }
        response = session.post(
                url,
                data=bulk_txt,
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
