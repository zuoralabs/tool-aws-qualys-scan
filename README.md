
# User guide

## aws-qualys-scan.py
Gets list of public IP addresses for EC2 or ELB instances from AWS and updates them in Qualys.
Before using this script you will need:
* QualysGuard credentials in a .qcrc file otherwise the script will prompt you for credentials.
* AWS profiles `prod` for production account and/or `stg` for staging account.

Usage:
`python aws-qualys-scan.py [beanstalk|ec2|elb|elbv2|rds] [profile]`

Where currently the only two supported profiles are `prod` and `stg`.

You can collect IP addresses but skip the Qualys update with the `noupdate` option

e.g. `python aws-qualys-scan.py ec2 stg noupdate`

You can collect IP addresses, update Qualys, but skip scheduling a scan with the `noscan` option

e.g. `python aws-qualys-scan.py ec2 stg noscan`

## Environment Variable Driven Configuration
Rather than specify command line parameters you can configure the script through environment variables.
This is useful if you want to run the script through automation. Here's an example:
```
export QUALYS_ASSET_GROUP=_AWS_External_EC2s_STAGE
export QUALYS_SCAN_TITLE=AWS_External_EC2_Instance_VScan_Daily-Script
export AWS_QUALYS_SCAN_OP=noupdate # Optional
export QUALYS_USERNAME=qualys_username_goes_here
export QUALYS_PASSWORD=qualys_password_goes_here
export AWS_RESOURCE=ec2
export AWS_PROFILE=stg # Optional, will use the default profile or IAM role credentials if omitted

python aws-qualys-scan.py
```

## ec2.py (DEPRECATED USE aws-qualys-scan.py)
Gets list of public IP addresses for EC2 instances from AWS and updates them in Qualys.
Before using this script you will need:
* QualysGuard credentials in a .qcrc file otherwise the script will prompt you for credentials.
* AWS profiles `prod` for production account and/or `stg` for staging account.

Usage:
`python ec2.py [profile]`

Where currently the only two supported profiles are `prod` and `stg`.

## elb.py (DEPRECATED USE aws-qualys-scan.py)
Gets list of public IP addresses for ELBs from AWS and updates them in Qualys.
Before using this script you will need:
* QualysGuard credentials in a .qcrc file otherwise the script will prompt you for credentials.
* AWS profiles `prod` for production account and/or `stg` for staging account.

Usage:
`python elb.py [profile]`

Where currently the only two supported profiles are `prod` and `stg`.
