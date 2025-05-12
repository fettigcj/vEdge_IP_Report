import zlib
from base64 import urlsafe_b64encode as b64e, urlsafe_b64decode as b64d
from getpass import getpass
import logging

def encode_pass(data: bytes) -> bytes:
    """Encode and compress the provided data."""
    return b64e(zlib.compress(data, 9))

def decode_pass(obscured: bytes) -> bytes:
    """Decompress and decode the provided data."""
    return zlib.decompress(b64d(obscured))

def store_creds(file_name: str) -> None:
    """Store encoded username and password in a file."""
    try:
        username = input("Enter your username: ")
        password = getpass("Enter your password: ")
        with open(file_name, "w") as writer:
            writer.write(f"{encode_pass(username.encode('ascii')).decode('ascii')}\n")
            writer.write(f"{encode_pass(password.encode('ascii')).decode('ascii')}\n")
    except IOError as e:
        logging.error(f"Error writing to file: {e}")

def get_creds(file_name: str) -> tuple[str, str]:
    """Retrieve and decode username and password from a file."""
    try:
        with open(file_name, "r") as reader:
            lines = reader.readlines()
            username = decode_pass(lines[0].strip().encode('ascii')).decode()
            password = decode_pass(lines[1].strip().encode('ascii')).decode()
            return username, password
    except IOError as e:
        logging.error(f"Error reading from file: {e}")
        return "", ""