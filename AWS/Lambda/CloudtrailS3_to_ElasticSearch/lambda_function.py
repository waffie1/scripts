# CloudtrailS3_to_ElasticSearch 
# Version 1.0.1
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
import json
import logging
import os
import re
import logging
import requests
import zlib
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


logs_per_request = 500


def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    host = os.environ['HOST']
    region = os.environ['REGION']
    index_date = re.search('.*([0-9]{8})T.*', key).group(1)
    url = 'https://%s/_bulk' % host
    if 'Digest' in key:
        logger.info("Digest File... Skipping")
        return
    s3 = boto3.resource('s3')
    obj = s3.Object(bucket, key)
    compressed_contents = obj.get()['Body'].read()
    contents = zlib.decompress(compressed_contents, 16+zlib.MAX_WBITS)
    records = json.loads(contents)["Records"]
    logchunk = list(records[i:i+logs_per_request] for i in xrange(
            0, len(records), logs_per_request))
    credentials = boto3.Session().get_credentials()
    auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'es',
            session_token=credentials.token
    )

    index_dict = {
            'index': {
                    '_index': 'logstash-%s' % index_date,
                    '_type': 'iislog'
            }
    }
    session = requests.Session()
    for chunk in logchunk:
        bulk_txt = ''
        for item in chunk:
            try:
                logging.info('Sending event to elasticsearch')
                item["@timestamp"] = item["eventTime"]
                item["eventSource"] = item["eventSource"].split(".")[0]
                index_date = item["eventTime"].split("T")[0].replace("-", ".")
                index_dict = {
                        'index': {
                                '_index': 'logstash-%s' % index_date,
                                '_type': 'cloudtrail'
                        }
                }
                bulk_txt += '%s\n%s\n' % (
                        json.dumps(index_dict),
                        json.dumps(item)
                )
            except Exception as e:
                logger.warning('Unable to process log entry: %s' % item)
                logger.warning('Exception: %s' % e)
        amz_date = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        headers = {'Content-Type': 'application/x-ndjson',
                   'X-Amz-Date': amz_date}
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
            logger.warning('Reponse Text: %s', response.content)
            logger.warning('This message was not inserted into elasticsearch')
        else:
            logger.info('Log Event sent to Elastic Search')
    session.close()

