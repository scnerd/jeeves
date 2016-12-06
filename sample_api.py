"""
"""

def add(x, y):
    return x + y

def hostname():
    import socket
    hn = socket.gethostname()
    print(hn)
    return hn