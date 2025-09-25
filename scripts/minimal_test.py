#!/usr/bin/env python3
"""Minimal test to check what's wrong with the thread safety tests."""

import threading
import time

def basic_test():
    """Simple test that should work."""
    print("Testing basic threading...")

    counter = 0
    lock = threading.Lock()

    def worker():
        nonlocal counter
        for _ in range(10):
            with lock:
                counter += 1

    # Start 2 threads
    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print(f"Counter: {counter}, Expected: 20")
    return counter == 20

if __name__ == "__main__":
    success = basic_test()
    print(f"Result: {'PASS' if success else 'FAIL'}")