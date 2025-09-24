import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_db_credentials(vault_url: str, username_secret_name: str, password_secret_name: str):
    """
    Retrieve database credentials securely from Azure Key Vault using Managed Identity.
    """
    credential = DefaultAzureCredential()
    secret_client = SecretClient(vault_url=vault_url, credential=credential)

    username = secret_client.get_secret(username_secret_name).value
    password = secret_client.get_secret(password_secret_name).value
    return username, password

def connect_to_db(username: str, password: str):
    """
    Simulate connecting to a database using provided credentials.
    """
    # Replace this print statement with actual database connection logic.
    print(f"Connecting to database with user {username}")

if __name__ == "__main__":
    # These environment variables should be set in your deployment environment.
    VAULT_URL = os.environ.get("AZURE_KEY_VAULT_URL")
    USERNAME_SECRET_NAME = os.environ.get("DB_USERNAME_SECRET_NAME")
    PASSWORD_SECRET_NAME = os.environ.get("DB_PASSWORD_SECRET_NAME")

    if not all([VAULT_URL, USERNAME_SECRET_NAME, PASSWORD_SECRET_NAME]):
        raise EnvironmentError("Required environment variables are not set.")

    username, password = get_db_credentials(VAULT_URL, USERNAME_SECRET_NAME, PASSWORD_SECRET_NAME)
    connect_to_db(username, password)

# Guidance:
# - Store secrets (such as database usernames and passwords) in Azure Key Vault.
# - Use Azure Managed Identity for secure, passwordless authentication to Key Vault.
# - Rotate secrets in Key Vault regularly and ensure your application retrieves secrets dynamically at runtime.
# - Never hardcode credentials in source code or configuration files.