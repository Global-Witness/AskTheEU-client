#!/usr/bin/env python3
"""
Script to list FOI requests using the AskTheEU.org client.
"""

from asktheeu_client import AskTheEUClient
import json

def main():
    # Create client (will use credentials from .env file)
    client = AskTheEUClient()
    
    # Log in to AskTheEU.org
    print("Logging in to AskTheEU.org...")
    if client.login():
        print("Login successful")
        
        # List FOI requests
        print("\nListing your FOI requests...\n")
        result = client.list_requests()
        
        if result["success"]:
            # Pretty print the result
            print(f"Found {len(result['requests'])} requests:")
            for i, request in enumerate(result["requests"], 1):
                print(f"\n{i}. {request['title']}")
                print(f"   Status: {request['status']}")
                print(f"   Date: {request['date']}")
                print(f"   URL: {request['url']}")
            
            # Show pagination info
            pagination = result["pagination"]
            print(f"\nPage: {pagination['current_page']}")
            if pagination["next_page"]:
                print(f"There are more requests on page {pagination['next_page']}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    else:
        print("Login failed. Check your credentials in the .env file.")

if __name__ == "__main__":
    main()