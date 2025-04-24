#!/usr/bin/env python3
"""
Test script for AskTheEU.org login.
"""

from asktheeu_client import AskTheEUClient

def main():
    client = AskTheEUClient()
    print("Attempting to log in to AskTheEU.org...\n")
    result = client.login(debug=True)
    print("\nFinal result:", "Login successful" if result else "Login failed")

if __name__ == "__main__":
    main()