# AWS Lab Orchestrator

A Flask web application to automate the creation and management of AWS lab environments. Instantly set up VPCs, subnets, EC2 instances, security groups, and network ACLs through a modern web interface. Ideal for cloud labs, demos, and training environments.

## Features
- Create a secure AWS lab environment with a web form
- View all AWS resources (VPCs, subnets, security groups, EC2 instances)
- Add and remove security group rules
- Add and remove network ACL rules
- Modern, responsive UI with Bootstrap

## Prerequisites
- Python 3.8+
- An AWS account with programmatic access (Access Key ID and Secret Access Key)
- AWS credentials configured on your machine (see below)

## Setup Instructions

1. **Clone the repository:**
   ```sh
   git clone https://github.com/nwokehenry90/aws-lab-orchestrator.git
   cd aws-lab-orchestrator
   ```

2. **Create and activate a virtual environment:**
   ```sh
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Configure AWS credentials:**
   - Run `aws configure` and enter your AWS Access Key, Secret Key, and default region.
   - Or set environment variables:
     ```sh
     set AWS_ACCESS_KEY_ID=your_access_key_id
     set AWS_SECRET_ACCESS_KEY=your_secret_access_key
     set AWS_DEFAULT_REGION=your_region
     ```

5. **Run the application:**
   ```sh
   python app.py
   ```
   The app will be available at [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Usage
- **Home:** Fill out the form to launch a new AWS lab environment.
- **Resources:** View all VPCs, subnets, security groups, and EC2 instances.
- **Security Groups:** Add or remove ingress rules for any security group.
- **Network ACLs:** Add or remove rules for any network ACL.

## Notes
- Make sure your AWS account has sufficient permissions to create and manage VPCs, EC2, security groups, and network ACLs.
- All resources are created in the region specified in your AWS configuration.
- Remember to clean up resources in your AWS account to avoid unnecessary charges.

## Acknowledgements
- Original project idea by [Your Friend's Name].
- Flask app and automation logic by [Your Name].

## License
MIT License
