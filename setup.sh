#!/bin/bash
# setup.sh - Quick setup script for the project

set -e  # Exit on error

echo "================================================"
echo "Nutrition & Sports Health RAQA - Setup Script"
echo "================================================"
echo ""

# Check Python version
echo "✓ Checking Python version..."
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "  Python version: $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "✓ Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "  Virtual env already exists. Skipping creation."
else
    python3 -m venv .venv
    echo "  Created .venv/"
fi

# Activate virtual environment
echo ""
echo "✓ Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo ""
echo "✓ Upgrading pip..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1

# Install dependencies
echo ""
echo "✓ Installing project dependencies..."
pip install -r requirements.txt

# Run tests
echo ""
echo "✓ Running tests..."
python3 -m pytest tests/test_data.py -v

echo ""
echo "================================================"
echo "Setup complete! ✓"
echo "================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source .venv/bin/activate"
echo ""
echo "2. Run the API:"
echo "   uvicorn app.main:app --reload"
echo ""
echo "3. In another terminal, run the demo:"
echo "   streamlit run demo.py"
echo ""
echo "4. Or use Docker Compose:"
echo "   docker-compose up"
echo ""
echo "For more details, see README.md"
echo ""
