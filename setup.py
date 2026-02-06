from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="real-time-analytics-platform",
    version="0.1.0",
    author="Manali Verma",
    author_email="your.email@example.com",
    description="Enterprise-grade real-time data streaming and analytics platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/manaliverma/real-time-analytics-platform",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Monitoring",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    python_requires=">=3.9",
    install_requires=[
        "kafka-python>=2.0.0",
        "pydantic>=2.0.0",
        "jsonschema>=4.0.0",
        "prometheus-client>=0.17.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
        ],
    },
)
