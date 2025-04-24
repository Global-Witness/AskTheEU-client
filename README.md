# AskTheEU.org Client

A Python client for interacting with AskTheEU.org to create and manage freedom of information requests to EU institutions.
This logic mostly follows previous work from the Data Investigations Team on monitoring meetings between the European Commission and the gas lobby – [see here](https://github.com/Global-Witness/eu-gas-detector).

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

## Making Requests

The client uses the Alaveteli Pro interface of AskTheEU.org to create FOI requests:

- Uses the `/en/alaveteli_pro/info_requests/new` endpoint
- Login matches the format shown in the example.txt file
- Supports draft creation and sending FOI requests

## Usage

Basic example of creating a draft FOI request:

```python
from asktheeu_client import AskTheEUClient

# Create client (will use credentials from .env file)
client = AskTheEUClient()

# Log in to AskTheEU.org
if client.login():
    # Create a draft FOI request using the Alaveteli Pro interface
    result = client.create_draft_request(
        public_body_id="576",  # ID of the institution (e.g., 576 for Secretariat General)
        title="Request for documents related to X",
        body="Dear Sir/Madam,\n\nUnder Regulation 1049/2001, I am requesting access to documents concerning X...\n\nYours faithfully,"
    )

    if result["success"]:
        print(f"Draft created: {result['draft_url']}")

        # Optionally send the request
        send_result = client.send_request(result["draft_id"])
        if send_result["success"]:
            print(f"Request sent: {send_result['request_url']}")
    else:
        print(f"Error creating draft: {result.get('error')}")
else:
    print("Login failed")
```
