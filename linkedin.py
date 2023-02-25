import sqlite3, random, time, pickle, re
from bs4 import BeautifulSoup as bs
from pprint import pprint
import lxml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options   
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import *
import undetected_chromedriver.v2 as uc
from webdriver_manager.chrome import ChromeDriverManager



#PATH = r"C:\Users\aweab\.wdm\drivers\chromedriver\win32\104.0.5112.79\chromedriver.exe"
#PATH = ChromeDriverManager().install()

def login(driver, email, password):
    driver.get("https://www.linkedin.com/login")

    try:
        cookies = pickle.load(open(f"assets/{email}.pkl", "rb"))
        for cookie in cookies:
            driver.add_cookie(cookie)
        print('Added')
        driver.refresh()
    except FileNotFoundError:
        time.sleep(random.uniform(5, 10))
        driver.find_element(By.ID, "username").send_keys(email)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, ".btn__primary--large").click()
        time.sleep(random.uniform(5, 10))

        if '/checkpoint/challenge/' in driver.current_url or 'security check' in driver.page_source:
            print('######################### IMPORTANT ############################')
            input("Please complete the security check and press enter in this console when it is done.")
            print('#############################################################################')
            time.sleep(random.uniform(5.5, 10.5))

        pickle.dump(driver.get_cookies(), open(f'assets/{email}.pkl', 'wb'))
    

def linkedin_driver():
    options = Options()
    # options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument("--disable-notifications")

    PATH = ChromeDriverManager().install()
    driver = uc.Chrome(driver_executable_path=PATH, options=options)
    driver.maximize_window()

    return driver

def click(driver, element):
    action = ActionChains(driver)
    action.click(element)
    action.perform()

def wait(driver, locator, id, time=10):
    element = WebDriverWait(driver, time).until(EC.presence_of_element_located((locator, id)))
    return element

def waitVisible(driver, locator, id, time=10):
    elements = WebDriverWait(driver, time).until(EC.visibility_of_all_elements_located((locator, id)))
    return elements

def profile_scrape(driver, cursor, link, delay):
    cursor.execute("""CREATE TABLE IF NOT EXISTS linkedin_profile (
        profile_link TEXT,
        fullname TEXT,
        location TEXT,
        designation TEXT,
        contact_info TEXT,
        about TEXT,
        experience TEXT,
        education TEXT);""")


    driver.get(link)
    time.sleep(delay)
    try:
        waitVisible(driver, By.CLASS_NAME, 'pv-top-card', time=25)
    except:
        return None
    soup = bs(driver.page_source, 'lxml')

    name = soup.find('h1', class_='text-heading-xlarge').text.strip()
    location = soup.select_one('div.pv-text-details__left-panel.pb2 > span').text.strip()
    designation = soup.select_one('div.pv-text-details__left-panel div:nth-child(2)').text.strip()

    try: about = soup.select_one('.pv-shared-text-with-see-more span.visually-hidden').text.strip()
    except: about = ''


    # Contact info
    driver.find_element(By.ID, 'top-card-text-details-contact-info').click()
    time.sleep(delay)

    wait(driver, By.CLASS_NAME, 'pv-contact-info')
    cs = bs(driver.page_source, 'lxml')
    div = cs.select_one('.section-info')

    contact_info = {}
    for section in div.find_all('section'):
        h3 = section.find('h3').text.strip()
        if "Profile" in h3:
            continue
        contact_info[h3] = section.select_one('.pv-contact-info__ci-container').text.strip().replace('\n', '')

    contact_info_str = ''
    for key, value in contact_info.items():
        contact_info_str += f'{key}: {value}\n' + '-'*10 + '\n'

    
    driver.back()


    # Experience
    try:
        ex = soup.find('div', {'id':'experience'}).parent
        experiences = ''

        for experience in ex.select('.artdeco-list__item')[:5]:
            designation = experience.select_one('span.mr1')
            if 'hoverable-link-text' in designation['class']:
                company_name = designation.span.text.strip()

                designation = experience.select_one('.pvs-list li .pvs-list__outer-container span.mr1').span.text.strip()

                # location = experience.select_one('.t-14.t-normal.t-black--light').span.text.strip()

            else:
                designation = designation.span.text.strip()
                company_name = experience.select_one('.t-normal:not(span.t-black--light)').span.text.strip()
                # location = experience.find_all('span', {'class':'t-black--light'})[-1].span.text
            
            company_link = experience.find('a')['href']
            try:
                ex_location = [sp.span.text for sp in experience.select('.t-14.t-normal.t-black--light') if not re.search('\d', sp.span.text)][0]
            except IndexError: ex_location = ''


            experiences += company_name + '\n'
            experiences += company_link + '\n'
            experiences += designation + '\n'
            experiences += ex_location + '\n'

            experiences += '-'*20 + '\n\n'

    except:
        experiences = ""

    # Education
    try:
        ed = soup.find('div', {'id':'education'}).parent
        educations = ''

        for li in ed.select('.artdeco-list__item')[:2]:
            institute = li.select_one('span.mr1').span.text
            try:
                course = li.select_one('span.t-14.t-normal:not(.t-black--light)').span.text
            except: course = "Not specified"
            try:
                year = li.select_one('span.t-black--light').span.text
            except: year = "Not specified"

            educations += f"Institute Name - {institute}\n"
            educations += f"Course Name - {course}\n"
            educations += f"Year - {year}\n{'-'*20}\n"
    except:
        educations = ""

    cursor.execute("INSERT INTO linkedin_profile (profile_link, fullname, location, designation, about, experience, contact_info, education) VALUES (?,?,?,?,?,?,?,?)",
                    (link, name, location, designation, about, experiences, contact_info_str, educations))

    return [link, name, location, designation, about, experiences, contact_info_str, educations]

def company_scrape(driver, cursor, link, delay):
    if not link.rstrip('/').endswith('about'):
        link = link.rstrip('/') + '/about/'
    

    query = """CREATE TABLE IF NOT EXISTS linkedin_company (
        company_name TEXT,
        overview TEXT,
        website TEXT,
        industry TEXT,
        company_size TEXT,
        headquarters TEXT,
        specialities TEXT,
        locations TEXT)"""
    cursor.execute(query)

    driver.get(link)
    time.sleep(delay)

    try:
        waitVisible(driver, By.CLASS_NAME, 'artdeco-card', time=25)
    except:
        return None

    soup = bs(driver.page_source, 'lxml')

    company_name = soup.find('h1').text.strip()
    overview = soup.select_one('section.artdeco-card > p').text.strip()


    details = soup.select_one('section.artdeco-card.p5').find('dl')

    website = details.find('dt', string=re.compile('Website', flags=re.IGNORECASE)).find_next_sibling('dd').a['href']
    industry = details.find('dt', string=re.compile('Industry', flags=re.IGNORECASE)).find_next_sibling('dd').text.strip()

    company_size = ''
    company_size_tag = details.find('dt', string=re.compile('Company size', flags=re.IGNORECASE))
    for _ in range(2):
        company_size_tag = company_size_tag.find_next_sibling('dd')
        company_size += company_size_tag.find(text=True).text.strip() + '\n'

    try: hq = details.find('dt', string=re.compile('Headquarters', flags=re.IGNORECASE)).find_next_sibling('dd').text.strip()
    except AttributeError: hq = None

    specialities = details.find('dt', string=re.compile('Specialties', flags=re.IGNORECASE)).find_next_sibling('dd').text.strip()
    

    locations = ""

    l = 0
    locations_svg = driver.find_elements(By.XPATH, "//*[name()='svg'][@aria-label = 'Interactive chart']//*[name() = 'path'][contains(@aria-label, 'CompanyLocations')]")
    while l < 5:
        try:
            location = locations_svg[l]
        except IndexError:
            break
            
        click(driver, location)
        locations += wait(driver, By.CSS_SELECTOR, '.org-location-card p').text + '\n' + '-'*20 + '\n'
        time.sleep(1)
        click(driver, driver.find_element(By.XPATH, "//button[contains(@aria-label, 'locations')]"))
        locations_svg = waitVisible(driver, By.XPATH, "//*[name()='svg'][@aria-label = 'Interactive chart']//*[name() = 'path'][contains(@aria-label, 'CompanyLocations')]")

        l += 1
    time.sleep(delay)

    query = "INSERT INTO linkedin_company VALUES(?,?,?,?,?,?,?,?)"
    cursor.execute(query, (company_name, overview, website, industry, company_size, hq, specialities, locations))

    return [company_name, overview, website, industry, company_size, hq, specialities, locations]


if __name__ == "__main__":
    link = 'https://in.linkedin.com/in/sparashar'

    driver = linkedin_driver()
    login(driver, 'abdark24@gmail.com', 'Characters1')
    profile_scrape(driver, None, link)

    company_scrape(2, 3, 'https://www.linkedin.com/company/ctrls-datacenters-ltd/about/')

