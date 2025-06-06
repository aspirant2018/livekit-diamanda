import os
import requests
from dotenv import load_dotenv

def get_access_token(tenant_id,client_id,client_secret):
    
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    data = {
        "client_id": client_id,
        "scope": "https://graph.microsoft.com/.default",
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json()



load_dotenv()


tenant_id = os.getenv("tenant_id")
client_id = os.getenv("client_id")
client_secret = os.getenv("client_secret")

access_token = get_access_token(tenant_id,client_id,client_secret).get('access_token')

def get_user_presence(user_id: str) -> dict:
    """
    Check the presence of a user in Microsoft Graph.
    
    Args:
        user_id (str): The user's email or ID in Azure AD.
    
    Returns:
        dict: A dictionary with 'available' (bool) and 'raw' (full JSON response).
    """

    
    url = f"https://graph.microsoft.com/beta/users/{user_id}/presence"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        availability = data.get("availability", "").lower()
        is_available = availability in ["available", "availableIdle"]
        return {"available": is_available, "raw": data}
    elif response.status_code == 404:
        return {"available": False, "raw": {"error": "User not found"}}
    else:
        response.raise_for_status()


