import requests
import os
from dotenv import load_dotenv

load_dotenv()

FMP_API_KEY = os.getenv("FMP_API_KEY")

symbol = "SPCX"  # or "AAPL" for testing

# Test Quote
url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={FMP_API_KEY}"
response = requests.get(url, timeout=10)

print("Status Code:", response.status_code)
print("Response:", response.json())
