import requests
from configuration import SUBSCRIPTION_URL, VERIFY_SSL


def delete_subscription(token_mgr, subscription_id):
    url = f"{SUBSCRIPTION_URL}/{subscription_id}"

    headers = {
        "Authorization": f"Bearer {token_mgr.get_access_token()}",
        "Content-Type": "application/json"
    }

    response = requests.delete(url, headers=headers, verify=VERIFY_SSL)
    response.raise_for_status()
    print("🗑️ Subscription deleted")
