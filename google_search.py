import pickle
import sys
import time, random
import urllib, sqlite3
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.chrome.options import Options   
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import *

from webdriver_manager.chrome import ChromeDriverManager
from twocaptcha import TwoCaptcha

from multiprocessing import freeze_support

freeze_support()
import undetected_chromedriver.v2 as uc


# PATH = r"C:\Users\aweab\.wdm\drivers\chromedriver\win32\104.0.5112.79\chromedriver.exe"
HEADERS = {
    'User-agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582'
}
BASE_URL = 'https://google.com/search?q=' 


def get_driver():
    options = Options()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    options.add_argument("--disable-notifications")

    PATH = ChromeDriverManager().install()
    
    # driver = webdriver.Chrome(service=Service(PATH), options=options)
    driver = uc.Chrome(driver_executable_path=PATH)
    driver.maximize_window()

    return driver


def scrape_list(text_list, start, end):
    driver = get_driver()

    for text in text_list:
        text = urllib.parse.quote_plus(text)

        for page in range(start, end+1):

            page = (page * 10) - 10
            url = BASE_URL + text + f"&start={page}&filter=0"

            
            driver.get(url)
            soup = bs(driver.page_source, "lxml")

            divs = soup.select('div[data-sokoban-container]')


            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()

            cursor.execute('CREATE TABLE IF NOT EXISTS google_results (name TEXT, web_details TEXT, description TEXT, link TEXT);')

                
            
            for div in divs:
                web_details = div.find('cite').text.strip()
                name = div.find('h3').text.strip()
                description = div.select_one('div[data-content-feature="1"]').text.strip()

                link = div.find('a')['href']

                cursor.execute('INSERT INTO google_results(name, web_details, description, link) VALUES(?,?,?,?)', 
                    (name, web_details, description, link))

                conn.commit()

    driver.quit()
    conn.close()



def scrape(driver, cursor, text, page, delay):
    text = urllib.parse.quote_plus(text)
    page = (page * 10) - 10
    url = BASE_URL + text + f"&start={page}&filter=0"

    
    driver.get(url)
    try:
        if 'sorry/index' in driver.current_url:
            pass
        else:
            WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, '//iframe[@title = "reCAPTCHA"]')))
        
        # try:
        print("Found captcha")
        #     cookies = pickle.load(open(f"assets/google.pkl", "rb"))
        #     driver.back()
        #     for cookie in cookies:
        #         driver.add_cookie(cookie)
        # except:
        input("Please solve manually then press [enter] here to continue scraping\n")
        # pickle.dump(driver.get_cookies(), open(f'assets/google.pkl', 'wb'))

        driver.get(url)
        if 'sorry/index' in driver.current_url:
            return [[]]
        # driver.find_element(By.XPATH, '//iframe[@title = "reCAPTCHA"]')
    except:
        pass
    
    time.sleep(random.uniform(abs(delay-3 ), delay+5))
    soup = bs(driver.page_source, "lxml")

    divs = soup.select('div[data-sokoban-container]')

    cursor.execute('CREATE TABLE IF NOT EXISTS google_results (name TEXT, web_details TEXT, description TEXT, link TEXT);')

        
    all_results = []
    for div in divs:
        web_details = div.find('cite').text.strip()
        name = div.find('h3').text.strip()
        description = div.select_one('div[data-content-feature="1"]').text.strip()

        link = div.find('a')['href']

        cursor.execute('INSERT INTO google_results(name, web_details, description, link) VALUES(?,?,?,?)', 
            (name, web_details, description, link))

        all_results.append([name, web_details, description, link])

    return all_results

if __name__ == "__main__":
    text = "CIO ABB LIMITED linkein"
    text = "google"
    delay = 5
    driver = get_driver()

    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()

        for page in range(1, 5):
            if scrape(driver, cursor, text, page, delay) is None:
                break

