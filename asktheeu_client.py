#!/usr/bin/env python3
"""
AskTheEU.org Client

A focused Python client for interacting with AskTheEU.org to create and manage
freedom of information requests to EU institutions.
"""

import os
import requests
import urllib.parse
from lxml import etree
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file if it exists
env_path = Path('.env')
if env_path.exists():
    load_dotenv(env_path)


class AskTheEUClient:
    """Client for interacting with AskTheEU.org for FOI requests using the Alaveteli Pro interface."""

    def __init__(
        self, 
        email: Optional[str] = None, 
        password: Optional[str] = None,
        domain: str = "https://www.asktheeu.org"
    ) -> None:
        """
        Initialize AskTheEU client.
        
        Args:
            email: AskTheEU.org account email. If None, tries to get from environment.
            password: AskTheEU.org account password. If None, tries to get from environment.
            domain: AskTheEU.org domain. Defaults to "https://www.asktheeu.org".
        """
        self.domain = domain
        self.email = email or os.environ.get("ASKTHEEU_EMAIL")
        self.password = password or os.environ.get("ASKTHEEU_PASSWORD")
        
        if not self.email or not self.password:
            raise ValueError("Email and password must be provided or set in environment variables")
        
        self.session = requests.Session()
        self._authenticated = False
    
    def login(self, debug=False) -> bool:
        """
        Log in to AskTheEU.org using the format from the example.txt curl representation.
        
        Args:
            debug: If True, print debug information
            
        Returns:
            bool: True if login was successful, False otherwise
        """
        if self._authenticated:
            if debug:
                print("Already authenticated")
            return True
        
        if debug:
            print(f"Accessing login page: {self.domain}/profile/sign_in")
            
        # Get the login page to extract token
        r = self.session.get(f"{self.domain}/profile/sign_in")
        
        if debug:
            print(f"Login page status code: {r.status_code}")
            
        login_page = etree.HTML(r.text)
        
        # Extract the signin token from the page (based on example.txt)
        token = login_page.xpath('//input[@id="signin_token"]/@value')
        
        if not token:
            if debug:
                print("No signin_token found in login page")
            
            # Try alternative token locations
            token = login_page.xpath('//input[@name="authenticity_token"]/@value')
            if not token:
                if debug:
                    print("No token found")
                return False
        
        if debug:
            print(f"Found token: {token[0][:10]}...")
        
        # Set headers to match the curl example
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': self.domain,
            'pragma': 'no-cache',
            'referer': f"{self.domain}/profile/sign_in?r=%2F",
            'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
        }
        
        # Prepare login data - exactly matching the curl example format
        login_data = {
            'authenticity_token': '',
            'user_signin[email]': self.email,
            'user_signin[password]': self.password,
            'token': token[0],
            'modal': '',
            'commit': 'Sign in'
        }
        
        if debug:
            print("Submitting login form with data:")
            for k, v in login_data.items():
                if 'password' in k:
                    print(f" - {k}: ******")
                else:
                    print(f" - {k}: {v[:20] + '...' if isinstance(v, str) and len(v) > 20 else v}")
                
        # Submit login form with headers
        r = self.session.post(
            url=f"{self.domain}/profile/sign_in",
            headers=headers,
            data=login_data
        )
        
        if debug:
            print(f"Login response status code: {r.status_code}")
        
        # Check if login was successful
        success_indicators = [
            "Sign out" in r.text,
            "sign_out" in r.text,
            "Your profile" in r.text,
            "alaveteli_pro/dashboard" in r.text,
            "logout" in r.text.lower(),
            r.url != f"{self.domain}/profile/sign_in"
        ]
        
        self._authenticated = any(success_indicators)
        
        if debug:
            if self._authenticated:
                print("Login successful")
            else:
                print("Login failed")
                # Save response for debugging
                with open("login_response.html", "w") as f:
                    f.write(r.text)
                print("Saved login response to login_response.html")
        
        return self._authenticated
    
    def create_draft_request(
        self,
        public_body_id: str,
        title: str,
        body: str,
        embargo_duration: str = "",
        debug: bool = False
    ) -> Dict[str, Any]:
        """
        Create a draft FOI request on AskTheEU.org.
        Tries Alaveteli Pro interface first, then falls back to standard interface.
        
        Args:
            public_body_id: ID of the public body on AskTheEU.org
            title: Title of the FOI request
            body: Body text of the FOI request
            embargo_duration: Optional embargo duration (e.g., "3_months")
            debug: If True, print debug information
            
        Returns:
            Dict with response info including success status and draft URL if successful
        """
        if not self._authenticated and not self.login(debug=debug):
            return {"success": False, "error": "Not authenticated"}
            
        # Try Alaveteli Pro interface first
        if debug:
            print("\nTrying Alaveteli Pro interface first...")
            
        pro_result = self._try_pro_interface(public_body_id, title, body, embargo_duration, debug)
        if pro_result.get("success"):
            if debug:
                print("Pro interface request succeeded")
            return pro_result
            
        # If Pro interface failed due to access or token issues, try standard interface
        if debug:
            print(f"\nPro interface failed: {pro_result.get('error')}")
            print("Trying standard interface as fallback...")
            
        if "token" in pro_result.get("error", "") or "page" in pro_result.get("error", ""):
            standard_result = self._try_standard_interface(public_body_id, title, body, debug)
            if standard_result.get("success"):
                if debug:
                    print("Standard interface request succeeded")
                return standard_result
            elif debug:
                print(f"Standard interface also failed: {standard_result.get('error')}")
        
        # If it failed for other reasons, return the Pro interface error
        return pro_result
        
    def _try_pro_interface(
        self, 
        public_body_id: str,
        title: str,
        body: str,
        embargo_duration: str = "",
        debug: bool = False
    ) -> Dict[str, Any]:
        """Try creating a request using the Alaveteli Pro interface."""
        try:
            # Get the new request page to extract CSRF token
            if debug:
                print("Fetching Pro interface request page...")
                
            r = self.session.get(f"{self.domain}/en/alaveteli_pro/info_requests/new")
            if r.status_code != 200:
                if debug:
                    print(f"Failed to access Pro page, status code: {r.status_code}")
                return {"success": False, "error": f"Failed to access Pro interface page: {r.status_code}"}
                
            if debug:
                # Save the response for debugging
                with open("pro_interface_page.html", "w") as f:
                    f.write(r.text)
                print("Saved Pro interface page to pro_interface_page.html")
                
            request_page = etree.HTML(r.text)
            
            # Check page title to see if we have Pro access
            page_title = request_page.xpath('//title/text()')
            if page_title and "not found" in page_title[0].lower():
                if debug:
                    print(f"Page title indicates no access: {page_title[0]}")
                return {"success": False, "error": "No access to Pro interface"}
            
            # Try to extract token
            token = request_page.xpath('//input[@name="authenticity_token"]/@value')
            
            # Try alternative token locations if not found
            if not token:
                if debug:
                    print("Primary token not found, trying alternatives...")
                    
                token = (request_page.xpath('//meta[@name="csrf-token"]/@content') or
                        request_page.xpath('//input[contains(@name, "token")]/@value'))
                        
                if token and debug:
                    print(f"Found alternative token: {token[0][:10]}...")
                    
            if not token:
                if debug:
                    print("No authenticity token found in Pro interface")
                return {"success": False, "error": "Could not find authenticity token in Pro interface"}
            
            # Set headers similar to login headers
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': self.domain,
                'referer': f"{self.domain}/en/alaveteli_pro/info_requests/new",
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
            }
            
            # Create draft request
            if debug:
                print("Submitting Pro interface draft request...")
                
            r = self.session.post(
                url=f"{self.domain}/en/alaveteli_pro/draft_info_requests",
                headers=headers,
                data={
                    "utf8": "✓",
                    "authenticity_token": token[0],
                    "info_request[public_body_id]": public_body_id,
                    "info_request[title]": title,
                    "outgoing_message[body]": body,
                    "embargo[embargo_duration]": embargo_duration,
                    "preview": "true"
                }
            )
            
            if debug:
                print(f"Response status code: {r.status_code}")
                
                # Save the response for debugging
                with open("pro_draft_response.html", "w") as f:
                    f.write(r.text)
                print("Saved response to pro_draft_response.html")
            
            # Check for success and extract the draft ID
            if r.status_code == 200:
                try:
                    # Try to extract the draft ID from the response URL or content
                    draft_page = etree.HTML(r.text)
                    draft_links = draft_page.xpath('//a[contains(@href, "/en/alaveteli_pro/info_requests/")]/@href')
                    
                    if draft_links:
                        for link in draft_links:
                            # Extract the ID from the URL path
                            parts = link.split('/')
                            if len(parts) > 0:
                                draft_id = parts[-1]
                                if draft_id.isdigit():
                                    return {
                                        "success": True,
                                        "method": "pro_interface",
                                        "draft_id": draft_id,
                                        "draft_url": f"{self.domain}/en/alaveteli_pro/info_requests/{draft_id}"
                                    }
                except Exception as e:
                    if debug:
                        print(f"Error parsing Pro response: {str(e)}")
                    return {"success": False, "error": f"Error parsing Pro response: {str(e)}"}
            
            return {
                "success": False,
                "error": f"Failed to create Pro draft request. Status code: {r.status_code}"
            }
        except Exception as e:
            if debug:
                print(f"Exception in Pro interface: {str(e)}")
            return {"success": False, "error": f"Pro interface error: {str(e)}"}
            
    def _try_standard_interface(
        self, 
        public_body_id: str,
        title: str,
        body: str,
        debug: bool = False
    ) -> Dict[str, Any]:
        """Try creating a request using the standard (non-Pro) interface."""
        try:
            # Get the new request page with the public body
            if debug:
                print("Fetching standard interface request page...")
                
            r = self.session.get(f"{self.domain}/new?body={public_body_id}")
            
            if r.status_code != 200:
                # Try alternative URL
                r = self.session.get(f"{self.domain}/new")
                
                if r.status_code != 200:
                    if debug:
                        print(f"Failed to access standard page, status code: {r.status_code}")
                    return {"success": False, "error": f"Failed to access standard interface page: {r.status_code}"}
            
            if debug:
                # Save the response for debugging
                with open("standard_interface_page.html", "w") as f:
                    f.write(r.text)
                print("Saved standard interface page to standard_interface_page.html")
                
            request_page = etree.HTML(r.text)
            
            # Try to extract token
            token = request_page.xpath('//input[@name="authenticity_token"]/@value')
            
            # Try alternative token locations if not found
            if not token:
                if debug:
                    print("Primary token not found, trying alternatives...")
                    
                token = (request_page.xpath('//meta[@name="csrf-token"]/@content') or
                        request_page.xpath('//input[contains(@name, "token")]/@value'))
                        
                if token and debug:
                    print(f"Found alternative token: {token[0][:10]}...")
                    
            if not token:
                if debug:
                    print("No authenticity token found in standard interface")
                return {"success": False, "error": "Could not find authenticity token in standard interface"}
            
            # Set headers similar to login headers
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': self.domain,
                'referer': f"{self.domain}/new",
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
            }
            
            # Create draft request using the standard interface format
            if debug:
                print("Submitting standard interface draft request...")
                
            r = self.session.post(
                url=f"{self.domain}/new",
                headers=headers,
                data={
                    "authenticity_token": token[0],
                    "info_request[title]": title,
                    "outgoing_message[body]": body,
                    "info_request[public_body_id]": public_body_id,
                    "submitted_new_request": "1",
                    "preview": "1",
                    "commit": "Preview"
                }
            )
            
            if debug:
                print(f"Response status code: {r.status_code}")
                
                # Save the response for debugging
                with open("standard_draft_response.html", "w") as f:
                    f.write(r.text)
                print("Saved response to standard_draft_response.html")
            
            # Check for success - standard interface usually redirects to preview page
            if r.status_code in [200, 302]:
                # Extract ID from the response URL
                draft_id = None
                preview_url = r.url
                
                if "/preview/" in preview_url:
                    draft_id = preview_url.split("/preview/")[-1].split("?")[0]
                
                if draft_id:
                    return {
                        "success": True,
                        "method": "standard_interface",
                        "draft_id": draft_id,
                        "draft_url": f"{self.domain}/preview/{draft_id}"
                    }
                else:
                    # Try to extract from HTML if URL doesn't contain it
                    try:
                        preview_page = etree.HTML(r.text)
                        form_action = preview_page.xpath('//form[@id="preview_form"]/@action')
                        
                        if form_action and "/preview/" in form_action[0]:
                            draft_id = form_action[0].split("/preview/")[-1]
                            
                            return {
                                "success": True,
                                "method": "standard_interface",
                                "draft_id": draft_id,
                                "draft_url": f"{self.domain}/preview/{draft_id}"
                            }
                    except Exception as e:
                        if debug:
                            print(f"Error extracting draft ID: {str(e)}")
            
            return {
                "success": False,
                "error": f"Failed to create standard draft request. Status code: {r.status_code}"
            }
        except Exception as e:
            if debug:
                print(f"Exception in standard interface: {str(e)}")
            return {"success": False, "error": f"Standard interface error: {str(e)}"}
    
    def send_request(self, draft_id: str, is_pro: bool = True) -> Dict[str, Any]:
        """
        Send a draft FOI request on AskTheEU.org.
        
        Args:
            draft_id: ID of the draft request
            is_pro: Whether this is a Pro interface draft (default True)
            
        Returns:
            Dict with response info including success status
        """
        if not self._authenticated and not self.login():
            return {"success": False, "error": "Not authenticated"}
        
        if is_pro:
            # Send using Pro interface
            return self._send_pro_request(draft_id)
        else:
            # Send using standard interface
            return self._send_standard_request(draft_id)
    
    def _send_pro_request(self, draft_id: str) -> Dict[str, Any]:
        """Send a request using the Pro interface."""
        # Get the draft page to extract CSRF token
        r = self.session.get(f"{self.domain}/en/alaveteli_pro/info_requests/{draft_id}")
        if r.status_code != 200:
            return {"success": False, "error": f"Failed to access Pro draft request: {r.status_code}"}
            
        draft_page = etree.HTML(r.text)
        token = draft_page.xpath('//input[@name="authenticity_token"]/@value')
        if not token:
            return {"success": False, "error": "Could not find authenticity token"}
        
        # Set headers similar to login headers
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': self.domain,
            'referer': f"{self.domain}/en/alaveteli_pro/info_requests/{draft_id}",
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
        }
        
        # Send the request
        r = self.session.post(
            url=f"{self.domain}/en/alaveteli_pro/info_requests/{draft_id}/send",
            headers=headers,
            data={
                "utf8": "✓",
                "authenticity_token": token[0],
                "commit": "Send request"
            }
        )
        
        # Check for success
        if r.status_code in [200, 302]:
            # Try to extract the public request ID from the response
            request_id = None
            try:
                if 'Location' in r.headers:
                    location = r.headers['Location']
                    if '/request/' in location:
                        request_id = location.split('/request/')[-1].split('/')[0]
            except Exception:
                pass
            
            return {
                "success": True,
                "request_id": request_id,
                "request_url": f"{self.domain}/en/request/{request_id}" if request_id else None
            }
        
        return {
            "success": False,
            "error": f"Failed to send Pro request. Status code: {r.status_code}"
        }
    
    def _send_standard_request(self, draft_id: str) -> Dict[str, Any]:
        """Send a request using the standard interface."""
        # Get the preview page to extract CSRF token
        r = self.session.get(f"{self.domain}/preview/{draft_id}")
        if r.status_code != 200:
            return {"success": False, "error": f"Failed to access standard preview: {r.status_code}"}
            
        preview_page = etree.HTML(r.text)
        token = preview_page.xpath('//input[@name="authenticity_token"]/@value')
        if not token:
            return {"success": False, "error": "Could not find authenticity token in preview"}
        
        # Set headers similar to login headers
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': self.domain,
            'referer': f"{self.domain}/preview/{draft_id}",
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
        }
        
        # Send the request
        r = self.session.post(
            url=f"{self.domain}/preview/{draft_id}",
            headers=headers,
            data={
                "authenticity_token": token[0],
                "submit": "1"
            }
        )
        
        # Check for success
        if r.status_code in [200, 302]:
            # Try to extract the request ID
            request_id = None
            
            # Check if we were redirected to the request
            if "/request/" in r.url:
                try:
                    request_id = r.url.split("/request/")[-1].split("/")[0]
                except Exception:
                    pass
                    
            # If not found in URL, try to parse from the response
            if not request_id:
                try:
                    response_page = etree.HTML(r.text)
                    request_links = response_page.xpath('//a[contains(@href, "/request/")]/@href')
                    
                    for link in request_links:
                        if "/request/" in link:
                            request_id = link.split("/request/")[-1].split("/")[0]
                            break
                except Exception:
                    pass
            
            return {
                "success": True,
                "request_id": request_id,
                "request_url": f"{self.domain}/request/{request_id}" if request_id else None
            }
        
        return {
            "success": False,
            "error": f"Failed to send standard request. Status code: {r.status_code}"
        }
    
    def list_requests(self, page: int = 1) -> Dict[str, Any]:
        """
        List FOI requests made by the authenticated user.
        
        Args:
            page: Page number for paginated results
            
        Returns:
            Dict with list of requests and pagination info
        """
        if not self._authenticated and not self.login():
            return {"success": False, "error": "Not authenticated"}
        
        # Set headers similar to login headers
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
        }
        
        # Try Pro interface first, then fall back to standard
        r = self.session.get(
            f"{self.domain}/en/alaveteli_pro/info_requests?page={page}",
            headers=headers
        )
        
        # If Pro interface isn't available, try standard interface
        if r.status_code != 200:
            r = self.session.get(
                f"{self.domain}/profile/{self.email}/requests?page={page}",
                headers=headers
            )
            
            # Try another standard path if the first fails
            if r.status_code != 200:
                r = self.session.get(
                    f"{self.domain}/request/user?user_name={self.email}&page={page}",
                    headers=headers
                )
                
                if r.status_code != 200:
                    return {"success": False, "error": f"Failed to list requests: {r.status_code}"}
        
        requests_page = etree.HTML(r.text)
        requests = []
        
        # Extract request info from the page - try both Pro and standard patterns
        request_items = (
            requests_page.xpath('//div[contains(@class, "request-list__request")]') or
            requests_page.xpath('//div[contains(@class, "request_listing")]') or
            requests_page.xpath('//div[contains(@class, "request-listing")]')
        )
        
        for item in request_items:
            try:
                # Try different selectors for request title links
                title_elem = (
                    item.xpath('.//a[contains(@class, "request-list__request__title")]') or
                    item.xpath('.//a[contains(@class, "request_listing__title")]') or
                    item.xpath('.//a[contains(@class, "request-listing__title")]') or
                    item.xpath('.//h3/a') or
                    item.xpath('.//h4/a') or
                    item.xpath('.//a')  # Fallback to any link
                )
                
                if not title_elem:
                    continue
                    
                title = title_elem[0].text.strip() if title_elem[0].text else "Untitled Request"
                url = title_elem[0].get('href')
                
                # Some URLs are relative, others are absolute
                if url and not url.startswith('http'):
                    url = url if url.startswith('/') else f"/{url}"
                
                # Try to extract request ID from URL
                request_id = None
                if url and '/request/' in url:
                    request_id = url.split('/request/')[-1].split('/')[0]
                
                # Try to get status and date info looking for different patterns
                status_elem = (
                    item.xpath('.//span[contains(@class, "status")]') or
                    item.xpath('.//div[contains(@class, "status")]') or
                    item.xpath('.//p[contains(@class, "status")]')
                )
                status = status_elem[0].text.strip() if status_elem and status_elem[0].text else "Unknown"
                
                date_elem = (
                    item.xpath('.//time') or
                    item.xpath('.//span[contains(@class, "date")]') or
                    item.xpath('.//div[contains(@class, "date")]')
                )
                date = date_elem[0].text.strip() if date_elem and date_elem[0].text else None
                
                requests.append({
                    "id": request_id,
                    "title": title,
                    "url": f"{self.domain}{url}" if url and not url.startswith('http') else url,
                    "status": status,
                    "date": date
                })
            except Exception:
                # Skip items that can't be parsed
                continue
        
        # Get pagination info
        next_page = requests_page.xpath('//a[@rel="next"]/@href')
        prev_page = requests_page.xpath('//a[@rel="prev"]/@href')
        
        return {
            "success": True,
            "requests": requests,
            "pagination": {
                "current_page": page,
                "next_page": page + 1 if next_page else None,
                "prev_page": page - 1 if prev_page and page > 1 else None
            }
        }


def create_foi_request(
    public_body_id: str,
    request_data: Dict[str, Any],
    email: Optional[str] = None, 
    password: Optional[str] = None,
    domain: str = "https://www.asktheeu.org",
    debug: bool = False
) -> Dict[str, Any]:
    """
    Helper function to create a FOI request with AskTheEU.
    
    Args:
        public_body_id: ID of the public body on AskTheEU.org
        request_data: Dict with title, body, and other request parameters
        email: Optional AskTheEU.org email. If None, uses environment variable.
        password: Optional AskTheEU.org password. If None, uses environment variable.
        domain: AskTheEU.org domain. Defaults to "https://www.asktheeu.org".
        debug: If True, print debug information.
        
    Returns:
        Dict with response info including success status and draft URL
    """
    try:
        client = AskTheEUClient(email=email, password=password, domain=domain)
        if not client.login(debug=debug):
            return {"success": False, "error": "Login failed"}
        
        title = request_data.get("title")
        body = request_data.get("body")
        
        if not title or not body:
            return {"success": False, "error": "Title and body are required"}
        
        return client.create_draft_request(
            public_body_id=public_body_id,
            title=title,
            body=body,
            embargo_duration=request_data.get("embargo_duration", ""),
            debug=debug
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: asktheeu_client.py <public_body_id> <request_title>")
        sys.exit(1)
    
    public_body_id = sys.argv[1]
    title = sys.argv[2]
    
    # Create sample request body
    body = """Dear Sir or Madam,

Referring to Regulation (EC) No 1049/2001 on public access to EU documents and to the 'Aarhus Convention' I would herewith like to ask for access to the following documents:

All documents related to [SUBJECT].

In consideration of the environment I would prefer to receive documents electronically.

Should my request be denied wholly or partially, please explain the denial or all deletions referring to specific exemptions in the regulation.

Please confirm having received this application. I look forward to your reply within 15 business days, according to the regulation.

Yours sincerely,
[YOUR NAME]
"""
    
    # Create client and send request with debug mode
    client = AskTheEUClient()
    if client.login(debug=True):
        result = client.create_draft_request(
            public_body_id=public_body_id,
            title=title,
            body=body,
            debug=True
        )
        print(f"Draft created: {result}")
    else:
        print("Login failed")