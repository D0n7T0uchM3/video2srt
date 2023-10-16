import requests
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

rvc_api_url = "http://localhost:7865/run/infer_set"

payload = {
  "data": [
        "kuplinov.pth",
        0.33,
        0.33
        ]
}

response = requests.post(rvc_api_url, json=payload).json()
data = response["data"]

logging.info(data)