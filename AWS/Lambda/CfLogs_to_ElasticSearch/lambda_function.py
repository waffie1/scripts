# CloudfrontLogs_to_ElasticSearch
# Version 1.0.2
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
import gzip
import json
import logging
import os
import requests
from base64 import b64decode
from geoip import geolite2
from requests_aws4auth import AWS4Auth
from StringIO import StringIO
from ua_parser import user_agent_parser


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
role_mapping = 'arn:aws:iam::%s:role/LogParserHelper'
log_field_type_override = {
        'cs-bytes': int,
        'sc-bytes': int,
        'sc-status': int,
        'time-taken': float
}


# Yes I know this is ugly, but I could not find a single clean
# solution that dealt with all possible scenarios.
# At least this way makes it obvious what I am doing
def geo_lookup(ip):
    g = {}
    try:
        lookup = geolite2.lookup(ip)
    except ValueError:
        logger.info('Unable to lookup geo-info for %s' % ip)
        pass
    else:
        if lookup:
            geo = lookup.get_info_dict()
            try:
                g['geo.city_name'] = geo['city']['names']['en']
            except:
                pass
            try:
                g['geoip.continent_code'] = geo['continent']['names']['en']
            except:
                pass
            try:
                g['geoip.country_code'] = geo['country']['iso_code']
            except:
                pass
            try:
                g['geoip.country_name'] = geo['country']['names']['en']
            except:
                pass
            try:
                g['geoip.dma_code'] = geo['location']['metro_code']
            except:
                pass
            try:
                g['geoip.latitude'] = geo['location']['latitude']
            except:
                pass
            try:
                g['geoip.location'] = '%s, %s' % (
                        geo['location']['latitude'],
                        geo['location']['longitude']
                )
            except:
                pass
            try:
                g['geoip.longitude'] = geo['location']['longitude']
            except:
                pass
            try:
                g['geoip.postal_code'] = geo['postal']['code']
            except:
                pass
            try:
                g['geoip.region_code'] = geo['subdivisions'][0]['iso_code']
            except:
                pass
            try:
                g['geoip.region_name'] = geo['subdivisions'][0]['names']['en']
            except:
                pass
            try:
                g['geoip.timezone'] = geo['location']['time_zone']
            except:
                pass
    return g


def ua_lookup(ua_string):
    ua = {}
    r = user_agent_parser.Parse(ua_string)
    ua['browser_device'] = r['device']['family']
    ua['browser_major'] = r['user_agent']['major']
    ua['browser_minor'] = r['user_agent']['minor']
    ua['browser_name'] = r['user_agent']['family']
    ua['browser_os'] = r['os']['family']
    return ua


def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    # Variables from Lambda Environment
    region = os.environ['REGION']
    access_key = boto3.client('kms').decrypt(CiphertextBlob=b64decode(
            os.environ['ACCESS_KEY']))['Plaintext']
    secret_key = boto3.client('kms').decrypt(CiphertextBlob=b64decode(
            os.environ['SECRET_KEY']))['Plaintext']
    url = 'https://%s/_bulk' % os.environ['ES_ENDPOINT']

    # Auth header for Elastic Search
    auth = AWS4Auth(
            access_key,
            secret_key,
            region,
            'es',
    )

    # Get variables from S3 key
    t = key.split('/')
    account = t[1]
    distribution_id = t[4].split('.')[0]
    index_date = t[4].split('.')[1][:-3].replace('-', '.')
    try:
        # Get tags from distribution
        sts_client = boto3.client('sts')
        assumedRoleObject = sts_client.assume_role(
                RoleArn=role_mapping % account,
                RoleSessionName="AssumeRoleSession"
        )
        credentials = assumedRoleObject['Credentials']
        client = boto3.client(
                'cloudfront',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
        )
        result = client.list_distributions()
        for item in result['DistributionList']['Items']:
            if item['Id'] == distribution_id:
                cf_tags = client.list_tags_for_resource(
                        Resource=item['ARN'])['Tags']['Items']
    except Exception as e:
        logger.warning('Unable to get tags from distribution: %s' % e)
        cf_tags = []

    # Authentication Header for ElasticSearch
    # Retrieve the logfile from S3
    s3 = boto3.resource('s3')
    obj = s3.Object(bucket, key)
    compressed_contents = obj.get()['Body'].read()
    log_txt = gzip.GzipFile(fileobj=StringIO(compressed_contents)).read()

    # Get log fields from file header
    log_list = log_txt.split('\n')
    del(log_list[0])
    fields_str = log_list.pop(0)
    fields_str = fields_str.replace('#Fields: ', '')
    log_fields = fields_str.split()

    # Chunk logfile into pieces for bulk submission to ES
    log_chunk = list(log_list[i:i+logs_per_request] for i in xrange(
            0, len(log_list), logs_per_request))

    logger.info('%s entries in log file' % len(log_list))
    logger.info('Log split into %s chunks' % len(log_chunk))
    # Create ES index string that prepends each of the document lines for
    # bulk update
    index_dict = {
            'index': {
                    '_index': 'logstash-%s' % index_date,
                    '_type': 'cloudfrontlogs'
                    }
    }
    session = requests.Session()
    geo_ip_cache = {}
    ua_cache = {}
    logs_inserted = 0
    for chunk in log_chunk:
        bulk_txt = ''
        for line in chunk:
            if not line:
                continue
            item = dict(zip(log_fields, line.split('\t')))
            try:
                # Modify fields that should not be text
                for k,v in item.items():
                    if k in log_field_type_override:
                        item[k] = log_field_type_override[k](v)
                if item['c-ip'] not in geo_ip_cache:
                    geo_ip_cache[item['c-ip']] = geo_lookup(item['c-ip'])
                item.update(geo_ip_cache[item['c-ip']])
                if item['cs(User-Agent)'] not in ua_cache:
                    ua_cache[item['cs(User-Agent)']] = ua_lookup(
                            item['cs(User-Agent)'])
                item.update(ua_cache[item['cs(User-Agent)']])
                item['@timestamp'] = '%sT%sZ' % (item['date'], item['time'])
                item['type'] = 'cloudfrontlogs'
                del(item['time'])
                del(item['date'])
                for tag in cf_tags:
                    item['tag.%s' % tag['Key']] = tag['Value']
                item['aws-account'] = account
                bulk_txt += '%s\n%s\n' % (
                        json.dumps(index_dict),
                        json.dumps(item)
                )
            except Exception as e:
                logger.warning('Invalid Message Format: %s' % item)
                logger.warning('Exception: %s' % e)
                logger.warning('Skipping this message')
                logger.warning('Item' % item)

            logs_inserted += 1


        amz_date = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        headers = {
                'Content-Type': 'application/x-ndjson',
                'X-Amz-Date': amz_date,
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
    logger.info('Lines inserted into elasticsearch: %s' % logs_inserted)
    obj.delete()
