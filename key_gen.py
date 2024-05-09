from cryptography.fernet import Fernet

key = Fernet.generate_key()

# generate key
with open('highscore_key', 'wb') as high_key:
    high_key.write(key)

# load key
with open('highscore_key', 'rb') as high_key:
    key = high_key.read()

# encrypt file
f = Fernet(key)

with open('highscore.txt', 'rb') as original_file:
    original = original_file.read()

encrypted = f.encrypt(original)

with open('highscore.txt', 'wb') as encrypted_file:
    encrypted_file.write(encrypted)
