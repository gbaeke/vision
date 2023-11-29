from openai import OpenAI
import dotenv
import base64

# load env vars including OPENAI_API_KEY
dotenv.load_dotenv()

client = OpenAI()

# open image invoice.png and convert to base64
with open("invoice.png", "rb") as image_file:
    image = base64.b64encode(image_file.read()).decode("utf-8")


response = client.chat.completions.create(
  model="gpt-4-vision-preview",
  messages=[
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "Extract only the invoice items and the quantities. Present them in a JSON array with fields item and quantity."},
        {
          "type": "image_url",
          "image_url": {
            "url": f"data:image/png;base64,{image}",
          },
        },
      ],
    }
  ],
  max_tokens=500,
)

print(response.choices[0].message.content)
