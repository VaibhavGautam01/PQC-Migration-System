# Week 2 Day 1: scanner cross-check

**Check A** (finding matches real source line): 24 of 24.

**Check B** (crypto-looking lines with no finding): 166, for manual review.

| Project | File:line | Code | Review |
|---|---|---|---|
| Secure-Video-S | app.py:2 | `Streamlit dashboard for "A Secure Video Steganography Framework Using RSA` | |
| Secure-Video-S | app.py:6 | `1. Keys      - generate/load RSA keypair` | |
| Secure-Video-S | app.py:27 | `st.set_page_config(page_title="Video Steganography (RSA + XOR-LSB)", layout="wide", page_icon="🛡️")` | |
| Secure-Video-S | app.py:35 | `# encryption/secrecy-related elements only, so it stays meaningful instead of` | |
| Secure-Video-S | app.py:218 | `<h1>Secure Video Steganography — RSA + Randomized XOR-LSB</h1>` | |
| Secure-Video-S | app.py:219 | `<p>A secret message, encrypted with RSA and hidden inside the least-significant` | |
| Secure-Video-S | app.py:220 | `bits of frames chosen by a SHA-256-keyed selection — invisible to the eye,` | |
| Secure-Video-S | app.py:223 | `<span class="chip"><b>01</b> Textbook RSA (paper steps 1–8)</span>` | |
| Secure-Video-S | app.py:224 | `<span class="chip"><b>02</b> SHA-256 Frame Selection</span>` | |
| Secure-Video-S | app.py:236 | `# here would mean every user's RSA keys — including PRIVATE keys —` | |
| Secure-Video-S | app.py:249 | `st.subheader("RSA Keypair")` | |
| Secure-Video-S | app.py:252 | `"decrypt the message) generates this keypair — on their own machine. "` | |
| Secure-Video-S | app.py:254 | `"safe, it can only encrypt, never decrypt. The **private key never leaves "` | |
| Secure-Video-S | app.py:256 | `"person has their own, different keypair; a message encrypted for one "` | |
| Secure-Video-S | app.py:257 | `"person's public key can only be decrypted by that same person's private key."` | |
| Secure-Video-S | app.py:261 | `st.caption("⚠️ 1024-bit RSA is factorable with enough compute — fine for a demo, not for a real secret. Use 20` | |
| Secure-Video-S | app.py:262 | `if st.button("Generate new keypair"):` | |
| Secure-Video-S | app.py:268 | `st.success(f"Keypair generated ({key_size}-bit).")` | |
| Secure-Video-S | app.py:293 | `p = os.path.join(st.session_state.keys_dir, "public_key.key")` | |
| Secure-Video-S | app.py:308 | `p = os.path.join(st.session_state.keys_dir, "private_key.key")` | |
| Secure-Video-S | app.py:320 | `st.metric("Max message size for this key (single RSA block limit)", f"{cap} bytes")` | |
| Secure-Video-S | app.py:330 | `"This secret key is short. It's hashed with SHA-256 but there's no "` | |
| Secure-Video-S | app.py:350 | `with st.spinner("Selecting frames, encrypting, embedding (XOR-LSB)..."):` | |
| Secure-Video-S | app.py:358 | `f"Embedded {result.ciphertext_len_bytes}-byte ciphertext across "` | |
| Secure-Video-S | app.py:373 | `who receives it) and pull the ciphertext back out. If it` | |
| Secure-Video-S | app.py:382 | `return recovered == result.ciphertext` | |
| Secure-Video-S | app.py:441 | `# frames and extraction fails with a confusing RSA error.` | |
| Secure-Video-S | app.py:474 | `with st.spinner("Selecting frames, extracting bits, decrypting..."):` | |
| Secure-Video-S | app.py:481 | `st.error(f"Extraction/decryption failed: {e}")` | |
| Secure-Video-S | frame_selector.py:2 | `Frame selection via SHA-256 hash of a secret key.` | |
| Secure-Video-S | frame_selector.py:5 | `1. secret_hash = SHA256(secret_key)              (hex digest)` | |
| Secure-Video-S | frame_selector.py:20 | `import hashlib` | |
| Secure-Video-S | pipeline.py:6 | `2. Encrypt message with RSA -> cipher_text.` | |
| Secure-Video-S | pipeline.py:7 | `3. Compute selected frame indices from SHA256(sk), limit to 'max_frames'.` | |
| Secure-Video-S | pipeline.py:8 | `4. Slice cipher_text into N slices (N <= max_frames); embed one slice` | |
| Secure-Video-S | pipeline.py:15 | `3. Concatenates slices to reconstruct ciphertext.` | |
| Secure-Video-S | pipeline.py:16 | `4. Decrypts with the RSA private key to recover plaintext.` | |
| Secure-Video-S | pipeline.py:30 | `ciphertext_len_bytes: int` | |
| Secure-Video-S | pipeline.py:32 | `ciphertext: bytes = b""` | |
| Secure-Video-S | pipeline.py:60 | `ciphertext = rsa_crypto.encrypt_message(message, pub_key)` | |
| Secure-Video-S | pipeline.py:68 | `slices = slice_bytes(ciphertext, n_slices)` | |
| Secure-Video-S | pipeline.py:75 | `# address slices up to 65535 bytes. Not reachable with the RSA` | |
| Secure-Video-S | pipeline.py:76 | `# key sizes offered in the dashboard (max ~384-byte ciphertext),` | |
| Secure-Video-S | pipeline.py:81 | `f"65535-byte limit. Use a smaller RSA key or more embedding frames."` | |
| Secure-Video-S | pipeline.py:98 | `ciphertext_len_bytes=len(ciphertext),` | |
| Secure-Video-S | pipeline.py:100 | `ciphertext=ciphertext,` | |
| Secure-Video-S | pipeline.py:107 | `ciphertext bytes out of the frames -- no RSA private key needed.` | |
| Secure-Video-S | pipeline.py:111 | `receiver's private key at all (textbook RSA here is deterministic, so` | |
| Secure-Video-S | pipeline.py:112 | `the ciphertext bytes recovered should be byte-for-byte identical to the` | |
| Secure-Video-S | pipeline.py:138 | `"""Full retrieval pipeline. Returns decrypted plaintext message."""` | |
| Secure-Video-S | pipeline.py:139 | `ciphertext = extract_ciphertext(stego_frames, secret_key, max_frames=max_frames)` | |
| Secure-Video-S | pipeline.py:140 | `return rsa_crypto.decrypt_message(ciphertext, priv_key)` | |
| Secure-Video-S | rsa_crypto.py:2 | `RSA encryption/decryption module.` | |
| Secure-Video-S | rsa_crypto.py:4 | `Literal reimplementation of Section III-A of the paper ("Encryption and` | |
| Secure-Video-S | rsa_crypto.py:5 | `decryption of secret message") -- textbook RSA, exactly as the paper's` | |
| Secure-Video-S | rsa_crypto.py:11 | `3. phi(n) = (p-1) * (q-1), phi(n) < n` | |
| Secure-Video-S | rsa_crypto.py:12 | `4. take a number e, coprime with phi(n), 1 < e < phi(n)` | |
| Secure-Video-S | rsa_crypto.py:13 | `5. d = (k*phi(n) + 1) / e  for some integer k   [ i.e. d = e^-1 mod phi(n) ]` | |
| Secure-Video-S | rsa_crypto.py:14 | `6. d * e = 1 mod phi(n)` | |
| Secure-Video-S | rsa_crypto.py:20 | `RSA, not a PyCryptodome RSA object. No separate ".json key file" format;` | |
| Secure-Video-S | rsa_crypto.py:24 | `Because there's no padding scheme, a single RSA block can only carry a` | |
| Secure-Video-S | rsa_crypto.py:26 | `the RSA algorithm" the paper itself names as a key priority for future` | |
| Secure-Video-S | rsa_crypto.py:43 | `"""Generate an RSA keypair following the paper's steps 1-8 and save as single-line text."""` | |
| Secure-Video-S | rsa_crypto.py:54 | `if number.GCD(e, phi) == 1:` | |
| Secure-Video-S | rsa_crypto.py:58 | `priv_path = os.path.join(out_dir, "private_key.key")` | |
| Secure-Video-S | rsa_crypto.py:59 | `pub_path = os.path.join(out_dir, "public_key.key")` | |
| Secure-Video-S | rsa_crypto.py:112 | `Max plaintext bytes a single textbook-RSA block can hold for this key` | |
| Secure-Video-S | rsa_crypto.py:114 | `a 4-byte CRC32 integrity checksum -- see the note on decrypt_message).` | |
| Secure-Video-S | rsa_crypto.py:115 | `This IS the "block size limitation of RSA" the paper flags as future` | |
| Secure-Video-S | rsa_crypto.py:123 | `def encrypt_message(message: str, pub_key: dict) -> bytes:` | |
| Secure-Video-S | rsa_crypto.py:124 | `"""Encrypt message text with the receiver's RSA public key (e, n)."""` | |
| Secure-Video-S | rsa_crypto.py:130 | `f"Message is {len(data)} bytes but this RSA key's single block "` | |
| Secure-Video-S | rsa_crypto.py:131 | `f"can only hold {cap} bytes (RSA block-size limitation noted in "` | |
| Secure-Video-S | rsa_crypto.py:155 | `def decrypt_message(ciphertext: bytes, priv_key: dict) -> str:` | |
| Secure-Video-S | rsa_crypto.py:157 | `Decrypt ciphertext with the receiver's RSA private key (d, n).` | |
| Secure-Video-S | rsa_crypto.py:159 | `Verifies a 4-byte CRC32 checksum embedded at encrypt time before` | |
| Secure-Video-S | rsa_crypto.py:169 | `c = int.from_bytes(ciphertext, "big")` | |
| Final-Year-pro | app.py:12 | `3. Compare All Techniques -- run LSB, R-Channel+RSA, and RSA+LSB side by side` | |
| Final-Year-pro | app.py:52 | `"R-Channel + RSA": "#ef4444",` | |
| Final-Year-pro | app.py:53 | `"RSA + LSB": "#3b82f6",` | |
| Final-Year-pro | app.py:160 | `TECHNIQUES = ["LSB", "R-Channel + small RSA (paper's method)", "RSA (secure) + LSB"]` | |
| Final-Year-pro | app.py:183 | `Channel encoding, and RSA encryption — implemented from` | |
| Final-Year-pro | app.py:233 | `f"Small RSA key generated for this session: public=(e={pub[0]}, "` | |
| Final-Year-pro | app.py:238 | `else:  # RSA (secure) + LSB` | |
| Final-Year-pro | app.py:243 | `"Secure RSA key pair generated for this session and stored "` | |
| Final-Year-pro | app.py:287 | `"Uses the small RSA key generated in the **Hide** tab during this "` | |
| Final-Year-pro | app.py:290 | `elif technique2.startswith("RSA (secure)"):` | |
| Final-Year-pro | app.py:292 | `"Uses the secure RSA key generated in the **Hide** tab during this "` | |
| Final-Year-pro | app.py:309 | `"No small RSA key found for this session. Embed a "` | |
| Final-Year-pro | app.py:319 | `"No RSA key found for this session. Embed a message "` | |
| Final-Year-pro | app.py:341 | `"Message for LSB & RSA+LSB",` | |
| Final-Year-pro | app.py:370 | `with st.spinner("Running R-Channel + small RSA..."):` | |
| Final-Year-pro | app.py:378 | `results["R-Channel + RSA"] = (stego, mse, calculate_psnr(mse), out == msg_small)` | |
| Final-Year-pro | app.py:382 | `with st.spinner("Running RSA (secure) + LSB..."):` | |
| Final-Year-pro | app.py:390 | `results["RSA + LSB"] = (stego, mse, calculate_psnr(mse), out == msg_main)` | |
| Final-Year-pro | app.py:392 | `st.warning(f"RSA + LSB technique skipped: {e}")` | |
| Final-Year-pro | app.py:527 | `if "R-Channel + RSA" in results:` | |
| Final-Year-pro | app.py:528 | `fig2 = plot_channel_effect(cover_img, results["R-Channel + RSA"][0], os.path.join(TMP_DIR, "effect_rsa.png"))` | |
| Final-Year-pro | app.py:529 | `plot_col2.image(fig2, caption="Effect of RSA Technique on Image", use_container_width=True)` | |
| Final-Year-pro | app.py:531 | `"LSB points hug the diagonal (value changes by at most 1); R-Channel + RSA "` | |
| Final-Year-pro | app.py:532 | `"points scatter further away, since the whole byte is replaced with a cipher "` | |
| Final-Year-pro | app.py:540 | `<span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:{TECH_COLORS['R-Channel + ` | |
| Final-Year-pro | app.py:541 | `<span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:{TECH_COLORS['RSA + LSB']}` | |
| Final-Year-pro | lsb_stego.py:10 | `itself (a real risk once we hide arbitrary bytes such as RSA` | |
| Final-Year-pro | lsb_stego.py:11 | `ciphertext hex), silently truncating the extracted message. The` | |
| Final-Year-pro | main.py:54 | `"""Prints the full 8-10 parameter comparison before and after embedding/encryption."""` | |
| Final-Year-pro | main.py:92 | `print_comparison_table(f"[{name}] R-Channel + RSA", original_img, stego_img)` | |
| Final-Year-pro | main.py:107 | `print(f"  [{name}] RSA+LSB  Match: {extracted == secret_message}   "` | |
| Final-Year-pro | main.py:110 | `print_comparison_table(f"[{name}] RSA + LSB Technique", original_img, stego_img)` | |
| Final-Year-pro | main.py:160 | `print_table("TABLE I(b) -- R-CHANNEL + SMALL RSA (paper's original method)", r_channel_rows)` | |
| Final-Year-pro | main.py:161 | `print_table("TABLE II -- PERFORMANCE ANALYSIS ON RSA (SECURE) + LSB TECHNIQUE", rsa_lsb_rows)` | |
| Final-Year-pro | main.py:166 | `print("  outputs/effect_rsa.png  -- Effect of RSA Technique on Image")` | |
| Final-Year-pro | metrics.py:2 | `Image quality and statistical metrics used to evaluate steganography and encryption` | |
| Final-Year-pro | metrics.py:106 | `Computes comparative parameters between original and encoded/encrypted images.` | |
| Final-Year-pro | metrics.py:131 | `"Status": "High Fidelity" if psnr_val > 40 else "Distorted / Encrypted",` | |
| Final-Year-pro | pixel_analysis.py:3 | `"Effect of LSB Technique on Image" and "Effect of RSA Technique on Image" --` | |
| Final-Year-pro | pixel_analysis.py:8 | `bit), so points hug the y=x diagonal almost exactly. The R-Channel + RSA` | |
| Final-Year-pro | pixel_analysis.py:9 | `technique replaces the entire Red-channel byte with a cipher value, so its` | |
| Final-Year-pro | pixel_analysis.py:60 | `Red-channel value, for the R-Channel + RSA technique. Points scatter` | |
| Final-Year-pro | pixel_analysis.py:62 | `cipher value rather than just its least significant bit.` | |
| Final-Year-pro | pixel_analysis.py:86 | `ax.set_title("Effect of RSA Technique on Image")` | |
| Final-Year-pro | r_channel_stego.py:2 | `R-Color Channel + RSA steganography — Section III.B.1 of the paper` | |
| Final-Year-pro | r_channel_stego.py:6 | `Red-channel value of each pixel with the RSA-encrypted value of one` | |
| Final-Year-pro | r_channel_stego.py:8 | `0-255, this requires an RSA modulus n < 256 — this is a real` | |
| Final-Year-pro | r_channel_stego.py:15 | `pixel (i+1)  -> R channel stores encrypt(ord(message[i]))` | |
| Final-Year-pro | r_channel_stego.py:21 | `from sympy import isprime` | |
| Final-Year-pro | r_channel_stego.py:23 | `from rsa_utils import encrypt_int, decrypt_int` | |
| Final-Year-pro | r_channel_stego.py:26 | `# Red channel after encryption. Below this, common text would randomly` | |
| Final-Year-pro | r_channel_stego.py:42 | `primes = [p for p in range(2, 40) if isprime(p)]` | |
| Final-Year-pro | r_channel_stego.py:54 | `e_candidates = [c for c in range(3, phi) if isprime(c) and phi % c != 0]` | |
| Final-Year-pro | r_channel_stego.py:74 | `f"modulus n={n}. This is the small-key limitation of this "` | |
| Final-Year-pro | r_channel_stego.py:87 | `cipher_vals = [encrypt_int(ord(ch), pub) for ch in secret_text]` | |
| Final-Year-pro | r_channel_stego.py:88 | `flat[1:len(secret_text) + 1, 0] = cipher_vals` | |
| Final-Year-pro | r_channel_stego.py:106 | `cipher_vals = flat[1:length + 1, 0]` | |
| Final-Year-pro | r_channel_stego.py:107 | `return ''.join(chr(decrypt_int(int(c), priv)) for c in cipher_vals)` | |
| Final-Year-pro | rsa_lsb_stego.py:2 | `Improved combined technique: real secure RSA (large modulus) + LSB` | |
| Final-Year-pro | rsa_lsb_stego.py:3 | `embedding of the ciphertext bytes. This fixes the small-keyspace` | |
| Final-Year-pro | rsa_lsb_stego.py:5 | `while keeping the same "encrypt, then hide" idea from Section III.B.` | |
| Final-Year-pro | rsa_lsb_stego.py:7 | `Each RSA-encrypted character is serialized as a fixed-width hex string` | |
| Final-Year-pro | rsa_lsb_stego.py:11 | `from rsa_utils import encrypt_text, decrypt_text` | |
| Final-Year-pro | rsa_lsb_stego.py:20 | `"""Encrypt secret_text with RSA, then LSB-embed the ciphertext."""` | |
| Final-Year-pro | rsa_lsb_stego.py:22 | `cipher_ints = encrypt_text(secret_text, pub)` | |
| Final-Year-pro | rsa_lsb_stego.py:23 | `hex_str = ''.join(format(c, f'0{hex_width}x') for c in cipher_ints)` | |
| Final-Year-pro | rsa_lsb_stego.py:29 | `"""Extract the hidden hex ciphertext via LSB, then RSA-decrypt it."""` | |
| Final-Year-pro | rsa_lsb_stego.py:34 | `"Extracted data is not a whole number of ciphertext blocks -- "` | |
| Final-Year-pro | rsa_lsb_stego.py:38 | `cipher_ints = [` | |
| Final-Year-pro | rsa_lsb_stego.py:42 | `return decrypt_text(cipher_ints, priv)` | |
| Final-Year-pro | rsa_utils.py:2 | `RSA key generation, encryption and decryption — Section III.B of the` | |
| Final-Year-pro | rsa_utils.py:6 | `3. phi(n) = (x-1)(y-1)` | |
| Final-Year-pro | rsa_utils.py:7 | `4. Choose e coprime to phi(n)` | |
| Final-Year-pro | rsa_utils.py:8 | `5. d = e^-1 mod phi(n)` | |
| Final-Year-pro | rsa_utils.py:11 | `8. Encrypt: C = M^e mod n` | |
| Final-Year-pro | rsa_utils.py:12 | `9. Decrypt: M = C^d mod n` | |
| Final-Year-pro | rsa_utils.py:26 | `"""Generate a (public, private) RSA key pair. n has ~2*bits bits."""` | |
| Final-Year-pro | rsa_utils.py:36 | `while phi % e == 0:` | |
| Final-Year-pro | rsa_utils.py:43 | `def encrypt_int(m, pub):` | |
| Final-Year-pro | rsa_utils.py:48 | `def decrypt_int(c, priv):` | |
| Final-Year-pro | rsa_utils.py:53 | `def encrypt_text(text, pub):` | |
| Final-Year-pro | rsa_utils.py:54 | `"""Encrypt text character-by-character -> list of cipher integers."""` | |
| Final-Year-pro | rsa_utils.py:55 | `return [encrypt_int(ord(ch), pub) for ch in text]` | |
| Final-Year-pro | rsa_utils.py:58 | `def decrypt_text(cipher_list, priv):` | |
| Final-Year-pro | rsa_utils.py:59 | `"""Decrypt a list of cipher integers back into text.` | |
| Final-Year-pro | rsa_utils.py:68 | `for c in cipher_list:` | |
| Final-Year-pro | rsa_utils.py:69 | `m = decrypt_int(c, priv)` | |
| Final-Year-pro | rsa_utils.py:74 | `"Decryption produced an invalid character -- this almost "` | |
| Final-Year-pro | rsa_utils.py:76 | `"ciphertext) was used."` | |
