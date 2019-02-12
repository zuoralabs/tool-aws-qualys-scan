#!/usr/bin/python

import boto3
import lxml.objectify  # $ pip2 install lxml
import os
import pdb  # for debugging
import qualysapi  # $ pip2 install qualysAPI
import socket
import subprocess
import sys
import time # for sleep time

def create_options_map():
    options_map = {
        'beanstalk' : {
            'prod' : ('_AWS_External_BEANSTALKs', 'AWS_External_BEANSTALK_Instance_VScan_Daily-Script'),
            'stg' : ('_AWS_External_BEANSTALKs_STAGE', 'AWS_External_BEANSTALK_STAGE_Instance_VScan_Daily-Script')
        },
        'ec2' : {
            'prod' : ('_AWS_External_EC2s', 'AWS_External_EC2_Instance_VScan_Daily-Script'),
            'stg' : ('_AWS_External_EC2s_STAGE', 'AWS_External_EC2_STAGE_Instance_VScan_Daily-Script')
        },
        'elb' : {
            'prod' : ('_AWS_External_ELBs', 'AWS_External_ELB_Instance_VScan_Daily-Script'),
            'stg' : ('_AWS_External_ELBs_STAGE', 'AWS_External_ELB_STAGE_Instance_VScan_Daily-Script')
        },
        'elbv2' : {
            'prod' : ('_AWS_External_ELBV2s', 'AWS_External_ELBV2_Instance_VScan_Daily-Script'),
            'stg' : ('_AWS_External_ELBV2s_STAGE', 'AWS_External_ELBV2_STAGE_Instance_VScan_Daily-Script')
        },
        'rds' : {
            'prod' : ('_AWS_External_RDSs', 'AWS_External_RDS_Instance_VScan_Daily-Script'),
            'stg' : ('_AWS_External_RDSs_STAGE', 'AWS_External_RDS_STAGE_Instance_VScan_Daily-Script')
        }
    }
    return options_map

def build_profile_param(profile):
    if (profile == ''):
        return ''
    else:
        return ' --profile ' + profile

def build_ip_list_display_name(aws_resource, profile):
    if (profile == ''):
        profile_display_name = 'default'
    else:
        profile_display_name = '\'' + profile + '\''

    ip_list_display_name = '\n -------------- AWS ' + profile_display_name + ' profile '
    ip_list_display_name += aws_resource + ' IP Address List --------------\n'
    return ip_list_display_name

def is_private_ip_address(ip_address):
    ip_private = "10"
    return str(ip_address)[:2] == ip_private[:2]

def get_beanstalk_ip_list(regions, profile):
    print build_ip_list_display_name("Elastic Beanstalk", profile)

    ip_list = []
    for region_name in regions:
        client = boto3.client('elasticbeanstalk', region_name=region_name)
        response = client.describe_environments()
        environments = response['Environments']
        for environment in environments:
            if 'EndpointURL' in environment:
                endpoint_url = environment['EndpointURL']
                try:
                    ip = socket.gethostbyname(endpoint_url)
                    if not is_private_ip_address(ip):
                        ip_list.append(ip)
                        print ip
                except:
                    print "DNS could not resolve the IP address for: " + endpoint_url
        time.sleep(1) #Prevent rate limiting

    return ip_list


def get_ec2_ip_list(regions, profile):
    print build_ip_list_display_name("EC2", profile)

    instance_ip_list = []
    address_ip_list = []
    for region_name in regions:
        client = boto3.client('ec2', region_name=region_name)
        paginator = client.get_paginator('describe_instances')
        response_iterator = paginator.paginate(PaginationConfig={'PageSize' : 10})
        for page in response_iterator:
            reservations = page['Reservations']
            for reservation in reservations:
                instances = reservation['Instances']
                for instance in instances:
                    if 'PublicIpAddress' in instance:
                        ip = instance['PublicIpAddress']
                        instance_ip_list.append(ip)

        response = client.describe_addresses()
        addresses = response['Addresses']
        for address in addresses:
            ip = address['PublicIp']
            address_ip_list.append(ip)

        time.sleep(1) #Prevent rate limiting

    ip_list = []
    for ip in set(address_ip_list) - set(instance_ip_list):
        ip_list.append(ip)
        print ip
    for ip in instance_ip_list:
        ip_list.append(ip)
        print ip
    return ip_list


def get_elb_ip_list(regions, profile):
    print build_ip_list_display_name("ELB", profile)

    ip_list = []
    for region_name in regions:
        client = boto3.client('elb', region_name=region_name)
        paginator = client.get_paginator('describe_load_balancers')
        response_iterator = paginator.paginate(PaginationConfig={'PageSize' : 10})
        for page in response_iterator:
            load_balancers = page['LoadBalancerDescriptions']
            for load_balancer in load_balancers:
                dns_name = load_balancer['DNSName']
                ip = socket.gethostbyname(dns_name)
                if not is_private_ip_address(ip):
                    ip_list.append(ip)
                    print ip
        time.sleep(1) #Prevent rate limiting

    return ip_list


def get_elbv2_ip_list(regions, profile):
    print build_ip_list_display_name("ELBv2", profile)

    ip_list = []
    for region_name in regions:
        client = boto3.client('elbv2', region_name=region_name)
        paginator = client.get_paginator('describe_load_balancers')
        response_iterator = paginator.paginate(PaginationConfig={'PageSize' : 10})
        for page in response_iterator:
            load_balancers = page['LoadBalancers']
            for load_balancer in load_balancers:
                dns_name = load_balancer['DNSName']
                ip = socket.gethostbyname(dns_name)
                if not is_private_ip_address(ip):
                    ip_list.append(ip)
                    print ip
        time.sleep(1) #Prevent rate limiting

    return ip_list


def get_rds_ip_list(regions, profile):
    print build_ip_list_display_name("RDS", profile)

    ip_list = []
    for region_name in regions:
        client = boto3.client('rds', region_name=region_name)
        paginator = client.get_paginator('describe_db_instances')
        response_iterator = paginator.paginate(PaginationConfig={'PageSize' : 100})
        for page in response_iterator:
            db_instances = page['DBInstances']
            for db_instance in db_instances:
                address = db_instance['Endpoint']['Address']
                ip = socket.gethostbyname(address)
                if not is_private_ip_address(ip):
                    ip_list.append(ip)
                    print ip

        time.sleep(1) #Prevent rate limiting

    return ip_list


def main():
    if (len(sys.argv) <= 1):
        qualys_asset_group = os.getenv('QUALYS_ASSET_GROUP', '')
        if (qualys_asset_group == ''):
            print "You must either specify input parameters or environment variables."
            sys.exit(1)

        qualys_scan_title = os.getenv('QUALYS_SCAN_TITLE', '')
        if (qualys_scan_title == ''):
            print "You must either specify input parameters or environment variables."
            sys.exit(1)

        qualys_username = os.getenv('QUALYS_USERNAME', '')
        if (qualys_username == ''):
            print "You must either specify input parameters or environment variables."
            sys.exit(1)

        qualys_password = os.getenv('QUALYS_PASSWORD', '')
        if (qualys_password == ''):
            print "You must either specify input parameters or environment variables."
            sys.exit(1)

        aws_resource = os.getenv('AWS_RESOURCE', 'ec2')
        op = os.getenv('AWS_QUALYS_SCAN_OP', 'normal')
        profile = ''

        fh = os.fdopen(os.open('aws-qualys-scan.qcrc', os.O_WRONLY | os.O_TRUNC | os.O_CREAT, 0o600), 'w')
        fh.write('[DEFAULT]\n')
        fh.write('max_retries = 3\n')
        fh.write('hostname = qualysapi.qualys.com\n')
        fh.write('\n')
        fh.write('[info]\n')
        fh.write('max_retries = 3\n')
        fh.write('username = ' + qualys_username + '\n')
        fh.write('password = ' + qualys_password + '\n')
        fh.close()
        use_dedicated_config=True

    elif ((len(sys.argv) > 1) and (len(sys.argv) < 3)):
        print "You must specify 2 parameters: the asset group and AWS profile."
        print '\taws-qualys-scan [beanstalk|ec2|elb|elbv2|rds] [profile]'
        sys.exit(1)

    else:
        aws_resource = sys.argv[1]
        supported_aws_resources = set(['beanstalk', 'ec2', 'elb', 'elbv2', 'rds'])
        if (aws_resource not in supported_aws_resources):
            print 'You must specify one of the following asset groups: ' + ', '.join(supported_aws_resources)
            sys.exit(1)

        profile = sys.argv[2]
        profiles = set(['prod', 'stg'])
        if (profile not in profiles):
            print 'You must specify one of the following profiles: ' + ', '.join(profiles)
            sys.exit(1)

        options_map = create_options_map()
        # Asset group in Qualys to modify:
        qualys_asset_group = options_map[aws_resource][profile][0]
        # Scan title:
        qualys_scan_title = options_map[aws_resource][profile][1]

        if (len(sys.argv) > 3):
            op = sys.argv[3]
        else:
            op = 'normal'

        use_dedicated_config=False

    #regions being tested
    regions = ["us-east-1", "us-east-2", "us-west-1", "us-west-2", "ca-central-1", "ap-south-1", "ap-northeast-2",
        "ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "eu-central-1", "eu-west-1", "eu-west-2", "sa-east-1"]

    to_be_removed_group_id = '1705672'

    # scan_option_profile = 'PCI Pentration Test w/o password brute forcing'
    scan_option_profile = 'PCI Pentration Test w/o password brute forcing_SLOW_ELB'

    print '\n -------------- Qualys \'' + qualys_asset_group + '\' Asset Group IP Address List --------------\n'

    # Connect to qualys using .qcrc file for credentials
    if (use_dedicated_config):
        qgc = qualysapi.connect('aws-qualys-scan.qcrc')
    else:
        qgc = qualysapi.connect(remember_me = True)

    # The call is our request's first parameter.
    call = 'asset_group_list.php?'
    # The parameters to append to the url is our request's second parameter.
    parameters = 'title=' + qualys_asset_group
    # Note qualysapi will automatically convert spaces into plus signs for API v1 & v2.
    # Let's call the API and store the result in xml_output.
    while True:
        try:
            xml_output = qgc.request(call, parameters)
            break
        except:
            time.sleep(5)
            continue

    # Convert xml output to tree
    try:
        root = lxml.objectify.fromstring(xml_output)
    except:
        print xml_output
        sys.exit(1)

    # variable for list of IP addresses from Qualys
    qualys_ip_list = []

    # boolean to tell if list is empty
    empty_list = True

    # check if list is empty
    try:
        root.ASSET_GROUP.SCANIPS.IP
        empty_list = False
    except AttributeError:
        print "No IP addresses in Qualys group"

    if empty_list == False:
        # Iterate through IP addresses in XML tree and add to IP address list
        for ip in root.ASSET_GROUP.SCANIPS.IP:
            qualys_ip_list.append(ip.text)

    # Save asset group ID (needed to modify group later)
    qualys_asset_group_id = root.ASSET_GROUP.ID.text

    for ip in qualys_ip_list:
        print ip

    if (aws_resource == 'beanstalk'):
        ip_list = get_beanstalk_ip_list(regions, profile)
    elif (aws_resource == 'ec2'):
        ip_list = get_ec2_ip_list(regions, profile)
    elif (aws_resource == 'elb'):
        ip_list = get_elb_ip_list(regions, profile)
    elif (aws_resource == 'elbv2'):
        ip_list = get_elbv2_ip_list(regions, profile)
    elif (aws_resource == 'rds'):
        ip_list = get_rds_ip_list(regions, profile)
    else:
        print aws_resource + ' is not a supported AWS resource.\n'
        sys.exit(1)

    if (op == 'noupdate'):
        sys.exit(0)

    # Qualys Call parameters
    asset_call = '/api/2.0/fo/asset/ip/?'
    group_call = '/api/2.0/fo/asset/group/?'
    purge_call = '/api/2.0/fo/asset/host/?'

    print '\n -------------- Difference --------------\n'

    if set(qualys_ip_list) != set(ip_list):
        print 'Lists do not match. Updating Qualys List...'

        print '\nRemoving from Qualys:'
        for ip in set(qualys_ip_list) - set(ip_list):
            # Adding IP address to Qualys group
            parameters = {
                'action' : 'edit',
                'id' : to_be_removed_group_id,
                'add_ips' : ip
            }

            while True:
                try:
                    xml_output = qgc.request(group_call, parameters)
                    break
                except:
                    time.sleep(5)
                    continue
            root = lxml.objectify.fromstring(xml_output)
            print ip + ': ' + root.RESPONSE.TEXT.text

            # Removing IP address from Qualys group
            parameters = {
                'action' : 'edit',
                'id' : qualys_asset_group_id,
                'remove_ips' : ip
            }

            while True:
                try:
                    xml_output = qgc.request(group_call, parameters)
                    break
                except:
                    time.sleep(5)
                    continue
            root = lxml.objectify.fromstring(xml_output)
            print ip + ': ' + root.RESPONSE.TEXT.text

        print '\nAdding to Qualys:'
        for ip in set(ip_list) - set(qualys_ip_list):
            # Adding IP address to Qualys
            parameters = {
                'action' : 'add',
                'ips' : ip,
                'enable_vm' : '1',
                'echo_request' : '1'
            }

            while True:
                try:
                    xml_output = qgc.request(asset_call, parameters)
                    break
                except:
                    time.sleep(5)
                    continue
            root = lxml.objectify.fromstring(xml_output)
            print ip + ': ' + root.RESPONSE.TEXT.text

            # Adding IP address to Qualys group
            parameters = {
                'action' : 'edit',
                'id' : qualys_asset_group_id,
                'add_ips' : ip
            }

            while True:
                try:
                    xml_output = qgc.request(group_call, parameters)
                    break
                except:
                    time.sleep(5)
                    continue
            root = lxml.objectify.fromstring(xml_output)
            print ip + ': ' + root.RESPONSE.TEXT.text

        print '\n -------------- Updated ' + qualys_asset_group + ' Asset Group --------------\n'

        call = 'asset_group_list.php?'
        parameters = 'title=' + qualys_asset_group
        while True:
            try:
                xml_output = qgc.request(call, parameters)
                break
            except:
                time.sleep(5)
                continue
        root = lxml.objectify.fromstring(xml_output)
        for ip in root.ASSET_GROUP.SCANIPS.IP:
            print ip.text
    else:
        print 'Lists already up to date, no changes made'

    if (op == 'noscan'):
        sys.exit(0)

    print 'Preparing to Launch Scan'
    time.sleep(10)
    print '.'
    time.sleep(10)
    print '.'
    time.sleep(10)
    print '.'
    time.sleep(10)
    print '.'
    time.sleep(10)
    print '.'
    time.sleep(10)
    print '.'

    # Launching Qualys scan
    scan_call = '/api/2.0/fo/scan/?'
    parameters = {
        'action' : 'launch',
        'scan_title' : qualys_scan_title,
        'asset_groups' : qualys_asset_group,
        'option_title' : scan_option_profile,
        'echo_request' : '1'
    }

    while True:
        try:
            xml_output = qgc.request(scan_call, parameters)
            break
        except:
            time.sleep(5)
            continue
    root = lxml.objectify.fromstring(xml_output)
    print 'launching scan ' + qualys_scan_title + ': ' + root.RESPONSE.TEXT.text

if __name__ == '__main__':
    main()
