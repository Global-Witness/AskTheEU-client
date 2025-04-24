# AskTheEU.org Client

A Python client for interacting with AskTheEU.org to create and manage freedom of information requests to EU institutions.
This logic mostly follows previous work from the Data Investigations Team on monitoring meetings between the European Commission and the gas lobby – [see here](https://github.com/Global-Witness/eu-gas-detector).

Note: [it requires a Pro subscription.](https://github.com/Global-Witness/AskTheEU-client/issues/1)

## Requirements

- Python 3.9+
- Make

## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/gw-asktheeu-client.git
   cd gw-asktheeu-client
   ```

2. Copy the example environment file and configure your credentials:

   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. Install dependencies:

   ```bash
   make setup
   ```

4. The `data/public-bodies.csv` file contains a mapping of institution URLs to their IDs.
   A sample file is provided, but you may need to update it with actual IDs from AskTheEU.org.

## Testing

You can test your login credentials with:

```bash
make test-login
```

To test creating a draft FOI request to the Secretariat General:

```bash
make test-draft
```

This will create a draft request (but not send it) and provide detailed debug information.

## Making Requests

The client is flexible and will try multiple methods to create FOI requests:

1. First attempts using the Alaveteli Pro interface
2. If Pro access isn't available, falls back to standard interface
3. Login matches the format shown in the example.txt file
4. Supports draft creation and sending FOI requests
5. Provides detailed debugging information when needed

## Usage

Basic example of creating a draft FOI request:

```python
from asktheeu_client import AskTheEUClient

# Create client (will use credentials from .env file)
client = AskTheEUClient()

# Log in to AskTheEU.org with debugging enabled
if client.login(debug=True):
    # Create a draft FOI request (tries Pro interface first, then falls back to standard)
    result = client.create_draft_request(
        public_body_id="576",  # ID of the institution (e.g., 576 for Secretariat General)
        title="Request for documents related to X",
        body="Dear Sir/Madam,\n\nUnder Regulation 1049/2001, I am requesting access to documents concerning X...\n\nYours faithfully,",
        debug=True  # Enable detailed debugging output
    )

    if result["success"]:
        print(f"Draft created: {result['draft_url']}")
        print(f"Interface used: {result.get('method', 'unknown')}")

        # Optionally send the request
        # Note: is_pro parameter should match the method used to create the draft
        is_pro = result.get('method') == 'pro_interface'
        send_result = client.send_request(result["draft_id"], is_pro=is_pro)
        if send_result["success"]:
            print(f"Request sent: {send_result['request_url']}")
    else:
        print(f"Error creating draft: {result.get('error')}")
else:
    print("Login failed")
```
