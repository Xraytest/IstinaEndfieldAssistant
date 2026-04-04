"""
MAA Touch Controller - Setup Configuration
"""

from setuptools import setup, find_packages
import os

# Read README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
requirements = []
if os.path.exists("requirements.txt"):
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="maa-touch-controller",
    version="1.0.0",
    author="MAA Touch Controller",
    author_email="noreply@example.com",
    description="A standalone touch control system extracted from MAA for Python applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/maa-touch-controller",
    packages=find_packages(),
    package_data={
        "maa_touch_controller": ["../minitouch_resources/**/*"],
    },
    include_package_data=True,
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    keywords="maa, touch, adb, minitouch, android, automation",
)