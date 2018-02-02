# ElbLogs_to_ElasticSearch
# Version 1.0.3
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
import csv
import datetime
import gzip
import json
import logging
import os
import re
import requests
from base64 import b64decode
from collections import OrderedDict
from geoip import geolite2
from requests_aws4auth import AWS4Auth
from StringIO import StringIO
from urlparse import urlsplit
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
log_fields = OrderedDict([
        ('elb_request_type', str),
        ('@timestamp', str),
        ('elb_id', str),
        ('client:port', str),
        ('target:port', str),
        ('request_processing_time', float),
        ('target_processing_time', float),
        ('response_processing_time', float),
        ('elb_status_code', int),
        ('target_status_code', int),
        ('cs-bytes', int),
        ('sc-bytes', int),
        ('request', str),
        ('cs(User-Agent)', str),
        ('ssl-cipher', str),
        ('ssl-protocol', str),
        ('target_group_arn', str),
        ('trace_id', str),
        ('cs(Host)', str),
        ('chosen_cert_arn', str)
])


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
    key_fields = re.search('.*(\d{12})_.*app\.(.+?)\..*(\d{8})T', key)
    account = key_fields.group(1)
    logger.info('Account number derived from S3 Key: %s' % account)
    elb_name = key_fields.group(2)
    logger.info('ELB name derived from S3 Key: %s' % elb_name)
    index_date = '%s.%s.%s' % (
            key_fields.group(3)[0:4],
            key_fields.group(3)[4:6],
            key_fields.group(3)[6:8]
    )
    logger.info('index_date derived from S3 Key: %s' % index_date)

    # Attempt to get tags from the load balancer
    try:
        # Get authentication token for the account/role this elb is in
        sts_client = boto3.client('sts')
        assumedRoleObject = sts_client.assume_role(
                RoleArn=role_mapping % account,
                RoleSessionName="AssumeRoleSession"
        )
        credentials = assumedRoleObject['Credentials']
        elb_client = boto3.client(
                'elbv2',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
        )
        load_balancer = elb_client.describe_load_balancers(Names=[elb_name])
        lb_arn = load_balancer['LoadBalancers'][0]['LoadBalancerArn']
        tag_result = elb_client.describe_tags(ResourceArns=[lb_arn])
        lb_tags = tag_result['TagDescriptions'][0]['Tags']
    except Exception as e:
        logger.warning('Problem getting tags for ELB: %s' % e)
        logger.warning('Account: %s' % account)
        lb_tags = []

    # Retrieve the logfile from S3
    s3 = boto3.resource('s3')
    obj = s3.Object(bucket, key)
    compressed_contents = obj.get()['Body'].read()
    log_txt = gzip.GzipFile(fileobj=StringIO(compressed_contents)).read()

    # Chunk logfile into pieces for bulk submission to ES
    log_list = log_txt.split('\n')
    log_chunk = list(log_list[i:i+logs_per_request] for i in xrange(
            0, len(log_list), logs_per_request))

    # Create ES index string that prepends each of the document lines for
    # bulk operation
    index_dict = {
            'index': {
                    '_index': 'logstash-%s' % index_date,
                    '_type': 'elblogs'
                    }
    }
    session = requests.Session()
    geo_ip_cache = {}
    ua_cache = {}
    logs_inserted = 0
    for chunk in log_chunk:
        bulk_txt = ''
        reader = csv.DictReader(chunk, log_fields.keys(), delimiter=' ')
        for item in reader:
            try:
                # Fix target_status_code if set to -
                if item['target_status_code'] == '-':
                    item['target_status_code'] = -1
                # Set data types properly for items
                for k, v in item.items():
                    if k in log_fields:
                        item[k] = log_fields[k](v)
                cp = item['client:port'].split(':')
                if len(cp) == 2:
                    item['c-ip'] = cp[0]
                    item['c-port'] = int(cp[1])
                    #item['c-ip'], item['c-port'] = cp
                sp = item['target:port'].split(':')
                if len(sp) == 2:
                    item['s-ip'] = sp[0]
                    item['s-port'] = int(sp[1])
                    #item['s-ip'], item['s-port'] = sp
                cm = item['request'].split()
                if len(cm) == 3:
                    (item['cs-method'],
                            item['cs-uri'],
                            item['cs-protocol-version']) = cm
                us = urlsplit(item['cs-uri'])
                if us.path:
                    item['cs-uri-stem'] = us.path
                else:
                    item['cs-uri-stem'] = '-'
                if us.query:
                    item['cs-uri-query'] = us.query
                else:
                    item['cs-uri-query'] = '-'
                for tag in lb_tags:
                    item['tag.%s' % tag['Key']] = tag['Value']
                item['aws-account'] = account

                if item['c-ip'] not in geo_ip_cache:
                    geo_ip_cache[item['c-ip']] = geo_lookup(item['c-ip'])
                item.update(geo_ip_cache[item['c-ip']])
                if item['cs(User-Agent)'] not in ua_cache:
                    ua_cache[item['cs(User-Agent)']] = ua_lookup(
                            item['cs(User-Agent)'])
                item.update(ua_cache[item['cs(User-Agent)']])
                item['type'] = 'elblogs'
            except Exception as e:
                logger.warning('Problem adding additional fields to messages: %s' % e)
            bulk_txt += '%s\n%s\n' % (
                    json.dumps(index_dict),
                    json.dumps(item)
            )
            logs_inserted += 1
        amz_date = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        headers = {
                'Content-Type': 'application/x-ndjson',
                'X-Amz-Date': amz_date
        }
        # Dummy continue to skip posting into ES
        if not bulk_txt:
            continue
        response = session.post(
                url,
                data=bulk_txt,
                headers=headers,
                auth=auth
        )
        try:
            response.raise_for_status()
        except Exception as e:
            raise
            logger.warning('Error Reponse Code Received: %s',
                           response.status_code)
            logger.warning('Text: %s', response.content)
            logger.warning('This message was not inserted into elasticsearch')
        else:
            logger.info('Log Event sent to Elastic Search')
    session.close()
    logger.info('%s lines in log file %s' % (len(log_list), key))
    logger.info('Lines inserted into elasticsearch: %s' % logs_inserted)
    obj.delete()

