# Payment Service Setup Configuration
from setuptools import setup, find_packages

setup(
    name="payment-svc",
    version="1.0.0",
    description="AIVO Payment Service with Stripe integration",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "stripe>=7.8.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "structlog>=23.2.0",
        "httpx>=0.25.2",
        "sqlalchemy>=2.0.23",
        "redis>=5.0.1"
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1", 
            "pytest-mock>=3.14.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "pact-python>=2.0.1"
        ]
    },
    python_requires=">=3.9",
    author="AIVO Engineering",
    author_email="engineering@aivo.com",
    url="https://github.com/aivo-ai/aivo-virtual-brain",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ]
)
