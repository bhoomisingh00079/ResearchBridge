"""Selenium EP example against the public OrangeHRM demo login page."""

import os

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

URL = "https://opensource-demo.orangehrmlive.com/web/index.php/auth/login"
USER, PASSWORD = (By.NAME, "username"), (By.NAME, "password")
SUBMIT = (By.CSS_SELECTOR, "button[type='submit']")
ALERT = (By.CSS_SELECTOR, ".oxd-alert-content-text")
FIELD_ERROR = (By.CSS_SELECTOR, ".oxd-input-field-error-message")
DASH_HEADER = (By.CSS_SELECTOR, "h6.oxd-topbar-header-breadcrumb-module")


@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    if os.getenv("HEADLESS"):
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1366,900")
    browser = webdriver.Chrome(options=options)
    browser.get(URL)
    yield browser
    browser.quit()


def login(browser, username, password):
    wait = WebDriverWait(browser, 15)
    wait.until(EC.visibility_of_element_located(USER)).send_keys(username)
    browser.find_element(*PASSWORD).send_keys(password)
    browser.find_element(*SUBMIT).click()
    return wait


CASES = [
    ("TC01", "Admin", "admin123", "dashboard"),
    ("TC02", "Admin", "wrong", "invalid"),
    ("TC03", "nobody", "admin123", "invalid"),
    ("TC04", "nobody", "wrong", "invalid"),
    ("TC05", "", "", "required2"),
    ("TC06", "", "admin123", "required1"),
    ("TC07", "Admin", "", "required1"),
    ("TC08", "ADMIN", "admin123", "dashboard"),  # Demo behavior must be confirmed.
    ("TC09", "Admin", "ADMIN123", "invalid"),
]


@pytest.mark.parametrize("case_id,username,password,expected", CASES, ids=[case[0] for case in CASES])
def test_login_partitions(driver, case_id, username, password, expected):
    wait = login(driver, username, password)
    if expected == "dashboard":
        wait.until(EC.url_contains("/dashboard"))
        assert "Dashboard" in wait.until(EC.visibility_of_element_located(DASH_HEADER)).text
    elif expected == "invalid":
        assert "Invalid credentials" in wait.until(EC.visibility_of_element_located(ALERT)).text
    else:
        count = 2 if expected == "required2" else 1
        wait.until(lambda browser: len(browser.find_elements(*FIELD_ERROR)) == count)
        assert all(error.text == "Required" for error in driver.find_elements(*FIELD_ERROR))
        assert "/auth/login" in driver.current_url
