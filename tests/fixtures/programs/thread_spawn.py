import threading
import time

threads = [threading.Thread(target=time.sleep, args=(0.4,)) for _ in range(5)]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()
