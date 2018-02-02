# InstanceTerminationCleanup
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
import logging
import os
import requests
from base64 import b64decode


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
    try:
        octopus_server = os.environ['OCTOPUS_SERVER']
        api_key = boto3.client('kms').decrypt(CiphertextBlob=b64decode(
                os.environ['API_KEY']))['Plaintext']
        ssm_association_name = os.environ['SSM_ASSOCIATION_NAME']
    except KeyError as e:
        logger.error('Environmental variable missing from config: %e')
        raise
    try:
        if not event['detail']['state'] == 'terminated':
            logger.info('Event state is not terminated.  Exiting')
            return json.dumps({'Status': 'WrongEvent'})
        instance_id = event['detail']['instance-id']
    except KeyError:
        logger.error('Event received is not a valid event')
        raise
    logger.info('Removing machine from Octopus')
    response = octopus_deregister(
            instance_id=instance_id,
            octopus_server=octopus_server,
            api_key=api_key
    )
    if not response:
        logger.warning('InstanceId %s not removed from Octopus' % instance_id)
    else:
        logger.info('InstanceId %s  removed from Octopus' % instance_id)
    logger.info('Removing Domain Join SSM Associations')
    response = ssm_association_deregister(instance_id, ssm_association_name)
    if not response:
        logger.warning('No SSM Associations removed for Instance %s' %
                    instance_id)
    else:
        logger.info('SSM Associations removed for Instance %s' % instance_id)


def octopus_deregister(instance_id, octopus_server, api_key):
    client = boto3.client('ec2')
    ec2_filter = [
        {
            'Name': 'resource-id',
            'Values': [instance_id]
        },
        {
            'Name': 'key',
            'Values': ['OctopusMachineId']
        }
    ]
    result = client.describe_tags(Filters=ec2_filter)
    if len(result['Tags']) == 0:
        logger.info('OctopusMachineId Tag not found for instance %s' %
                    instance_id)
        return False
    octopus_machine_id = result['Tags'][0]['Value']
    if not octopus_machine_id:
        logger.info('OctopusMachineId Tag not found for instance %s' %
                    instance_id)
        return False
    url = 'http://%s/api/machines/%s?apiKey=%s' % (
        octopus_server,
        octopus_machine_id,
        api_key
    )
    response = requests.delete(url)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        logger.error('Error removing machine from %s Octopus' % instance_id)
        return False
    else:
        logger.info('Request to delete %s successful' %
                    octopus_machine_id)
        return True


def ssm_association_deregister(instance_id, ssm_association_name):
    client = boto3.client('ssm')
    ssm_filter = [
            {'key': 'InstanceId', 'value': instance_id},
            {'key': 'Name', 'value': ssm_association_name}
    ]
    status = False
    response = client.list_associations(AssociationFilterList=ssm_filter)
    if not response['Associations']:
        logger.info('No SSM Association found for %s' % instance_id)
        return False
    for item in response['Associations']:
        if item['Name'] == ssm_association_name:
            try:
                client.delete_association(
                        Name=item['Name'],
                        InstanceId=item['InstanceId'],
                        AssociationId=item['AssociationId']
                )
            except Exception as e:
                logger.error('Error deleting SSM Association: %s' % e)
            else:
                status = True
        return status
