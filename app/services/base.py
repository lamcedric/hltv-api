from dataclasses import dataclass, field
from typing import Optional
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from fastapi import HTTPException
from lxml import etree

from app.utils.utils import trim

# Try curl_cffi first (better Cloudflare bypass), fallback to cloudscraper
try:
    from curl_cffi import requests as curl_requests
    USE_CURL_CFFI = True
except ImportError:
    import cloudscraper
    USE_CURL_CFFI = False


@dataclass
class HLTVBase:
    """
    Base class for making HTTP requests to HLTV and extracting data from the web pages.

    Args:
        URL (str): The URL for the web page to be fetched.
    Attributes:
        response (dict): A dictionary to store the response data.
    """

    URL: str = field(init = False)
    response: dict = field(default_factory= lambda: {}, init= False)
    
    def make_request(self, url: Optional[str] = None, max_retries: int = 3):
        """
        Make an HTTP GET request to the specified URL with retry logic.
        Uses curl_cffi (better Cloudflare bypass) if available, otherwise cloudscraper.

        Args:
            url (str, optional): The URL to make the request to. If not provided, the class's URL
                attribute will be used.
            max_retries (int): Maximum number of retries for 403/429 errors.

        Returns:
            Response: An HTTP Response object containing the server's response to the request.

        Raises:
            HTTPException: If there are too many redirects, or if the server returns a client or
                server error status code.
        """
        import time
        import random

        url = self.URL if not url else url

        # Browser impersonation options for curl_cffi
        impersonate_browsers = ["chrome120", "chrome119", "chrome110", "safari17_0"]

        last_exception = None
        for attempt in range(max_retries):
            try:
                if USE_CURL_CFFI:
                    # Use curl_cffi with browser impersonation (best for Cloudflare)
                    browser = random.choice(impersonate_browsers)
                    response = curl_requests.get(
                        url,
                        impersonate=browser,
                        timeout=30,
                    )
                else:
                    # Fallback to cloudscraper
                    scraper = cloudscraper.create_scraper(
                        browser={
                            'browser': 'chrome',
                            'platform': 'windows',
                            'desktop': True,
                        }
                    )
                    response = scraper.get(
                        url=url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Accept-Language": "en-US,en;q=0.9",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                            "Connection": "keep-alive",
                        },
                    )

                # Check for rate limiting or Cloudflare block
                if response.status_code in (403, 429, 503):
                    wait_time = (2 ** attempt) + random.uniform(2, 5)
                    time.sleep(wait_time)
                    continue

                if 400 <= response.status_code < 500:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Client Error. {response.status_code} for url: {url}"
                    )

                return response

            except HTTPException:
                raise
            except Exception as e:
                error_str = str(e).lower()
                if "redirect" in error_str:
                    raise HTTPException(status_code=404, detail=f"Not found for url: {url}")
                last_exception = HTTPException(status_code=500, detail=f"Error for url: {url}. {e}")
                wait_time = (2 ** attempt) + random.uniform(2, 5)
                time.sleep(wait_time)

        if last_exception:
            raise last_exception
        raise HTTPException(status_code=500, detail=f"Max retries exceeded for url: {url}")
    
    def request_url_bsoup(self) -> BeautifulSoup:
        """
        Fetch the web page content and parse it using BeautifulSoup.

        Returns:
            BeautifulSoup: A BeautifulSoup object representing the parsed web page content.

        Raises:
            HTTPException: If there are too many redirects, or if the server returns a client or
                server error status code.
        """

        response: Response = self.make_request()
        return BeautifulSoup(markup=response.content, features="html.parser")
    
    @staticmethod
    def convert_bsoup_to_page(bsoup: BeautifulSoup) -> ElementTree:
        """
        Convert a BeautifulSoup object to an ElementTree.

        Args:
            bsoup (BeautifulSoup): The BeautifulSoup object representing the parsed web page content.

        Returns:
            ElementTree: An ElementTree representing the parsed web page content for further processing.
        """

        return etree.HTML(str(bsoup))
    
    def request_url_page(self) -> ElementTree:
        """
        Fetch the web page content, parse it using BeautifulSoup, and convert it to an ElementTree.

        Returns:
            ElementTree: An ElementTree representing the parsed web page content for further
                processing.

        Raises:
            HTTPException: If there are too many redirects, or if the server returns a client or
                server error status code.
        """
        bsoup: BeautifulSoup = self.request_url_bsoup()
        return self.convert_bsoup_to_page(bsoup=bsoup)
    
    def get_all_by_xpath(self,xpath: str) -> list[str]:
        """
    Extract all text elements from the web page using the specified XPath expression.

    Args:
        xpath (str): The XPath expression used to locate the desired elements on the web page.

    Returns:
        list[str]: A list of trimmed strings extracted from the elements found via the XPath expression.

    Raises:
        ValueError: If there is an error during XPath evaluation or element extraction.
        """
        try:
            elements = self.page.xpath(xpath)
            return [trim(e) for e in elements if e]
        except Exception as e :
            raise ValueError(f"Error at xpath data extract'{xpath}': {e}") from e
            return []
    
    def get_text_by_xpath(
            self,
            xpath: str,
            pos: int =0,
            iloc: Optional[int] = None,
            iloc_from: Optional[int] = None,
            iloc_to: Optional[int] = None,
            join_str: Optional[str] = None,
            attribute: Optional[str] =None
    ) -> Optional[str]:
        """
    Extract text or attribute from elements using XPath.

    Args:
        xpath (str): XPath expression to select elements.
        pos (int): Default index to select if multiple elements match.
        iloc (int): Specific index of the desired element (alternative to 'pos').
        iloc_from (int): Start index for slicing (inclusive).
        iloc_to (int): End index for slicing (exclusive).
        join_str (str): If provided, joins multiple extracted values using this separator.
        attribute (str): Attribute to extract (e.g., 'alt', 'title'). If None, extracts text content.

    Returns:
        Optional[str]: Extracted text or attribute value, or None if not found.
        """
        

        if not hasattr(self,"page"):
            self.page = self.request_url_page()

        elements = self.page.xpath(xpath) 
        
        if not elements:
            return None

        def extract(e):
            if isinstance(e,etree._Element):
                if attribute:
                    return trim(e.get(attribute,""))
                return trim(e.text) if e.text else None
            return trim(str(e)) if e else None

        elements = [extract(e) for e in elements if extract(e)]

        if isinstance(iloc,int):
            return elements[iloc] if iloc < len(elements) else None
        
        if isinstance(iloc_from, int) and isinstance(iloc_to, int):
            elements= elements[iloc_from:iloc_to]
        elif isinstance(iloc_to, int):
            elements = elements[:iloc_to]
        elif isinstance(iloc_from,int):
            elements= elements[iloc_from:]

        if join_str:
            return join_str.join(elements)
        
        try:
            return elements[pos]
        except IndexError:
            return None

    def raise_exception_if_not_found(self, xpath: str):
        """
    Raise an HTTP 404 exception if no element is found for the given XPath expression.

    Args:
        xpath (str): The XPath expression used to search for content on the page.

    Raises:
        HTTPException: Raised with status code 404 if the XPath does not return any result,
        indicating that the requested resource was not found or is invalid.
        """

        if not self.get_text_by_xpath(xpath):
            raise HTTPException(status_code = 404, detail=f"Invalid request (url: {self.URL})")