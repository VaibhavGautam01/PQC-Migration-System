"""
extra_patterns.py - Day 3: crypto patterns beyond RSA.

Direct rule of the quantum threat:
  - Shor's algorithm   -> completely breaks RSA, ECC, DSA, DH
  - Grover's algorithm -> roughly halves the strength of AES, SHA
So every finding carries a "primitive" label, so that Stage 2 (mapper)
can apply the correct quantum algorithm.
"""


def mk(pid, prim, rx, desc, conf, keygen=False):
    """Builds one pattern dict (same format as the RSA patterns).

    pid    : unique name, shown in the report (e.g. ECC-ECDSA)
    prim   : crypto family (ECC / DSA / DH / AES / SHA)
    rx     : regex that is matched against a single line
    desc   : human-readable explanation
    conf   : high / medium / low (how confident we are that it is really crypto)
    keygen : if True, the scanner will try to extract the key size
             (if there is a (?P<bits>...) group, that becomes the size)
    """
    return {"id": pid, "primitive": prim, "regex": rx, "desc": desc,
            "confidence": conf, "keygen": keygen}


EXTRA_PATTERNS = []

# ---------------- ECC (broken by Shor) ----------------
EXTRA_PATTERNS += [
    mk("ECC-GEN-CRYPTOGRAPHY", "ECC", r'\bec\.generate_private_key\s*\(',
       "ECC key generation (cryptography lib)", "high"),
    mk("ECC-GEN-PYCRYPTODOME", "ECC", r'\bECC\.generate\s*\(',
       "ECC key generation (PyCryptodome)", "high"),
    mk("ECC-GEN-JAVA", "ECC",
       r'KeyPairGenerator\.getInstance\(\s*"(?:EC|ECDSA|ECDH|XDH|EdDSA)"',
       "ECC key generation (Java KeyPairGenerator)", "high"),
    # The key size comes straight from the curve name (SECP256R1 = 256 bit)
    mk("ECC-CURVE-NAME", "ECC", r'\b(?:SECP|secp)(?P<bits>256|384|521)[rRkK]1\b',
       "Named SECG/NIST elliptic curve", "high", True),
    mk("ECC-CURVE-PNAME", "ECC", r'\bcurve\s*=\s*.P-(?P<bits>256|384|521)',
       "NIST P-curve selected by name", "high", True),
    mk("ECC-ECDSA", "ECC", r'\bec\.ECDSA\s*\(|\becdsa\.(?:SigningKey|VerifyingKey)\b',
       "ECDSA signing/verification", "high"),
    mk("ECC-ECDH", "ECC", r'\bec\.ECDH\s*\(|\bX25519PrivateKey\b|\bX448PrivateKey\b',
       "ECDH / X25519 key exchange", "high"),
    mk("ECC-EDDSA", "ECC", r'\bEd25519PrivateKey\b|\bEd448PrivateKey\b',
       "EdDSA signatures (Ed25519/Ed448)", "high"),
    mk("ECC-CLI", "ECC",
       r'openssl\s+ecparam|ssh-keygen\s+.*-t\s+(?:ecdsa|ed25519)',
       "ECC key generation via CLI", "high"),
    # Import is only "medium": an import does not mean it was actually used
    mk("ECC-IMPORT", "ECC",
       r'from\s+cryptography\.hazmat\.primitives\.asymmetric\s+import\s+.*\b(?:ec|ed25519|x25519)\b'
       r'|from\s+ecdsa\s+import|^\s*import\s+ecdsa\b'
       r'|from\s+Crypto\.PublicKey\s+import\s+.*\bECC\b',
       "Imports an ECC library", "medium"),
]

# ---------------- DSA / DH (broken by Shor) ----------------
EXTRA_PATTERNS += [
    mk("DSA-GEN", "DSA",
       r'\bdsa\.generate_private_key\s*\(|\bDSA\.generate\s*\(\s*(?P<bits>\d+)?',
       "DSA key generation", "high", True),
    mk("DH-GEN", "DH",
       r'\bdh\.generate_parameters\s*\(|KeyPairGenerator\.getInstance\(\s*"DH"|\bDiffieHellman\b',
       "Diffie-Hellman parameter/key generation", "medium", True),
]

# ---------------- AES (symmetric: Grover, effective key size is halved) ----------------
EXTRA_PATTERNS += [
    mk("AES-NEW", "AES", r'\bAES\.new\s*\(',
       "AES cipher (PyCryptodome)", "high"),
    mk("AES-CRYPTOGRAPHY", "AES",
       r'\balgorithms\.AES\s*\(|\bAESGCM\s*\(|\bAESCCM\s*\(',
       "AES cipher (cryptography lib)", "high"),
    mk("AES-JAVA", "AES",
       r'(?:Cipher|KeyGenerator)\.getInstance\(\s*"AES|SecretKeySpec\(.*"AES"',
       "AES usage (Java)", "high"),
    mk("AES-FERNET", "AES", r'\bFernet\s*\(|\bFernet\.generate_key\s*\(',
       "Fernet (AES-128-CBC + HMAC)", "medium"),
    # ECB mode is a separate issue from quantum; it is also weak classically (leaks patterns)
    mk("AES-ECB", "AES", r'\bAES\.MODE_ECB\b|AES/ECB',
       "AES in ECB mode (classically weak mode)", "high"),
    # Text like "AES-256" can also appear in comments/UI strings, hence low
    mk("AES-VARIANT", "AES", r'\bAES[-_]?(?P<bits>128|192|256)\b',
       "AES key size named in code/comment", "low", True),
    mk("AES-IMPORT", "AES",
       r'from\s+Crypto\.Cipher\s+import\s+.*\bAES\b'
       r'|from\s+cryptography\.hazmat\.primitives\.ciphers\.aead\s+import\s+.*AES',
       "Imports an AES implementation", "medium"),
]

# ---------------- Hashes: SHA family (Grover) ----------------
# bits = digest size (256 etc.), will be useful for the Grover estimate in Week 3
EXTRA_PATTERNS += [
    mk("HASH-SHA2-HASHLIB", "SHA", r'\bhashlib\.sha(?P<bits>224|256|384|512)\b',
       "SHA-2 hash (hashlib)", "high", True),
    mk("HASH-SHA3-HASHLIB", "SHA", r'\bhashlib\.sha3_(?P<bits>224|256|384|512)\b',
       "SHA-3 hash (hashlib)", "high", True),
    mk("HASH-HASHLIB-NEW", "SHA", r'\bhashlib\.new\(\s*.sha(?P<bits>224|256|384|512)',
       "SHA-2 hash via hashlib.new()", "high", True),
    mk("HASH-SHA2-PYCRYPTODOME", "SHA", r'\bSHA(?P<bits>224|256|384|512)\.new\s*\(',
       "SHA-2 hash (PyCryptodome)", "high", True),
    mk("HASH-SHA2-JAVA", "SHA",
       r'MessageDigest\.getInstance\(\s*"SHA-?(?:3-)?(?P<bits>224|256|384|512)"',
       "SHA-2/3 hash (Java MessageDigest)", "high", True),
    mk("HASH-SHA2-CLI", "SHA",
       r'\bsha(?:224|256|384|512)sum\b|openssl\s+dgst\s+-sha(?:1|224|256|384|512)\b',
       "SHA hash via CLI", "medium"),
    # SHA-1 / MD5 were already broken classically, even before quantum
    mk("HASH-WEAK", "SHA",
       r'\bhashlib\.(?:sha1|md5)\b|\b(?:SHA1|MD5)\.new\s*\(|MessageDigest\.getInstance\(\s*"(?:SHA-?1|MD5)"',
       "SHA-1 / MD5 (classically broken hash)", "high"),
]
