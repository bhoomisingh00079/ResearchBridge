"""Locator, HTML5 validation and BVA practice on the public SelectorsHub page."""

import os

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

URL = "https://selectorshub.com/xpath-practice-page/"


def field(label):
    return By.XPATH, f"//label[contains(normalize-space(),'{label}')]/following::input[1]"


LOC = {
    "email": field("User Email"), "password": field("Password"), "company": field("Company"),
    "mobile": field("Mobile Number"), "card_no": field("Card Number"), "cvv": field("CVV"),
    "submit": (By.XPATH, "//button[normalize-space()='Submit' or @value='Submit'] | //input[@value='Submit']"),
    "pay": (By.XPATH, "//button[contains(normalize-space(),'Pay')]"),
    "alert_btn": (By.XPATH, "//button[contains(.,'Open Window Alert')]"),
}


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


def type_into(browser, key, value):
    element = WebDriverWait(browser, 15).until(EC.presence_of_element_located(LOC[key]))
    browser.execute_script("arguments[0].scrollIntoView({block:'center'})", element)
    element.clear()
    element.send_keys(value)
    return element


def test_dummy_form_accepts_valid_input(driver):
    type_into(driver, "email", "student@ves.ac.in")
    type_into(driver, "password", "Secret123")
    type_into(driver, "company", "VESIT")
    type_into(driver, "mobile", "9876543210")
    assert driver.find_element(*LOC["email"]).get_attribute("value") == "student@ves.ac.in"
    assert driver.find_element(*LOC["mobile"]).get_attribute("value") == "9876543210"


@pytest.mark.parametrize("email,valid", [("student@ves.ac.in", True), ("no-at-sign", False),
                                          ("a@b", True), ("two@@signs.com", False)],
                         ids=["valid", "no-at", "minimal-valid-per-html5", "double-at"])
def test_email_html5_validation_partitions(driver, email, valid):
    element = type_into(driver, "email", email)
    assert driver.execute_script("return arguments[0].checkValidity()", element) is valid


def hint(browser, label, text):
    return browser.find_element(By.XPATH,
        f"//label[contains(normalize-space(),'{label}')]/following::*[contains(normalize-space(),'{text}')][1]")


@pytest.mark.parametrize("digits,valid", [(15, False), (16, True), (17, False)], ids=["15-below", "16-boundary", "17-above"])
def test_card_number_length_bva(driver, digits, valid):
    type_into(driver, "card_no", "4" * digits)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(LOC["pay"])).click()
    assert hint(driver, "Card Number", "valid 16-digit").is_displayed() is (not valid)


@pytest.mark.parametrize("digits,valid", [(2, False), (3, True), (4, True), (5, False)], ids=["2-below", "3-lower", "4-upper", "5-above"])
def test_cvv_length_bva(driver, digits, valid):
    type_into(driver, "cvv", "1" * digits)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(LOC["pay"])).click()
    assert hint(driver, "CVV", "valid 3 or 4").is_displayed() is (not valid)


def test_window_alert_is_handled(driver):
    WebDriverWait(driver, 15).until(EC.element_to_be_clickable(LOC["alert_btn"])).click()
    alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
    assert alert.text
    alert.accept()
