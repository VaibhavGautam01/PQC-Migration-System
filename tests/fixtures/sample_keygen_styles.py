# Fixture 4: key-size styles
from Crypto.PublicKey import RSA
from Crypto.Util import number

KEY_BITS = 3072
k1 = RSA.generate(2048)
k2 = RSA.generate(KEY_BITS)
k3 = rsa.generate_private_key(public_exponent=65537, key_size=4096)
pub, priv = generate_keypair(bits=128)
pub2, priv2 = generate_keypair(key_size=1024)

def make(key_size=2048):
    half = key_size // 2
    p = number.getPrime(half)
    q = number.getPrime(256)
    return p, q
