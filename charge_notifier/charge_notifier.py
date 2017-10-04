import os
from os import path

import boto3

EMAIL_TEMPLATE = 'email.html'
SMS_MESSAGE = 'Your BMW i3 is fully charged.'

EMAIL_ADDRESS = os.environ['EMAIL_ADDRESS']
FROM_ADDRESS = os.environ['FROM_ADDRESS']
PHONE_NUMBER = os.environ['TARGET_TOPIC']


def lambda_handler(event: dict, context):
    """

    :param event:
    :param context:
    :return:
    """

    sns_client = boto3.client('sns')
    sns_client.publish(PhoneNumber=PHONE_NUMBER, Message=SMS_MESSAGE)

    with open(path.join(path.dirname(__file__), EMAIL_TEMPLATE)) as html_file:
        html_template = html_file.read()
    message_text = html_template.format(image_data='')
    ses_client = boto3.client('ses')
    ses_client.send_email(
        Source=FROM_ADDRESS, Destination={
            'ToAddresses': [
                EMAIL_ADDRESS,
            ],
        }, Message={
            'Subject': {
                'Data': 'Your i3 Is Charged',
            },
            'Body': {
                'Html': {
                    'Data': message_text,
                },
            },
        }
    )
