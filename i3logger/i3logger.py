import base64
import json
import os
from os import path

import boto3

from iota import api

for variable in [
    'CACHE_BUCKET', 'CACHE_KEY', 'CLOUDWATCH_NAMESPACE', 'VEHICLE_VIN',
]:
    vars()[variable] = os.environ[variable]

kms_client = boto3.client('kms')
for variable in [
    'API_KEY', 'API_SECRET', 'CONNECTEDDRIVE_USERNAME',
    'CONNECTEDDRIVE_PASSWORD',
]:
    vars()[variable] = str(kms_client.decrypt(CiphertextBlob=base64.b64decode(
        os.environ[variable]
    ))['Plaintext'], 'utf8')


def lambda_handler(event: dict, context):
    """Main entrypoint called by the AWS Lambda service.

    :param event:
    :param context:
    """

    access_token, refresh_token = load_cached_tokens(CACHE_BUCKET, CACHE_KEY)
    bmw_api_client = api.BMWiApiClient(
        API_KEY, API_SECRET, CONNECTEDDRIVE_USERNAME,
        CONNECTEDDRIVE_PASSWORD, refresh_token=refresh_token,
        access_token=access_token
    )

    my_i3 = bmw_api_client.get_vehicle(VEHICLE_VIN)
    metric_data = [
        {
            'MetricName': 'BatteryCharge',
            'Dimensions': [
                {
                    'Name': 'VIN',
                    'Value': VEHICLE_VIN,
                },
            ],
            'Value': my_i3.charge.percentage,
            'Unit': 'Percent',
            'StorageResolution': 60,
        },
        {
            'MetricName': 'MinutesUntilFullyCharged',
            'Dimensions': [
                {
                    'Name': 'VIN',
                    'Value': VEHICLE_VIN,
                },
            ],
            'Value': my_i3.charge.minutes_until_full if my_i3.charge.minutes_until_full != 'N/A' else 0,
            'Unit': 'Count',
            'StorageResolution': 60,
        },
        {
            'MetricName': 'OdometerKilometers',
            'Dimensions': [
                {
                    'Name': 'VIN',
                    'Value': VEHICLE_VIN,
                },
            ],
            'Value': my_i3.mileage,
            'Unit': 'Count',
            'StorageResolution': 60,
        },
    ]
    cloudwatch_client = boto3.client('cloudwatch')
    cloudwatch_client.put_metric_data(
        Namespace=CLOUDWATCH_NAMESPACE, MetricData=metric_data
    )

    save_token_cache(
        CACHE_BUCKET, CACHE_KEY, bmw_api_client.access_token,
        bmw_api_client.refresh_token
    )


def load_cached_tokens(bucket: str, key: str) -> tuple:
    """Retrieve cached OAuth tokens from a S3 bucket.

    Args:
        bucket: A S3 bucket to retrieve the cache from.
        key: A S3 key inside the bucket to load tokens from.

    Returns:
        An OAuth access token and refresh token, or None if no cached tokens
        could be loaded.
    """

    if not path.isfile('/tmp/i3logger-cache'):
        s3_resource = boto3.resource('s3')
        cache_bucket = s3_resource.Bucket(bucket)
        cache_bucket.download_file(key, '/tmp/i3logger-cache')

    with open('/tmp/i3logger-cache') as cache_file:
        cache_dict = json.load(cache_file)

    return cache_dict['access_token'], cache_dict['refresh_token']


def save_token_cache(
    bucket: str, key: str, access_token: str, refresh_token: str
):
    """Save OAuth tokens to a S3 bucket.

    Args:
        bucket: A S3 bucket to save the cache to.
        key: A S3 key inside the bucket to save cache as.
        access_token: BMW API OAuth access token.
        refresh_token: BMW API OAuth refresh token.
    """

    with open('/tmp/i3logger-cache', 'w') as cache_file:
        json.dump({
            'access_token': access_token,
            'refresh_token': refresh_token,
        }, cache_file)

    s3_resource = boto3.resource('s3')
    cache_bucket = s3_resource.Bucket(bucket)
    cache_bucket.upload_file('/tmp/i3logger-cache', key)
