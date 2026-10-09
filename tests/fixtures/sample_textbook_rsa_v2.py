# Fixture 2: other common textbook-RSA styles
import random
from math import gcd
from sympy import randprime, mod_inverse

p = randprime(2**511, 2**512)
q = randprime(2**511, 2**512)
n = p * q
phi = (p - 1) * (q - 1)
e = 65537
d = mod_inverse(e, phi)
d2 = modinv(e, phi)

def encrypt(m, e, n):
    return pow(m, e, n)

def decrypt(c, d, n):
    return (c ** d) % n

cipher = [pow(ord(ch), e, n) for ch in "hello"]
