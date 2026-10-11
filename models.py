from flask_login import UserMixin

class User(UserMixin):
    """Small Flask-Login user object; database access stays in route/service code."""
    def __init__(self, row):
        self.id = row["id"]
        self.name = row["name"]
        self.email = row["email"]
        self.password_hash = row["password_hash"]
        self.role = row["role"]
        self.phone = row.get("phone")
        self.birthday = row.get("birthday")
