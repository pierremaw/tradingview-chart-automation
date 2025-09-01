import time
from datetime import datetime
import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()  # Load variables from .env file

from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from flask import Flask, request, jsonify

# Airtable
airtable_api_key = os.environ.get('AIRTABLE_API_KEY')
airtable_api_url = os.environ.get('AIRTABLE_API_URL')
airtable_base_id = os.environ.get('AIRTABLE_BASE_ID')
airtable_table_name = os.environ.get('AIRTABLE_TABLE_NAME')

# VPS
remote_address = os.environ.get('REMOTE_ADDRESS')

# TradingView
trading_view_email = os.environ.get('TRADING_VIEW_EMAIL')
trading_view_password = os.environ.get('TRADING_VIEW_PASSWORD')

# Webhook
webhook_passphrase = os.environ.get('WEBHOOK_PASSPHRASE')
chart_webhook_passphrase = os.environ.get('CHART_WEBHOOK_PASSPHRASE')

app = Flask(__name__)

def selenium_chart(asset_name: str):
    '''
    This function:
    1. Uses selenium to navigate to TradingView.
    2. Accesses the chart for the asset specified via the parameter.
    3. Takes a chart image snapshot.
    4. Returns the chart image url and image source url.

    Parameters
    ----------
    asset_name : str
        The asset name to search for on TradingView.

    Returns
    -------
    A string that contains the tradingview chart image url.
    A string that contains the tradingview chart image source url.
    '''

    # Setup chrome options
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--start-maximized')
    
    # Setup user agent
    ua = UserAgent()
    userAgent = ua.random
    chrome_options.add_argument(f'user-agent={userAgent}')
    
    # Setup webdriver
    driver = webdriver.Remote(command_executor=f'{remote_address}:4444',options=chrome_options)
    
    # Access tradingview and sign in
    driver.get('https://www.tradingview.com/#signin')
    time.sleep(1)
    wait=WebDriverWait(driver, timeout=10)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Email']"))).click()
    time.sleep(1)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[name='username']"))).send_keys(trading_view_email)
    time.sleep(1)
    driver.find_element(By.XPATH, "//input[@name='password']").send_keys(f"{trading_view_password}" + Keys.RETURN)
    # Wait for TradingView
    time.sleep(5)

    # Access tradingview chart page
    trading_view_chart_page = False
    while not trading_view_chart_page :
        driver.get("https://www.tradingview.com/chart/")
        time.sleep(5)
        symbol_search = driver.find_element(By.XPATH, "//*[@id='header-toolbar-symbol-search']")
        if symbol_search != []:
            trading_view_chart_page = True
            break
    
    # Search for specific symbol
    symbol_search_visible = False 
    symbol_searched_for = False
    while not symbol_search_visible and not symbol_searched_for:
        symbol_search = driver.find_element(By.XPATH, "//*[@id='header-toolbar-symbol-search']")
        driver.execute_script("arguments[0].click();", symbol_search)
        time.sleep(3)
        search_bar = driver.find_element(By.XPATH, "//input[@placeholder='Search']")
        if search_bar != []:
            symbol_search_visible = True
            wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Search']")))
            search_bar.clear()
            time.sleep(1)
            wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Search']"))).send_keys(asset_name)
            time.sleep(1)
            wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Search']"))).send_keys(Keys.ENTER)
            time.sleep(5)
            take_a_snapshot = driver.find_elements(By.XPATH, "//button[@type='button'][@data-tooltip='Take a snapshot'][@aria-label='Take a snapshot']")

            if take_a_snapshot != []:
                symbol_searched_for = True

    # Take a snapshot
    new_tab_opened = False
    while not new_tab_opened:

        take_a_snapshot = driver.find_element(By.XPATH, "//button[@type='button'][@data-tooltip='Take a snapshot'][@aria-label='Take a snapshot']")
        driver.execute_script("arguments[0].click();", take_a_snapshot)
        time.sleep(1)

        open_image_in_new_tab = driver.find_element(By.XPATH, "//div[@data-name='open-image-in-new-tab']")
        driver.execute_script("arguments[0].click();", open_image_in_new_tab)
        new_tab_opened = True

    # Get image url
    time.sleep(5)
    driver.switch_to.window(driver.window_handles[-1])
    trading_view_chart_image_url = driver.current_url
    image_source_url = wait.until(EC.element_to_be_clickable((By.XPATH, "//img[@alt='TradingView Chart']"))).get_attribute("src")
    
    driver.close()
    driver.quit()

    return trading_view_chart_image_url, image_source_url

def airtable_api_request(airtable_api_url, data):
    '''
    Make a request to the Airtable API.

    Parameters
    ----------
    airtable_api_url : str
        The Airtable API url.
    data : dict

    Returns
    -------
    A boolean that indicates if the request was successful.
    '''
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {airtable_api_key}'
        }
    
    requests.patch(airtable_api_url, headers=headers, json=data)
    return True

@app.route('/')
def hello():
    '''
    Flask route for homepage

    Parameters
    ----------
    None

    Returns
    -------
    A string that contains the text 'W!'.
    '''
    
    return 'W!'

@app.route('/webhook_airtable', methods=['POST'])
def webhook_airtable():
    '''
    Flask route for Airtable webhook. The route accepts a POST request and returns a JSON object.

    Parameters
    ----------
    None

    Returns
    -------
    A dictionary that contains the code and message.

    '''

    # Get the data from the request
    webhook_data = json.loads(request.data)
    
    # Check if the passphrase is correct
    if webhook_data['passphrase'] != chart_webhook_passphrase:
        return {
            "code": "error",
            "message": "Invalid passphrase"
        }
    
    # Parse the data from the request
    record_id = webhook_data['record_id']
    asset_name = webhook_data['asset']
    chart_request_type = webhook_data['request_type']
    timeframe = webhook_data['timeframe']
    pattern = webhook_data['pattern']

    # Create a timestamp using today's date
    time_stamp = datetime.today().strftime('%Y-%m-%d')
    
    # Call to the main function that gets the TradingView chart data
    tradingview_chart_data = selenium_chart(asset_name)

    # Setup the data for the Airtable API request
    data = {"records": 
    [
        {"id": record_id,
            "fields": {
            f"{chart_request_type} Reference": tradingview_chart_data[0],
            f"{chart_request_type}": [{
                "url": tradingview_chart_data[1],
                "filename": f"[{time_stamp}] {asset_name}.png"
                }]
            }
        },
    ]
    }

    # Airtable API request & response
    api_response = airtable_api_request(airtable_api_url, data)

    # Return the response
    if api_response:
        return {
            "code": "success",
            "message": "Airtable record updated successfully"
        }
    else:
        return {
            "code": "error",
            "message": "Airtable record update failed",
            "airtable response": f'{api_response}'
        }

@app.route('/cache-me')
def cache():
    '''
    Flask route for testing nginx caching.
    
    Parameters
    ----------

    Returns
    -------
    A string that contains the text 'nginx will cache this response'.

    '''
    return "nginx will cache this response"

@app.route('/info')
def info():
    '''
    Flask route for info.

    Parameters
    ----------
    None

    Returns
    -------
    A dictionary that contains the connecting IP, proxy IP, host and user-agent.

    '''
    resp = {
		'connecting_ip': request.headers['X-Real-IP'],
		'proxy_ip': request.headers['X-Forwarded-For'],
		'host': request.headers['Host'],
		'user-agent': request.headers['User-Agent']
	}
    
    return jsonify(resp)

@app.route('/flask-health-check')
def flask_health_check():
    '''
    Flask route for health check.
    
    Parameters
    ----------
    None

    Returns
    -------
    A string that contains the text 'success'.

    '''
    return "success"
