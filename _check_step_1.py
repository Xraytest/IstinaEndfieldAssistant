# Minimal test - verify PIL and check screenshot
import os, sys

# Print Python info
print('Python:', sys.executable)
print('Version:', sys.version)

# Test PIL
from PIL import Image
print('PIL version:', Image.__version__)

# Check screenshot
img = Image.open('cache/screenshot_check.png')
print('Screenshot:', img.size, img.mode)

print('All OK')
