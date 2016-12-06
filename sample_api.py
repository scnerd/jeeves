"""
"""

def add(x, y):
    return x + y

def hostname():
    '''
    jeeves.content=nozip
    '''
    import socket
    hn = socket.gethostname()
    print(hn)
    return hn

def complex_signature(a, b, *, c, d, e=1, f=2, **kwargs):
    return a

def complex_signature2(a, b, *args, e=1, f=2, **kwargs):
    return b