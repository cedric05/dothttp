import os
from setuptools import setup, find_packages


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


def requirements():
    return [req.split(';')[0] for req in read('requirements.txt').split('\n')]


setup(
    name="dothttp_req",
    version="0.0.4",
    author="prasanth",
    author_email="kesavarapu.siva@gmail.com",
    description=("DotHttp recommended tool for making http requests."),
    license="MIT",
    package_data={
        "": ["*.tx", "*.md"]
    },
    entry_points={
        'console_scripts': ['dothttp=dothttp.__main__:main'],
    },
    packages=find_packages(),
    install_requires=requirements(),
    long_description=read('README.md'),
    long_description_content_type=('text/markdown'),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
