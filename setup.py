from setuptools import setup, find_packages

setup(
    name='chalbe',
    version='0.1.0',
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
    entry_points='''
        [console_scripts]
        chal=src.commands:cli
    ''',
)
