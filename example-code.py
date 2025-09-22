# Example of a security error: hardcoded password
def connect_to_db():
    username = "admin"
    password = "SuperSecret123"  # SECURITY FLAW: Do not hardcode credentials!
    print(f"Connecting to database with user {username} and password {password}")

if __name__ == "__main__":
    connect_to_db()