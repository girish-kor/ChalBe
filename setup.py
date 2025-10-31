import re
from setuptools import setup, find_packages

# Read the version from src/__init__.py
with open("src/__init__.py", "r") as f:
    version_match = re.search(r"^__version__\s*=\s*['\"]([^'\"]*)['\"]", f.read(), re.MULTILINE)
    if version_match:
        __version__ = version_match.group(1)
    else:
        __version__ = "0.0.0" # Fallback


setup(
    name='chalbe',
    version=__version__, # Use the dynamically read version
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'python-dotenv',
        'openai',
        'google-generativeai',
        'anthropic',
        'mistralai',
        'cohere',
        'huggingface-hub',
        'replicate',
        'together',
        'boto3',
    ],
    entry_points={
        'console_scripts': [
            'chal=src.commands:cli',
        ],
    },
)
