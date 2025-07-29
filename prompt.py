import base64
from openai import OpenAI
import os
from dotenv import load_dotenv
from atm_model import DiffSlip
import json

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def encode_image_bytes(image_bytes):
    return base64.b64encode(image_bytes).decode("utf-8")

def process_slip(image_bytes):
    base64_image = encode_image_bytes(image_bytes)
    prompt = """
You are given an image of two ATM slips placed side by side. Extract the following details for each slip separately:

1. ATM Number (usually appears before the branch name)
2. Branch Name
3. A list of Denominations and their corresponding END values (like ₹500.00 - END: 879)
4. Date and Time (if available) - extract both date and time separately

Respond ONLY in the following JSON format (no extra text):

===== Slip 1 =====
ATM Number: <value>
Branch: <value>
Date: <value>
Time: <value> (if available, otherwise null)
Denominations and END values:
₹<amount> - END: <value>
...

===== Slip 2 =====
ATM Number: <value>
Branch: <value>
Date: <value>
Time: <value> (if available, otherwise null)
Denominations and END values:
₹<amount> - END: <value>
...
"""
    response = client.responses.parse(
        model="gpt-4.1",
        text_format=DiffSlip,
        input=[
            {
                "role": "user",
                "content": [
                    { "type": "input_text", "text": prompt },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{base64_image}",
                    },
                ],
            }
        ],
    )
    output_text = response.output_text
    try:
        json_start = output_text.find('{')
        json_end = output_text.rfind('}') + 1
        json_str = output_text[json_start:json_end]
        data = json.loads(json_str)
        diffslip = DiffSlip.model_validate(data)
        return diffslip, output_text
    except Exception as e:
        raise ValueError(f"Could not parse JSON from LLM output: {e}\nOutput was:\n{output_text}")

if __name__ == "__main__":
    # For testing: process a local file and print result
    image_path = "slips/atm_slip_2.jpeg"
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    diffslip, raw_text = process_slip(image_bytes)
    print(diffslip)
    print(raw_text)