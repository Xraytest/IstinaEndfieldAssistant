import time,subprocess
adb = ['3rd-party/adb/adb.exe','-s','localhost:16512','shell','input']

# Tap outside dialog (top-left corner)
subprocess.run(adb + ['tap','100','100'],capture_output=True)
time.sleep(3)

# Screenshot result
subprocess.run(['3rd-party/adb/adb.exe','-s','localhost:16512','shell','screencap','-p','/sdcard/screen.png'],capture_output=True)
subprocess.run(['3rd-party/adb/adb.exe','-s','localhost:16512','pull','/sdcard/screen.png','cache/screenshot_current.png'],capture_output=True)
