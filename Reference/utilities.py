import hashlib


def compute_sha1(filename):
    BUFFER_SIZE = 131072  # 128KB blocks
    sha1 = hashlib.sha1()
    #filename = 'test.txt'

    with open(filename, 'rb') as f:
        while True:
            data = f.read(BUFFER_SIZE)
            if not data:
                break
            sha1.update(data)

    #print("SHA1: {0}".format(sha1.hexdigest()))
    return sha1.hexdigest()