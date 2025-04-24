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
        embargo_duration: str = ""
    ) -> Dict[str, Any]:
        """
        Create a draft FOI request on AskTheEU.org using the Alaveteli Pro interface.
        
        Args:
            public_body_id: ID of the public body on AskTheEU.org
            title: Title of the FOI request
            body: Body text of the FOI request
            embargo_duration: Optional embargo duration (e.g., "3_months")
            
        Returns:
            Dict with response info including success status and draft URL if successful
        """
        if not self._authenticated and not self.login():
            return {"success": False, "error": "Not authenticated"}
        
        # Get the new request page to extract CSRF token
        r = self.session.get(f"{self.domain}/en/alaveteli_pro/info_requests/new")
        if r.status_code != 200:
            return {"success": False, "error": f"Failed to access new request page: {r.status_code}"}
            
        request_page = etree.HTML(r.text)
        token = request_page.xpath('//input[@name="authenticity_token"]/@value')
        if not token:
            return {"success": False, "error": "Could not find authenticity token"}
        
        # Set headers similar to login headers
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': self.domain,
            'referer': f"{self.domain}/en/alaveteli_pro/info_requests/new",
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
        }
        
        # Create draft request
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
                                    "draft_id": draft_id,
                                    "draft_url": f"{self.domain}/en/alaveteli_pro/info_requests/{draft_id}"
                                }
            except Exception as e:
                return {"success": False, "error": f"Error parsing response: {str(e)}"}
        
        return {
            "success": False,
            "error": f"Failed to create draft request. Status code: {r.status_code}"
        }
    
    def send_request(self, draft_id: str) -> Dict[str, Any]:
        """
        Send a draft FOI request on AskTheEU.org.
        
        Args:
            draft_id: ID of the draft request
            
        Returns:
            Dict with response info including success status
        """
        if not self._authenticated and not self.login():
            return {"success": False, "error": "Not authenticated"}
        
        # Get the draft page to extract CSRF token
        r = self.session.get(f"{self.domain}/en/alaveteli_pro/info_requests/{draft_id}")
        if r.status_code != 200:
            return {"success": False, "error": f"Failed to access draft request: {r.status_code}"}
            
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
            "error": f"Failed to send request. Status code: {r.status_code}"
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
        
        r = self.session.get(
            f"{self.domain}/en/alaveteli_pro/info_requests?page={page}",
            headers=headers
        )
        if r.status_code != 200:
            return {"success": False, "error": f"Failed to list requests: {r.status_code}"}
        
        requests_page = etree.HTML(r.text)
        requests = []
        
        # Extract request info from the page
        request_items = requests_page.xpath('//div[contains(@class, "request-list__request")]')
        for item in request_items:
            try:
                title_elem = item.xpath('.//a[contains(@class, "request-list__request__title")]')
                if not title_elem:
                    continue
                    
                title = title_elem[0].text.strip()
                url = title_elem[0].get('href')
                request_id = url.split('/')[-1] if url else None
                
                # Try to get status and date info
                status = item.xpath('.//span[contains(@class, "request-list__request__status")]/text()')
                date = item.xpath('.//time/text()')
                
                requests.append({
                    "id": request_id,
                    "title": title,
                    "url": f"{self.domain}{url}" if url else None,
                    "status": status[0].strip() if status else "Unknown",
                    "date": date[0].strip() if date else None
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
    domain: str = "https://www.asktheeu.org"
) -> Dict[str, Any]:
    """
    Helper function to create a FOI request with AskTheEU.
    
    Args:
        public_body_id: ID of the public body on AskTheEU.org
        request_data: Dict with title, body, and other request parameters
        email: Optional AskTheEU.org email. If None, uses environment variable.
        password: Optional AskTheEU.org password. If None, uses environment variable.
        domain: AskTheEU.org domain. Defaults to "https://www.asktheeu.org".
        
    Returns:
        Dict with response info including success status and draft URL
    """
    try:
        client = AskTheEUClient(email=email, password=password, domain=domain)
        if not client.login():
            return {"success": False, "error": "Login failed"}
        
        title = request_data.get("title")
        body = request_data.get("body")
        
        if not title or not body:
            return {"success": False, "error": "Title and body are required"}
        
        return client.create_draft_request(
            public_body_id=public_body_id,
            title=title,
            body=body,
            embargo_duration=request_data.get("embargo_duration", "")
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
    
    # Create client and send request
    client = AskTheEUClient()
    if client.login():
        result = client.create_draft_request(
            public_body_id=public_body_id,
            title=title,
            body=body
        )
        print(f"Draft created: {result}")
    else:
        print("Login failed")