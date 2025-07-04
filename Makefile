.PHONY: setup install clean test test-login test-draft list-requests

# Main setup task - installs dependencies
setup: install

# Install dependencies
install:
	pip install -r requirements.txt

# Test login functionality
test-login:
	python tests/test_login.py

# Test draft request creation to Secretariat General
test-draft:
	python tests/test_draft_request.py

# List FOI requests
list-requests:
	python examples/list_requests.py

# Clean up generated files
clean:
	rm -rf *.pyc __pycache__ .pytest_cache tests/__pycache__ examples/__pycache__ *.html