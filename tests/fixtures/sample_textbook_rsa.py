# Fixture: textbook RSA with no padding (used to sanity-check scanner.py)
from Crypto.PublicKey import RSA
from Crypto.Util.number import getPrime
import rsa

key = RSA.generate(1024)
(pub, priv) = rsa.newkeys(512)
p = getPrime(512)
q = getPrime(512)
n = p * q
phi = (p - 1) * (q - 1)
d = pow(e, -1, phi)
cipher = pow(m, e, n)
