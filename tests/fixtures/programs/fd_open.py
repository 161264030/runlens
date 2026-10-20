import time

files = [open("/dev/null", "rb") for _ in range(24)]
try:
    time.sleep(0.4)
finally:
    for stream in files:
        stream.close()
