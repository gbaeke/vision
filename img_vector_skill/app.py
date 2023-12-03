from typing import List
from fastapi import FastAPI
from pydantic import BaseModel
import logging
import base64
import dotenv
from azure.storage.blob import BlobServiceClient
import os
import requests
from openai import OpenAI

# load environment variables
dotenv.load_dotenv("../.env")

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)

class RecordData(BaseModel):
    url: str

class Record(BaseModel):
    recordId: str
    data: RecordData

class RequestBody(BaseModel):
    values: List[Record]

app = FastAPI()

client = OpenAI()

def get_image_description(image_base64: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Provide a short description of the image below."},
                    {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}",
                    },
                    },
                ],
                }
            ],
            max_tokens=500,
        )

        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

def download_from_azure_storage(url):
        # extract container name and filename from the url
        container_name = url.split('/')[3]
        blob_name = url.split('/')[4]

        logger.info(f"container name: {container_name}")
        logger.info(f"blob name: {blob_name}")

        # Create a blob service client
        blob_service_client = BlobServiceClient.from_connection_string(os.getenv("STORAGE_CONNNECTION_STRING"))

        # Access the container and blob
        try:
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

            # Download the blob
            blob_data = blob_client.download_blob().readall()
            logger.info(f"blob data: {blob_data[:10]}...")
            return blob_data
        except Exception as e:
            logger.error(f"Error: {e}")
            return None

# vectorize with Azure Cognitive Services
def get_image_data(blob_url: str) -> (list, str):
    # Define the URL, headers, and data
    url = "https://geba-ai.cognitiveservices.azure.com/computervision/retrieval:vectorizeImage?api-version=2023-02-01-preview&modelVersion=latest"
    headers = {
        "Content-Type": "application/octet-stream",
        "Ocp-Apim-Subscription-Key": os.getenv("AZURE_AI_KEY")
    }

    # read file from azure blob; return None if that failed
    image_data = download_from_azure_storage(blob_url)
    if not image_data:
        return None, None

    # vectorize the image based on raw image data
    logger.info(f"Getting vector for {blob_url}...")
    try:
        response = requests.post(url, headers=headers, data=image_data)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Error: {e}")
        return None, None
    
    # base64 encode image_data
    image_base64 = base64.b64encode(image_data).decode("utf-8")

    # get image description
    description = get_image_description(image_base64)

    # return the vector
    return response.json().get('vector'), description

@app.post("/vectorize")
async def vectorize(request_body: RequestBody):
    # json response
    json_response = {
        "values": []
    }

    # skill can receive multiple records at a time
    for record in request_body.values:
        url = record.data.url
        logger.info(f"input url: {url}")

        # getting vector for image in url
        logger.info("getting vector...")
        vector, description = get_image_data(url)

        if vector and description:
            # add json to json_response values
            json_response["values"].append({
                "recordId": record.recordId,
                "data": {
                    "embedding": vector,
                    "description": description,
                },
                "errors": []
            })
        else:
            logger.info("vector is empty")
            
            # add json with error to json_response values
            json_response["values"].append({
                "recordId": record.recordId,
                "data": {},
                "errors": [
                    {
                        "message": "Error getting vector or description"
                    }
                ]
            })

    return json_response    
    

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=60)