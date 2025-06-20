from setuptools import setup

setup(
    name="smart_ai",
    version="0.1",
    packages=['smart_ai'],
    package_dir={'smart_ai': 'app'},
    install_requires=[
        line.strip() for line in open('requirements.txt') if line.strip()
    ],
)