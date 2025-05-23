import requests
import os
import ipaddress
from xlsxwriter import Workbook
import store_creds
import logging
import argparse

# Disable warnings about private certs since we're not able to verify the vManage's cert against a public CA'
requests.packages.urllib3.disable_warnings()


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Script to retrieve device and interface information from vManage.")
    parser.add_argument('-a', '--vmanage_address', required=True,
                        help='The IP address of the vManage server')
    parser.add_argument('-p', '--password_file', default='vManageCreds.txt',
                        help='The file to store or retrieve credentials')
    parser.add_argument('-l', '--log_file', default='RetrieveCiscoPublicIP.log',
                        help='The filename for logging')
    parser.add_argument('-o', '--output_file', default='CiscoPublicIPs',
                        help='The base filename for the output files (Omit extension, script will append .xlsx and .html)')
    parser.add_argument('-i', '--ignore_list', nargs='+', default=['ge0/0.22'],
                        help='A list of interfaces to ignore (Space separated e.g., " ge0/0.22 ge0/0.23  ")')
    return parser.parse_args()


def is_ipv4(address: str) -> bool:
    """
    Check if the provided address is a valid IPv4 network or host address.

    Args:
        address (str): The IP address or network to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        ipaddress.ip_network(address, strict=False)
        return True
    except ValueError:
        return False


def fetch_raw_json(query_url: str, auth: tuple) -> list:
    """
    Fetch device data from the given URL using the provided authentication.

    Args:
        query_url (str): The URL to be retrieved
        auth (tuple): Authentication tuple (username, password)

    Returns:
        list: List of data from the response
    """
    try:
        response = requests.get(query_url, auth=auth, verify=False)
        response.raise_for_status()
        return response.json().get('data', [])
    except requests.RequestException as e:
        logging.error(f"HTTP request failed: {e}")
        return []


def format_device_data(raw_devices: list, keys: list) -> dict:
    """
    Format raw device information into a dictionary, pruned to only requested fields in key list.

    Args:
        raw_devices (list): List of raw device data
        keys (list): List of keys to extract from device data

    Returns:
        dict: Formatted device data dictionary
    """
    devices = {}
    for device in raw_devices:
        system_ip = device['system-ip']
        device_data = {key: device.get(key, "N/A") for key in keys}
        devices[system_ip] = device_data
    return devices


def add_interface_info(devices: dict, auth: tuple, interface_query_base_url: str, ignore_interface_list: list) -> dict:
    """
    Gather interface information and update the provided dictionary in place.

    Args:
        devices (dict): Dictionary of device data
        auth (tuple): Authentication tuple (username, password)
        interface_query_base_url (str): Base URL for querying interfaces
        ignore_interface_list (list): List of interfaces to ignore

    Returns:
        dict: Updated device data with interface information
    """
    deviceCount = len(devices)
    for deviceNum, device in enumerate(devices, 1):
        logging.info(f"Fetching interface information for device {device} ({deviceNum} of {deviceCount})")
        query_url = f"{interface_query_base_url}{device}"
        interfaces = fetch_raw_json(query_url, auth)
        devices[device]['interfaces'] = {}
        for interface in interfaces:
            """ 
            If the interface is NOT in the HA / Interface ignore list, 
            Check if it has a valid IPv4 network or host address
            Then Check if that network or host address is private
            """
            if interface['ifname'] in ignore_interface_list:
                logging.info(f"\t {interface['ifname']} is in the ignore list. Skipping.")
                continue
            if is_ipv4(interface['ip-address']):
                if ipaddress.ip_network(interface['ip-address'], strict=False).is_private:
                    logging.info(f"\t {interface['ifname']} has a private IP: {interface['ip-address']} Skipping.")
                    continue
                else:
                    logging.info(f"\t {interface['ifname']} has a public IP: {interface['ip-address']} Adding to the list")
                    devices[device]['interfaces'][interface['ifname']] = interface['ip-address']
    return devices


def export_to_excel(devices: dict, output_file: str, keys: list) -> None:
    """
    Export the provided data to an Excel file.

    Args:
        devices (dict): Dictionary of device data
        output_file (str): Base filename for the output file
        keys (list): List of headers/keys for the Excel file

    Returns:
        None
    """
    workbook = Workbook(f'{output_file}.xlsx')
    header_format = workbook.add_format({'bold': True,
                                         'font_size': 12,
                                         'border': 1})
    base_format = workbook.add_format({'valign': 'vcenter',
                                       'align': 'left'})
    wrap_format = workbook.add_format({'text_wrap': True,
                                       'valign': 'vcenter',
                                       'align': 'left'})
    worksheet = workbook.add_worksheet('vEdgeData')
    worksheet.write_row(0, 0, keys, header_format)
    worksheet.write_row(0, len(keys), ['interface-name', 'interface-IP'], header_format)

    row = 1
    for device, data in devices.items():
        col = 0
        for header in keys:
            value = data.get(header, "N/A")
            worksheet.write(row, col, value, base_format)
            col += 1
        if data.get('interfaces'):
            ifnames = ""
            ifaddresses = ""
            for interface, ip in data['interfaces'].items():
                ifnames += f"{interface}\n"
                ifaddresses += f"{ip}\n"
            worksheet.write(row, col, ifnames.strip(), wrap_format)
            worksheet.write(row, col + 1, ifaddresses.strip(), wrap_format)
        row += 1
    workbook.close()


def export_to_html(devices: dict, output_file: str, keys: list) -> None:
    """
    Export the provided data to an HTML file.

    Args:
        devices (dict): Dictionary of device data
        output_file (str): Base filename for the output file
        keys (list): List of headers/keys for the HTML file

    Returns:
        None
    """
    html_head = """
    <html>
    <head>
        <title>Cisco Public IPs</title>
    </head>
    <body>
    <table border='1'>
        <thead>
    """
    html_tail = """
        </tbody>
    </table>
    </body>
    </html>
    """

    html_header_columns = ''.join([f"<th>{key}</th>" for key in keys]) + "<th>interface-name</th><th>interface-IP</th></tr>\r\t\t</thead>\r\t\t<tbody>"

    with (open(f'{output_file}.html', 'w') as html_file):
        html_file.write(html_head)
        html_file.write(f"\t\t<tr>{html_header_columns}\r")
        for device, data in devices.items():
            if data.get('interfaces'):
                row_data = ''.join([f"<td>{data.get(key, 'N/A')}</td>" for key in keys])
                interface_names = '<br>'.join(data['interfaces'].keys())
                interface_addresses = '<br>'.join(data['interfaces'].values())
                html_file.write(f"\t\t\t<tr>{row_data}<td>{interface_names}</td><td>{interface_addresses}</td></tr>\r")
        html_file.write(html_tail)


def setup_logging(log_file: str) -> None:
    """
    Setup logging to file and console.

    Args:
        log_file (str): Path to the log file

    Returns:
        None
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def main() -> None:
    """
    Main function to orchestrate data retrieval and processing.

    Returns:
        None
    """
    args = parse_arguments()

    # Define which column headers / keys to retrieve from the vManage device data and include in the HTML and XLSX output.
    keys = ['system-ip', 'host-name', 'reachability', 'version', 'site-id']

    # Setup logging with the specified log file and console output
    setup_logging(args.log_file)

    # Check and retrieve stored credentials
    if os.path.exists(args.password_file):
        username, password = store_creds.get_creds(args.password_file)
    else:
        store_creds.store_creds(args.password_file)
        username, password = store_creds.get_creds(args.password_file)

    auth = (username, password)
    device_query_url = f'https://{args.vmanage_address}:8443/dataservice/device'
    interface_query_base_url = f'https://{args.vmanage_address}:8443/dataservice/device/interface?deviceId='
    ignore_interface_list = args.ignore_list

    # Fetch device data
    raw_devices = fetch_raw_json(device_query_url, auth)
    logging.info(f"Fetched {len(raw_devices)} devices from the vManage server")
    if raw_devices:
        devices = format_device_data(raw_devices, keys)
        add_interface_info(devices, auth, interface_query_base_url, ignore_interface_list)
        export_to_excel(devices, args.output_file, keys)
        export_to_html(devices, args.output_file, keys)


if __name__ == "__main__":
    main()