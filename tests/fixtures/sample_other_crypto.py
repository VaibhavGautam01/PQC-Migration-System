# Fixture 3: non-RSA primitives (ECC / DSA / DH / AES / SHA)
import hashlib
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from Crypto.Cipher import AES

key = ec.generate_private_key(ec.SECP256R1())
sig = key.sign(data, ec.ECDSA(hashes.SHA256()))
shared = key.exchange(ec.ECDH(), peer_pub)
box = AES.new(k, AES.MODE_ECB)
aead = AESGCM(key)
cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
# using AES-256 for bulk data
digest = hashlib.sha256(data).hexdigest()
h3 = hashlib.sha3_512(data)
old = hashlib.md5(data)
h = SHA384.new(data)
f = Fernet(Fernet.generate_key())
dsa_key = dsa.generate_private_key(key_size=2048)
params = dh.generate_parameters(generator=2, key_size=2048)
