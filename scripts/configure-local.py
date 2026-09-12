"""Interactive local setup. Secret inputs are hidden and written only to ignored .env."""
import getpass
import secrets
from pathlib import Path
from dotenv import set_key


def main():
    root = Path(__file__).resolve().parents[1]
    target = root / '.env'
    print('Configure local NEXUS. Existing database accounts are not overwritten.')
    email = input('Initial administrator email: ').strip().lower()
    if '@' not in email:
        raise SystemExit('Enter a valid administrator email.')
    password = getpass.getpass('Initial administrator password (at least 10 characters): ')
    confirm = getpass.getpass('Confirm password: ')
    if password != confirm or len(password) < 10:
        raise SystemExit('Passwords must match and contain at least 10 characters.')
    if not target.exists():
        target.touch()
    for key, value in {
        'NEXUS_ADMIN_EMAIL': email,
        'NEXUS_ADMIN_PASSWORD': password,
    }.items():
        set_key(str(target), key, value)
    # Preserve an existing signing key and database configuration on repeat setup.
    from dotenv import dotenv_values
    existing = dotenv_values(target)
    for key, value in {
        'JWT_SECRET': secrets.token_urlsafe(48),
        'MONGODB_URI': 'mongodb://127.0.0.1:27017/?replicaSet=nexus-rs',
        'MONGODB_DATABASE': 'nexus',
        'EMAIL_PROVIDER': 'demo',
    }.items():
        if not existing.get(key):
            set_key(str(target), key, value)
    print('Local configuration saved. No credentials were printed. Start NEXUS normally.')


if __name__ == '__main__':
    main()
