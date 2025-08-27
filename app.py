from flask import Flask, render_template, request, redirect, url_for, flash
import boto3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this!

@app.route('/', methods=['GET', 'POST'])
def index():
    ec2 = boto3.client('ec2')
    keypairs = [kp['KeyName'] for kp in ec2.describe_key_pairs()['KeyPairs']]
    if request.method == 'POST':
        home_ip = request.form['home_ip']
        keypair = request.form['keypair']
        ami_id = request.form['ami_id']
        instance_type = request.form['instance_type']

        try:
            ec2_resource = boto3.resource('ec2')

            # 1. Create VPC
            vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
            vpc_id = vpc['Vpc']['VpcId']
            ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
            ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
            ec2.create_tags(Resources=[vpc_id], Tags=[{'Key': 'Name', 'Value': 'lab1-custom'}])

            # 2. Create Internet Gateway and attach to VPC
            igw = ec2.create_internet_gateway()
            igw_id = igw['InternetGateway']['InternetGatewayId']
            ec2.attach_internet_gateway(VpcId=vpc_id, InternetGatewayId=igw_id)

            # 3. Create public subnet and enable auto-assign public IP
            subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')
            subnet_id = subnet['Subnet']['SubnetId']
            ec2.modify_subnet_attribute(SubnetId=subnet_id, MapPublicIpOnLaunch={'Value': True})

            # 4. Create Route Table and route to IGW
            rt = ec2.create_route_table(VpcId=vpc_id)
            rt_id = rt['RouteTable']['RouteTableId']
            ec2.create_route(RouteTableId=rt_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)
            ec2.associate_route_table(SubnetId=subnet_id, RouteTableId=rt_id)

            # 5. Create Security Groups
            sga = ec2.create_security_group(GroupName='SGA', Description='Security Group A', VpcId=vpc_id)
            sgb = ec2.create_security_group(GroupName='SGB', Description='Security Group B', VpcId=vpc_id)
            sga_id = sga['GroupId']
            sgb_id = sgb['GroupId']

            # Add rules to SGA
            ec2.authorize_security_group_ingress(GroupId=sga_id,
                IpPermissions=[
                    {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                    {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                ])

            # Add rules to SGB (initially allow all HTTP)
            ec2.authorize_security_group_ingress(GroupId=sgb_id,
                IpPermissions=[
                    {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                ])

            # 6. Launch EC2 instances separately
            user_data_script = '''#!/bin/bash
            yum update -y
            yum install -y httpd
            systemctl start httpd
            systemctl enable httpd
            echo "<h1>Welcome to our EC2 Instance </h1>" > /var/www/html/index.html
            '''
            instance_a = ec2_resource.create_instances(
                ImageId=ami_id,
                InstanceType=instance_type,
                KeyName=keypair,
                MaxCount=1,
                MinCount=1,
                NetworkInterfaces=[{
                    'SubnetId': subnet_id,
                    'DeviceIndex': 0,
                    'AssociatePublicIpAddress': True,
                    'Groups': [sga_id]
                }],
                UserData=user_data_script
            )[0]

            instance_b = ec2_resource.create_instances(
                ImageId=ami_id,
                InstanceType=instance_type,
                KeyName=keypair,
                MaxCount=1,
                MinCount=1,
                NetworkInterfaces=[{
                    'SubnetId': subnet_id,
                    'DeviceIndex': 0,
                    'AssociatePublicIpAddress': True,
                    'Groups': [sgb_id]
                }], 
                UserData=user_data_script 
                 )[0]

            # Wait for both instances to be running
            for instance in [instance_a, instance_b]:
                instance.wait_until_running()
                instance.reload()

            instances = [instance_a, instance_b]

            # # 7. Restrict SGA HTTP to home IP
            # ec2.revoke_security_group_ingress(GroupId=sga_id,
            #     IpProtocol='tcp', FromPort=80, ToPort=80, CidrIp='0.0.0.0/0')
            # ec2.authorize_security_group_ingress(GroupId=sga_id,
            #     IpProtocol='tcp', FromPort=80, ToPort=80, CidrIp=home_ip)

            # # 8. Create and configure NACL to deny from home IP
            # nacl = ec2.create_network_acl(VpcId=vpc_id)
            # nacl_id = nacl['NetworkAcl']['NetworkAclId']
            # ec2.create_network_acl_entry(
            #     NetworkAclId=nacl_id, RuleNumber=100, Protocol='-1',
            #     RuleAction='deny', Egress=False, CidrBlock=home_ip
            # )
            # nacl_resource = ec2_resource.NetworkAcl(nacl_id)
            # try:
            #     nacl_resource.associate_with_subnets(SubnetIds=[subnet_id])
            # except Exception as e:
            #     flash(f"NACL association warning: {e}")

            # # 9. Update SGB to only allow HTTP from SGA
            # ec2.revoke_security_group_ingress(GroupId=sgb_id,
            #     IpProtocol='tcp', FromPort=80, ToPort=80, CidrIp='0.0.0.0/0')
            # ec2.authorize_security_group_ingress(GroupId=sgb_id,
            #     IpProtocol='tcp', FromPort=80, ToPort=80,
            #     UserIdGroupPairs=[{'GroupId': sga_id}])

            # 10. Enable ICMP both directions
            for sg_id in [sga_id, sgb_id]:
                ec2.authorize_security_group_ingress(GroupId=sg_id,
                    IpPermissions=[{'IpProtocol': 'icmp', 'FromPort': -1, 'ToPort': -1, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}])

            public_ips = [i.public_ip_address for i in instances]
            return render_template('result.html', public_ips=public_ips)

        except Exception as e:
            flash(str(e))
            return redirect(url_for('index'))

    return render_template('index.html', keypairs=keypairs)

@app.route('/resources')
def resources():
    ec2 = boto3.client('ec2')
    vpcs = ec2.describe_vpcs()['Vpcs']
    subnets = ec2.describe_subnets()['Subnets']
    sgs = ec2.describe_security_groups()['SecurityGroups']
    instances = ec2.describe_instances()['Reservations']
    return render_template('resources.html', vpcs=vpcs, subnets=subnets, sgs=sgs, instances=instances)

@app.route('/security-groups', methods=['GET', 'POST'])
def security_groups():
    ec2 = boto3.client('ec2')
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        group_id = request.form['group_id']
        ip_protocol = request.form['ip_protocol']
        from_port = int(request.form['from_port'])
        to_port = int(request.form['to_port'])
        cidr_ip = request.form['cidr_ip']
        try:
            if action == 'add':
                ec2.authorize_security_group_ingress(
                    GroupId=group_id,
                    IpPermissions=[{
                        'IpProtocol': ip_protocol,
                        'FromPort': from_port,
                        'ToPort': to_port,
                        'IpRanges': [{'CidrIp': cidr_ip}]
                    }]
                )
                flash('Rule added successfully!')
            elif action == 'delete':
                ec2.revoke_security_group_ingress(
                    GroupId=group_id,
                    IpPermissions=[{
                        'IpProtocol': ip_protocol,
                        'FromPort': from_port,
                        'ToPort': to_port,
                        'IpRanges': [{'CidrIp': cidr_ip}]
                    }]
                )
                flash('Rule deleted successfully!')
        except Exception as e:
            flash(str(e))
        return redirect(url_for('security_groups'))
    sgs = ec2.describe_security_groups()['SecurityGroups']
    return render_template('security_groups.html', sgs=sgs)

@app.route('/network-acls', methods=['GET', 'POST'])
def network_acls():
    ec2 = boto3.client('ec2')
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        nacl_id = request.form['nacl_id']
        rule_number = int(request.form['rule_number'])
        egress = request.form.get('egress', 'false') == 'true'
        try:
            if action == 'add':
                protocol = request.form['protocol']
                rule_action = request.form['rule_action']
                cidr_block = request.form['cidr_block']
                ec2.create_network_acl_entry(
                    NetworkAclId=nacl_id,
                    RuleNumber=rule_number,
                    Protocol=protocol,
                    RuleAction=rule_action,
                    Egress=egress,
                    CidrBlock=cidr_block
                )
                flash('NACL rule added successfully!')
            elif action == 'delete':
                ec2.delete_network_acl_entry(
                    NetworkAclId=nacl_id,
                    RuleNumber=rule_number,
                    Egress=egress
                )
                flash('NACL rule deleted successfully!')
        except Exception as e:
            flash(str(e))
        return redirect(url_for('network_acls'))
    nacls = ec2.describe_network_acls()['NetworkAcls']
    return render_template('network_acls.html', nacls=nacls)

if __name__ == '__main__':
    app.run(debug=True)