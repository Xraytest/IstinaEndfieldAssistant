from setuptools import setup, find_packages
import os

# Read the README file
with open(os.path.join(os.path.dirname(__file__), '..', 'README.md'), 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='maa-touch-controller',
    version='1.0.0',
    description='A standalone touch control system extracted from MAA for Python applications',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='MAA Touch Controller',
    author_email='noreply@example.com',
    url='https://github.com/your-username/maa-touch-controller',
    packages=find_packages(),
    package_data={
        'maa_touch_controller': ['../resources/minitouch/**/*', '../src/api/*.js'],
    },
    include_package_data=True,
    install_requires=[
        # No Python dependencies required, but Node.js is required
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    python_requires='>=3.7',
    keywords='maa, touch, adb, minitouch, android, automation',
)