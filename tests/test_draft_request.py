#!/usr/bin/env python3
"""
Test script for creating and sending a draft FOI request to the Secretariat General.
Includes detailed debug information to identify failure points.
"""

import os
import sys
import time
from pathlib import Path

# Add parent directory to path so we can import asktheeu_client
sys.path.append(str(Path(__file__).parent.parent))

from asktheeu_client import AskTheEUClient

def test_draft_request_to_sg():
    """
    Test creating and sending a draft FOI request to the Secretariat General.
    Includes detailed debug information at each step.
    """
    print("\n" + "="*80)
    print("TESTING DRAFT REQUEST TO SECRETARIAT GENERAL")
    print("="*80)
    
    # Check credentials
    email = os.environ.get("ASKTHEEU_EMAIL")
    password = os.environ.get("ASKTHEEU_PASSWORD")
    
    if not email or not password:
        print("❌ ERROR: Missing credentials")
        print("Make sure ASKTHEEU_EMAIL and ASKTHEEU_PASSWORD are set in your .env file")
        return False
    
    print(f"✓ Using email: {email}")
    print(f"✓ Password is set: {'*' * len(password)}")
    
    # Create client
    client = AskTheEUClient(email=email, password=password)
    print("✓ Client created")
    
    # Step 1: Login
    print("\n" + "-"*50)
    print("STEP 1: LOGGING IN TO ASKTHEEU.ORG")
    print("-"*50)
    
    login_result = client.login(debug=True)
    
    if not login_result:
        print("\n❌ LOGIN FAILED")
        print("See login_response.html for details on the failure")
        return False
    
    print("\n✅ LOGIN SUCCESSFUL")
    
    # Step 2: Create draft request
    print("\n" + "-"*50)
    print("STEP 2: CREATING DRAFT REQUEST TO SECRETARIAT GENERAL")
    print("-"*50)
    
    # Public body ID for Secretariat General is 576
    public_body_id = "576"
    title = "TEST REQUEST - Documents related to gas infrastructure (DELETE ME)"
    body = """Dear Secretariat General of the European Commission,

Under the right of access to documents in the EU treaties, as developed in Regulation 1049/2001, I am requesting documents which contain the following information:

All documents—including but not limited to meeting minutes, emails, presentations, and briefing materials—related to gas infrastructure projects from January 1, 2023 to present.

This is a test request for debugging purposes. Please ignore or delete this request.

Yours faithfully,

Test User
"""
    
    print(f"Request to: Secretariat General (ID: {public_body_id})")
    print(f"Title: {title}")
    print(f"Body length: {len(body)} characters")
    
    # Manually check the new request page and token before attempting creation
    print("\nChecking for authenticity token on new request page...")
    try:
        r = client.session.get(f"{client.domain}/en/alaveteli_pro/info_requests/new")
        print(f"- Request page status code: {r.status_code}")
        
        # Save the full page for debugging
        with open("new_request_page.html", "w", encoding="utf-8") as page_file:
            page_file.write(r.text)
            print(f"- Saved full page to new_request_page.html")
        
        # Parse and look for token
        from lxml import etree
        request_page = etree.HTML(r.text)
        
        # Try different token selectors
        token_selectors = [
            '//input[@name="authenticity_token"]/@value',
            '//meta[@name="csrf-token"]/@content',
            '//input[contains(@name, "token")]/@value'
        ]
        
        found_token = None
        for selector in token_selectors:
            tokens = request_page.xpath(selector)
            if tokens:
                found_token = tokens[0]
                print(f"- Found token with selector '{selector}': {found_token[:10]}...")
                break
        
        if not found_token:
            print("❌ No authenticity token found in the page!")
            
            # Check if page has form elements at all
            forms = request_page.xpath('//form')
            print(f"- Page contains {len(forms)} form elements")
            
            # Check if page title suggests we're not logged in or no access
            title = request_page.xpath('//title/text()')
            if title:
                print(f"- Page title: {title[0]}")
            
            print("- This may indicate you don't have Alaveteli Pro access or aren't properly logged in")
    except Exception as e:
        print(f"❌ Error checking for token: {str(e)}")
    
    # Create draft request with debug file
    with open("draft_request_debug.html", "w") as debug_file:
        debug_file.write(f"Attempting to create draft request to SG (ID: {public_body_id})\n")
        debug_file.write(f"Title: {title}\n\n")
        
        try:
            # Create draft request with debug enabled
            print("\nSending draft request to AskTheEU.org...")
            result = client.create_draft_request(
                public_body_id=public_body_id,
                title=title,
                body=body,
                debug=True
            )
            
            # Save result to debug file
            debug_file.write("\nResult:\n")
            for key, value in result.items():
                debug_file.write(f"- {key}: {value}\n")
                print(f"- {key}: {value}")
            
            if not result.get("success"):
                print("\n❌ DRAFT CREATION FAILED")
                print(f"Error: {result.get('error', 'Unknown error')}")
                return False
            
            draft_id = result.get("draft_id")
            draft_url = result.get("draft_url")
            
            if not draft_id:
                print("\n❌ DRAFT CREATION FAILED - No draft ID returned")
                return False
                
            print(f"\n✅ DRAFT CREATED SUCCESSFULLY: {draft_url}")
            
            # Step 3: Send the request (optional - commented out by default)
            print("\n" + "-"*50)
            print("STEP 3: SENDING THE REQUEST (OPTIONAL)")
            print("-"*50)
            print("NOTE: This step is commented out to prevent actual submission")
            print("To submit the request, uncomment the code below")
            
            debug_file.write("\n\nSend Request Step:\n")
            debug_file.write("This step is commented out to prevent actual submission\n")
            
            """
            # Uncomment to actually send the request
            print("\nWaiting 5 seconds before sending...")
            time.sleep(5)
            
            send_result = client.send_request(draft_id)
            
            # Save send result to debug file
            debug_file.write("\nSend Result:\n")
            for key, value in send_result.items():
                debug_file.write(f"- {key}: {value}\n")
                print(f"- {key}: {value}")
            
            if not send_result.get("success"):
                print("\n❌ REQUEST SENDING FAILED")
                print(f"Error: {send_result.get('error', 'Unknown error')}")
                return False
                
            request_url = send_result.get("request_url")
            if not request_url:
                print("\n❌ REQUEST SENDING FAILED - No request URL returned")
                return False
                
            print(f"\n✅ REQUEST SENT SUCCESSFULLY: {request_url}")
            """
            
            return True
            
        except Exception as e:
            error_msg = f"Error creating draft request: {str(e)}"
            debug_file.write(f"\n\nEXCEPTION: {error_msg}\n")
            print(f"\n❌ EXCEPTION: {error_msg}")
            return False

if __name__ == "__main__":
    # Set up environment variables from .env file if it exists
    env_path = Path(".env")
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
    
    # Run the test
    success = test_draft_request_to_sg()
    
    # Print final result
    print("\n" + "="*80)
    if success:
        print("✅ TEST PASSED: Successfully created a draft FOI request to the Secretariat General")
    else:
        print("❌ TEST FAILED: Could not create a draft FOI request")
    print("="*80 + "\n")
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)