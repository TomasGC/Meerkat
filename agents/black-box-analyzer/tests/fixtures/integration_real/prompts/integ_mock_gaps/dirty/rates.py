import requests

RATES_URL = "https://rates.example.com/latest"


def eur_to_usd(amount):
    response = requests.get(RATES_URL, timeout=5)
    response.raise_for_status()
    return amount * response.json()["usd"]
