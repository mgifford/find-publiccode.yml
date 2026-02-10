#!/bin/bash
# Setup script for publiccode.yml discovery framework

set -e

echo "=================================="
echo "PublicCode.yml Framework Setup"
echo "=================================="
echo

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "Error: Python 3 not found"; exit 1; }
echo "✓ Python 3 available"
echo

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo

# Install Python dependencies
echo "Installing Python dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt
echo "✓ Python dependencies installed"
echo

# Check for Go
echo "Checking for Go..."
if ! command -v go &> /dev/null; then
    echo "⚠ Go not found. The publiccode-parser validator requires Go."
    echo
    echo "To install Go on macOS:"
    echo "  brew install go"
    echo
    echo "Or download from: https://go.dev/dl/"
    echo
    echo "The framework will run without the validator, but spec compliance"
    echo "validation will be skipped."
    echo
else
    go version
    echo "✓ Go available"
    echo
    
    # Install publiccode-parser
    echo "Installing publiccode-parser..."
    go install github.com/italia/publiccode-parser-go/v5/publiccode-parser@latest
    
    # Check if it's in PATH
    if command -v publiccode-parser &> /dev/null; then
        echo "✓ publiccode-parser installed successfully"
        publiccode-parser --version || true
    else
        echo "⚠ publiccode-parser installed but not in PATH"
        echo
        echo "Add this to your ~/.zshrc or ~/.bash_profile:"
        echo "  export PATH=\$PATH:\$HOME/go/bin"
        echo
        echo "Then run: source ~/.zshrc"
    fi
fi

echo
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo
echo "IMPORTANT: Activate the virtual environment before running:"
echo "  source venv/bin/activate"
echo
echo "To test the framework:"
echo "  python3 main.py --limit 5 --output test_results.csv"
echo
echo "To run on all domains:"
echo "  python3 main.py --input eu_gov_domains.csv --output results.csv"
echo
echo "For help:"
echo "  python3 main.py --help"
echo
