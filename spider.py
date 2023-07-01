import os
import time
import requests
import validators
from bs4 import BeautifulSoup
from selenium import webdriver
from urllib.parse import quote
from urllib.parse import urljoin, urlparse
from selenium.webdriver.common.by import By
from urllib.request import Request, urlopen
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver
import selenium.webdriver.support.expected_conditions as Ex
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException


class Spider():
    def __init__(self, root_string=""):
        """ Initiation method for every 'Crawler' object.

        Args:
            root_string (str, optional): Initial link for a page to be crawled. Defaults to "".
        """
        self.root = root_string
        self.response = None
        self.selenium_driver = self.__init_selenium_process__()

    def __init_selenium_process__(self):
        # Start a Selenium driver; hide all information displayed
        op = Options()
        op.add_argument("--start-maximized")
        op.add_argument("--log-level=3")                                    # Disable any logging to the console
        op.add_argument("--headless=new")                                   # Run everything in the background
        op.add_experimental_option('excludeSwitches',['enable-logging'])    # Disables any residual logging to the console
        driver = webdriver.Chrome(options=op)
        driver.set_page_load_timeout(60) # set page load timeout to 30 seconds.
        return driver

    def _start_request(self, root: str, content_type='html/text'):
        """ Method that takes in a content_type (optional) and sets up the headers for a request query.

        Args:
            content_type (str, optional): Sets up the headers to send a request, the user-agent is set to Chrome to bypass any unauthorized access error. Defaults to 'html/text' when given a webpage.
        """
        self.response = Request(
            url = root,
            headers = {
              'User-Agent': 'Chrome/5.0',
              'Content-Type' : content_type
            }
        )

    def __optimize_selenium_driver__(self, webpage_url: str):
        """ Function that 'reuses' a Selenium Webdriver if it has already set to crawl a webpage.
        If the spider has already crawled a webpage, it will not issue a GET request to said page again,
        for it already has the webpage's information, leaving the driver in its latest state.
        Otherwise, it will issue a GET request to the page, getting the webpage's information

        Args:
            webpage_url (str): Webpage URL to Crawl

        Raises: 
            Exception if an unhandled error occurs.

        """

        # if our current crawler has already crawled this page, and is set to that, reuse it, otherwise crawl.

        if self.selenium_driver.current_url != webpage_url:
            try:
                self.selenium_driver.get(webpage_url)
            except Exception as ex:
                return ex

    def get_all_sublinks_selenium_by_soup(self, webpage: str = "") -> 'set[str]':
        """ Method that utilizes the Selenium Driver to retrieve the links on a webpage. This method can be used as a backup or the main way to get links.
            This method is set for pages that are mostly, if not completely, in JS as they have very little HTML.

        Args:
            webpage_url (str, Optional): Webpage URL to Crawl

        Returns:
            temp_set (set): Set of links in a webpage.
        """
        temp_set = set()

        if webpage != "":
            self.__optimize_selenium_driver__(webpage)

        waiting_time = 3
        _ = self.selenium_driver.timeouts.implicit_wait(waiting_time)
        soup = BeautifulSoup(self.selenium_driver.page_source, 'html.parser')          # Utilize beautiful soup for speed.
        links = self.get_all_sublinks_from_soup(soup)

        # record_start_time = perf_counter()
        for l in links:
            if l.startswith("https:") or l.startswith("http:"):          # Skip a link if it's more of an appended (#resources) link.
                temp_set.add(l)
        # record_end_time = perf_counter()
        # perf_elapsed_time = record_end_time - record_start_time
        # print(f"Looping through SOUP A TAGS executed in {perf_elapsed_time} seconds")
        return temp_set

    def get_all_sublinks_selenium_by_xpath(self, webpage: str = "") -> 'set[str]':
        """ Same as the method above, just using the XPATH
        
        Args:
            webpage_url (str, Optional): Webpage URL to Crawl

        Returns:
            temp_set (set): Set of links in a webpage.
        """
        temp_set = set()

        if webpage != "":
            self.__optimize_selenium_driver__(webpage)

        href_elements = self.selenium_driver.find_elements(By.XPATH, "//a[@href]")

        # record_start_time = perf_counter()
        for e in href_elements:
            thing = e.get_attribute("href")
            if thing.startswith("https:") or thing.startswith("http:"): 
                temp_set.add(thing)
        # record_end_time = perf_counter()
        # print(f"Looping XPATH executed in {record_end_time - record_start_time} seconds")
        return temp_set

    # Code taken from https://www.thepythoncode.com/article/extract-all-website-links-python 
    # Modified by William E Basquez on 5/17/2023
    def get_all_sublinks_from_soup(self, soup: BeautifulSoup) -> 'set[str]':
      """ Method that validates if a string is a valid URL, it does so with each string (sublink) received from the webpage's soup

      Args:
          soup (BeautifulSoup): Webpage's tree structure of HTML code

      Returns:
          temp_set: Set of sublinks from a webpage.
      """
      temp_set = set()
      for a_tag in soup.find_all('a'):    # Find all the <a> tag elements
          href = a_tag.get('href')        # Get all the href elements inside <a> tags
          if href == "" or href is None:  # href empty tag
              continue

          clean_href = self.modify_verify_url(self.root, href)
            
          if clean_href != "" and "mailto" not in clean_href:
              temp_set.add(clean_href)
        
      return temp_set

    def get_all_images_from_soup(self, soup: BeautifulSoup) -> set:
      """ Method that takes in a HTML tree representation of a webpage and looks for all the <img> elements

      Args:
          soup (BeautifulSoup): Webpage's tree structure of HTML code

      Returns:
          temp_set: Set containing the text (alt) and URL of where an image is stored (src)
      """
      temp_set = set()
      temp_links = []
      for a_tag in soup.find_all('img'):
          if a_tag.get('src') not in temp_links:
              temp_links.append(a_tag.get('src'))
              temp_set.add((a_tag.get('alt'), a_tag.get('src')))
      return temp_set

    def modify_verify_url(self, root: str, url: str) -> str:
      """ Method that takes in a root URL and a potentially broken sublink within that root URL, and creates a new URL with the root's domain joined with the sublink.
      The method also checks if this new URL is a valid URL, if it is, then returns it; otherwise it returns an empty string (meaning the link is either broken or a misdirected link)

      Args:
          root (str): 'Main' page of a product
          url (str): Sublink found the 'main' page that may or may not be a valid URL

      Returns:
          str: String containing a valid URL, or an empty string
      """

      # Clean the incoming link
      if validators.url(url):
          return url
        
      clean_href = "".join(quote(i) for i in url)

      if not validators.url(clean_href):  # if not a valid URL; make it valid
          # join the URL if it's relative (not absolute link)
          href = urljoin(root, clean_href)        
          parsed_href = urlparse(href)
        
          # remove URL GET parameters, URL fragments, etc.
          valid_href = parsed_href.scheme + "://" + parsed_href.netloc + parsed_href.path
        
          if validators.url(valid_href): # valid URL
              return valid_href
      else:
          return url
        
      return ""

    def get_elements_xpaths(self, webpage: str, xpath: str) -> 'list[str]':
        """_summary_

        Args:
            webpage (str): URL of a 'main' product page
            xpath (str): Full XPATH of an element within a webpage

        Returns:
            list_of_paths: List of all the XPATHs of a repeating element type within a webpage
        """
      
        list_of_elements = []

        path_of_elements = xpath.split('[INDEX]')

        self.__optimize_selenium_driver__(webpage)
        
        # We start with index at 1, because starting at 0 means tag is non-existent
        index = 1

        current_path = ""
        while True:
            # The assumption is that there will be at least 1 element, therefore we start with 1 inside square-brackets (div[1] == div; but div[2] != div)
            current_path = path_of_elements[0] + '[' + str(index) + ']' + path_of_elements[1]

            try:
                element = self.selenium_driver.find_element(By.XPATH, current_path)
            except NoSuchElementException:
                pass

            if element != None:  # If there is a WebElement with xpath = current_path, append its xpath
                list_of_elements.append(element)
                index += 1
            else:           # If there is not a WebElement with xpath = current_path, stop search or do something else
                break       # Maybe do somehting else...
    
        return list_of_elements

    def get_attributes_from_selenium_using_xpath(self, xpath: str, attributes: 'list[str]') -> 'list[tuple[str,str]]':
        """Method that returns the attributes of a WebElement using Selenium.
           We find the elements and return the desired attributes in a [key, value] pairing

        Args:
            xpath (str): Full xpath of an element in a webpage
            attributes (list[str]): List of possible WebElement attributes

        Returns:
            list[tuple[str,str]]: List containing tuples with [attribute, path] pairing
        """
        attribute_tuples = []
        element = self.selenium_driver.find_element(By.XPATH, xpath)
        for attr in attributes:
            path = element.get_attribute(attr)
            if path != "":
                attribute_tuples.append([attr, path])
        return attribute_tuples

    def _scroll_down_pages(self, webpage: str):
        """ Function that takes in a webpage and it scrolls down until there is no more data to load.
        It updates the Selenium WebDriver

        Args:
            webpage_url (str): URL of webpage to crawl.

        """

		self.__optimize_selenium_driver__(webpage)
        time.sleep(2)
        start_y = 0

        scroll_height = self.selenium_driver.execute_script("return document.body.scrollHeight") / 2
        r = len(self.selenium_driver.execute_script("return window.performance.getEntries();"))

        counter = 1
        multiplier = 0
        while True:
            counter /= 2
            multiplier += counter

            scroll_height = self.selenium_driver.execute_script("return document.body.scrollHeight")

            scroll_dist = scroll_height * multiplier

            _ = self.selenium_driver.execute_script("window.scrollTo({}, {})".format(start_y, scroll_dist))

            time.sleep(1)

            q = len(self.selenium_driver.execute_script("return window.performance.getEntries();"))

            if q == r:
                break

            r = q

            start_y = scroll_dist
