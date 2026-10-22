from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KEY = bytes.fromhex("00112233445566778899aabbccddeeff")


def encrypt(data: bytes) -> bytes:
    encryptor = Cipher(algorithms.AES(KEY), modes.ECB()).encryptor()
    return encryptor.update(data) + encryptor.finalize()
