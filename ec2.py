#!/usr/bin/python

import lxml.objectify  # $ pip2 install lxml
import pdb  # for debugging
import qualysapi  # $ pip2 install qualysAPI
import subprocess
import sys
import time # for sleep time

def main():
    if (len(sys.argv) < 2):
        print 'You must specify a deployment environment in the first commandline parameter.'
        sys.exit(1)

    deployment_env = sys.argv[1]
    deployment_envs = set(['prod', 'stg'])
    if (deployment_env not in deployment_envs):
        print 'You must specify one of the following deployment environments: ' + ', '.join(deployment_envs)
        sys.exit(1)

    #regions being tested
    regions = ["us-east-1", "us-east-2", "us-west-1", "us-west-2", "ca-central-1", "ap-south-1", "ap-northeast-2",
        "ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "eu-central-1", "eu-west-1", "eu-west-2", "sa-east-1"]

    # Asset group in Qualys to modify:
    if (deployment_env == "prod"):
        qualys_asset_group = '_AWS_External_EC2s'
        scan_title = 'AWS_External_EC2_Instance_VScan_Daily-Script'
    elif (deployment_env == "stg"):
        qualys_asset_group = '_AWS_External_EC2s_STAGE'
        scan_title = 'AWS_External_EC2_STAGE_Instance_VScan_Daily-Script'
    else:
        print deployment_env + ' is an unsupported deplyment environment.'

    to_be_removed_group_id = '1705672'

    # scan_option_profile = 'PCI Pentration Test w/o password brute forcing'
    scan_option_profile = 'PCI Pentration Test w/o password brute forcing_SLOW_ELB'

    print '\n -------------- Qualys IP Address List --------------\n'

    # Connect to qualys using .qcrc file for credentials
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
    root = lxml.objectify.fromstring(xml_output)
    print root
    # pdb.set_trace()

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
    asset_group_ID = root.ASSET_GROUP.ID.text

    for ip in qualys_ip_list:
        print ip

    print '\n -------------- Zuora IP Address List --------------\n'

    ip_list = []
    ip_list_region = []
    # Call zi command to get list of ips
    for region in regions:
        zi_call = 'aws --profile ' + deployment_env + ' ec2 describe-instances --region ' + region
        zi_call += ' | grep -ai publicip | cut -d \"\\\"\" -f4 | sort | uniq'
        ec2add_call = 'aws --profile ' + deployment_env + ' ec2 describe-addresses --region ' + region
        ec2add_call += ' | grep -ai publicip | cut -d \"\\\"\" -f4 | sort | uniq'
        #print zi_call
        output = subprocess.Popen(zi_call, shell = True, stdout = subprocess.PIPE).communicate()[0]
        output_add = subprocess.Popen(ec2add_call, shell = True, stdout = subprocess.PIPE).communicate()[0]
        #print output

        # Test if zi call succeeded or failed
        if 'Max' not in output:
        # Convert output from zi call to list of IP addresses
            ip_list_region = output.split()
            ip_ec2_add = output_add.split()
            for ip in set(ip_ec2_add) - set(ip_list_region):
                print ip
                ip_list.append(ip)
            for ip in ip_list_region:
                print ip
                ip_list.append(ip)
        else:
            print 'zi command failed!\n'

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
            parameters = {'action': 'edit', 'id': to_be_removed_group_id, 'add_ips': ip}
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
            parameters = {'action': 'edit', 'id': asset_group_ID, 'remove_ips': ip}
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
            parameters = {'action': 'add', 'ips': ip, 'enable_vm': '1', 'echo_request': '1'}
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
            parameters = {'action': 'edit', 'id': asset_group_ID, 'add_ips': ip}
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
    #else:
    #   print '!!! zi command failed !!!\n'

    #google_sheets_credential_filename = 'google_sheets_credential.json'
    #google_workbook_name = 'AWS IPs'
    #google_worksheet_name = 'AWS_External'
    #google = google_sheet_init(google_sheets_credential_filename, google_workbook_name)
    #upload_to_sheet(google, google_worksheet_name, ip_list)

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
    parameters = {'action': 'launch', 'scan_title': scan_title, 'asset_groups': qualys_asset_group,
                  'option_title': scan_option_profile, 'echo_request': '1'}
    while True:
        try:
            xml_output = qgc.request(scan_call, parameters)
            break
        except:
            time.sleep(5)
            continue
    root = lxml.objectify.fromstring(xml_output)
    print 'launching scan ' + scan_title + ': ' + root.RESPONSE.TEXT.text

def google_sheet_init(google_sheets_credential_filename, google_workbook_name):
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(google_sheets_credential_filename, scope)
    google_sheets = gspread.authorize(credentials)
    workbook = google_sheets.open(google_workbook_name)
    return workbook

def upload_to_sheet(workbook, service, ip_list):
    print '\nUploading list ' + service + '...'

    output = workbook.worksheet(service)

    # delete current data while keeping heading row
    output.resize(rows=1)
    # get today's date and put in A1
    from datetime import date
    todays_date = date.today().isoformat()
    output.update_cell(1, 1, 'Status' + '(' + todays_date + ')')

    # check if ip_list is empty
    if ip_list:
        # calculate new size of worksheets
        num_rows = len(ip_list) + 1
        num_cols = 1  # len(ip_list[0])   # only for 2d lists
        # resize worksheets
        output.resize(rows=num_rows, cols=num_cols)

        # Get range of cells to update (FYI it skips the first row to leave the headings)
        letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S',
            'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'AA']
        cell_range = 'A2:' + letters[num_cols - 1] + str(num_rows)

        # get cells in that range
        all_cells = output.range(cell_range)

        # flatten list of users so they can be iterated through (only for 2d lists)
        #ip_list = [item for sublist in ip_list for item in sublist]

        # update values in cells
        for i, cell in enumerate(all_cells):
            cell.value = ip_list[i]

        # Upload new cell list
        output.update_cells(all_cells)

    print ' done'

if __name__ == '__main__':
    main()
