import requests
from configuration import SUBSCRIPTION_URL, VERIFY_SSL


def renew_subscription(token_mgr, subscription_id):
    url = f"{SUBSCRIPTION_URL}/{subscription_id}/renewals"

    headers = {
        "Authorization": f"Bearer {token_mgr.get_access_token()}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json={}, verify=VERIFY_SSL)
    response.raise_for_status()
