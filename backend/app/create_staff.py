"""Create a staff login. Run from the backend folder:  python -m app.create_staff"""
import getpass
import sys

from app.core.security import hash_password
from app.db.session import database_sessions
from app.models import User


def main():
    email = input("Email: ").strip().lower()
    name = input("Full name: ").strip()
    role = input("Role (admin or operator) [operator]: ").strip() or "operator"
    password = getpass.getpass("Password (at least 10 characters): ")
    if role not in ("admin", "operator") or len(password) < 10 or not email or not name:
        sys.exit("Invalid input. Nothing was created.")
    with database_sessions()() as db:
        if db.query(User).filter_by(email=email).first():
            sys.exit("That email already exists.")
        db.add(User(full_name=name, email=email, password_hash=hash_password(password), role=role))
        db.commit()
    print(f"Created {role} {email}")


if __name__ == "__main__":
    main()
