# Cisco Public IP Retrieval Script

This script retrieves device and interface information from a Cisco vManage server, filters and processes the data to export it into an Excel and HTML file.

## Prerequisites

- Python 3.x
- `requests` library
- `ipaddress` library
- `xlsxwriter` library
- Custom `store_creds` module for managing credentials

## Installation

Install the necessary Python libraries using pip:  

pip install requests xlsxwriter  

Ensure the `store_creds.py` is present in the same directory or accessible in your Python path.

## Usage
get_vEdgeAddresses.py -a <vManage_IP_Address>  

Retrieve IP's from specified vManage server using defaults for all other fields. 
  
Additional Arguments:    
-a, --vmanage_address: The IP address of the vManage server (Required)    
-p, --password_file: The file to store or retrieve credentials (Default: vManageCreds.txt)    
-l, --log_file: The filename for logging (Default: RetrieveCiscoPublicIP.log)  
-o, --output_file: The base filename for the output files (Omit extension, script will append .xlsx and .html)    
-i, --ignore_list: A list of interfaces to ignore (Space separated, e.g., "ge0/0.22 ge0/0.23")  
  
get_vEdgeAddresses.py -a <vManage_IP_Address> -p <Password_File_Path> -l <Log_File_Path> -o <Output_File_Base> -i <Ignore_Interface_List>  
  
## Example

get_vEdgeAddresses.py -a 10.x.y.z -p vManageCreds.txt -l RetrieveCiscoPublicIP.log -o CiscoPublicIPs -i "ge0/0.22 ge0/0.23"

* The script will connect to vManage server '10.x.y.z' to retrieve a list of connected devices
* It will use (or create) credentials found in 'vManageCreds.txt'
  * Do NOT misunderstand. The contents of this file are "Encoded", NOT "Encrypted".   
    If the significance of this is not clear, stop, and do not use this script.
* Script activity will be logged to 'RetrieveCiscoPublicIP.log'
* Script will generate CiscoPublicIPs.xlsx and CiscoPublicIPs.html listing the public IP's for all vEdges connected to given vManage server
* ***except*** for interfaces ge0/0.22 and 0/0.23 (Which could be used for HA or other inapplicable purposes) 

## License

GPL-3.0