import json
import time

import requests
import datetime
import pygsheets

def daily_handler(event, context):
    print("Received request: " + json.dumps(event, indent=2))
    return None

def main():
    return daily_handler(None,None)


if __name__ == "__main__":
    main()
