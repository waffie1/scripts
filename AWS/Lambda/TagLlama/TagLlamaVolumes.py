# TagLlama
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


required_tags = [
        'ApplicationId',
        'ApplicationSuffix',
        'CostCenter',
        'Environment',
        'RecoveryTier',
        'ServiceLevel'
]


def lambda_handler(event, context):
    print("The Tag Llama is beginning the search for MISSING TAGS!")
    client = boto3.client('ec2')
    volumes = client.describe_volumes()
    vol_dict = {}
    for item in volumes['Volumes']:
        vol_dict[item['VolumeId']] = {}
        if 'Tags' in item:
            for tag in item['Tags']:
                vol_dict[item['VolumeId']][tag['Key']] = tag['Value']

    instances = client.describe_instances()
    for item in instances['Reservations']:
        instance_tags = []
        instance_id = item['Instances'][0]['InstanceId']
        if 'Tags' not in item['Instances'][0]:
            print("No tags found on Instance %s"
                  % item['Instances'][0]['InstanceId'])
            continue
        for block_device in item['Instances'][0]['BlockDeviceMappings']:
            vol_id = block_device['Ebs']['VolumeId']
            missing_tags = []
            for tag in item['Instances'][0]['Tags']:
                if (tag['Key'] not in vol_dict[vol_id] and
                        tag['Key'] in required_tags):
                    print("The Llama found that Volume %s is missing tag %s" %
                            (vol_id, tag['Key']))
                    missing_tags.append(tag)
            if missing_tags:
                print("The Llama is adding tags %s to volume %s" % (
                        missing_tags, vol_id))
                client.create_tags(Resources=[vol_id], Tags=missing_tags)
    return {'Status': 'Success'}


