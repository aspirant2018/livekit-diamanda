import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_user_presence(user_id: str) -> dict:
    """
    Check the presence of a user in Microsoft Graph.
    
    Args:
        user_id (str): The user's email or ID in Azure AD.
    
    Returns:
        dict: A dictionary with 'available' (bool) and 'raw' (full JSON response).
    """
    access_token = os.getenv("DIAMY_GRAPH_ACCESS_TOKEN")
    if not access_token:
        raise ValueError("Missing ACCESS_TOKEN in environment variables.")
    
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
