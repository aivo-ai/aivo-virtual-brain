# Payment Service Commands
# Windows PowerShell compatible development commands

# Install dependencies
install:
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run test suite
test:
python -m pytest tests/ -v

# Run linting
lint:
python -m flake8 app/ --max-line-length=100

# Format code  
format:
python -m black app/ tests/ --line-length=100

# Run development server
run:
python -m uvicorn main:app --host 0.0.0.0 --port 8004 --reload

# Clean up
clean:
Get-ChildItem -Path . -Recurse -Name "*.pyc" | Remove-Item
Get-ChildItem -Path . -Recurse -Name "__pycache__" | Remove-Item -Recurse
