from auth import hash_password
from database import create_user, get_user_by_email, initialize_db

DEMO_USERS = [
    ("Admin User", "admin@college.edu", "admin123", "admin"),
    ("Dr. Faculty", "faculty@college.edu", "faculty123", "faculty"),
    ("Student One", "student@college.edu", "student123", "student"),
]


def seed():
    initialize_db()
    for name, email, password, role in DEMO_USERS:
        if get_user_by_email(email) is None:
            create_user(name, email, hash_password(password), role)
            print(f"Created {role}: {email} / {password}")
        else:
            print(f"Already exists: {email}")


if __name__ == "__main__":
    seed()
