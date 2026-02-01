import os
from dotenv import load_dotenv

load_dotenv()

NSP_SERVER = os.getenv("NSP_SERVER", "192.168.42.7")

USERNAME = os.getenv("NSP_USERNAME")
PASSWORD = os.getenv("NSP_PASSWORD")
KAFKA_KEYSTORE_PASSWORD = os.getenv("KAFKA_KEYSTORE_PASSWORD")

AUTH_URL = f"https://{NSP_SERVER}:8443/rest-gateway/rest/api/v1/auth/token"
SUBSCRIPTION_URL = f"https://{NSP_SERVER}:8443/nbi-notification/api/v1/notifications/subscriptions"
REVOKE_URL = f"https://{NSP_SERVER}:8443/rest-gateway/rest/api/v1/auth/revocation"

VERIFY_SSL = False
