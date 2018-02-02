#!/usr/bin/python

# ElasticsearchIndexDelete
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


import boto3
import datetime
import logging
import os
import re
import requests
from base64 import b64decode
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
        logger.warning('Unable to load aws_xray_sdk module.  Xray functionality '
                    'may be limited')


def lambda_handler(event, context):
    logger.info('Starting index cleanup')
    elastic_url = event['ELASTIC_URL']
    expire_days = int(event['EXPIRE_DAYS'])
    region = event['REGION']
    access_key = boto3.client('kms').decrypt(CiphertextBlob=b64decode(
            event['ACCESS_KEY']))['Plaintext']
    secret_key = boto3.client('kms').decrypt(CiphertextBlob=b64decode(
            event['SECRET_KEY']))['Plaintext']
    auth = AWS4Auth(
            access_key,
            secret_key,
            region,
            'es',
    )
    session = requests.Session()
    count = 0
    date_pattern = re.compile(r'^.*([0-9]{4}\.[0-9]{2}\.[0-9]{2}).*$')
    expire_date = datetime.datetime.utcnow() + datetime.timedelta(-expire_days)
    response = session.get('%s/_cat/indices' % elastic_url, auth=auth)
    indexes = response.content.split('\n')
    for item in indexes:
        result = date_pattern.search(item)
        if result:
            index_date = datetime.datetime.strptime(
                    result.group(1), '%Y.%m.%d')
            if index_date < expire_date:
                index_name = item.split()[2]
                response = session.delete('%s/%s' % (elastic_url, index_name),
                        auth=auth)
                if response.status_code == 200:
                    logger.info('Deleted %s' % index_name)
                    count += 1
                else:
                    logger.warning('Error deleting %s' % index_name)
    logger.info('Completed index clearnup')
    logger.info('%s indexes deleted' % count)
