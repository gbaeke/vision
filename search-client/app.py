import dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.storage.blob import BlobServiceClient
import requests
import json
import streamlit as st
import logging
from openai import OpenAI
import os

# set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv.load_dotenv("../.env")

# helper functions
def get_image_vector(image_path: str) -> list:
    # Define the URL, headers, and data
    url = "https://geba-ai.cognitiveservices.azure.com//computervision/retrieval:vectorizeImage?api-version=2023-02-01-preview&modelVersion=latest"
    headers = {
        "Content-Type": "application/octet-stream",
        "Ocp-Apim-Subscription-Key": os.getenv("AZURE_AI_KEY")
    }

    with open(image_path, 'rb') as image_file:
        # Read the contents of the image file
        image_data = image_file.read()

    logger.info(f"Getting vector for {image_path}...")

    # Send a POST request
    response = requests.post(url, headers=headers, data=image_data)

    # return the vector
    return response.json().get('vector')

def get_text_vector(text: str):
    logger.info(f"Getting vector for {text}...")
    oai_client = OpenAI()
    embedding = oai_client.embeddings.create(input=[text], model="text-embedding-ada-002")
    return embedding.data[0].embedding

def download_from_azure_storage(url):
        # extract container name and filename from the url
        container_name = url.split('/')[3]
        blob_name = url.split('/')[4]

        # Create a blob service client
        blob_service_client = BlobServiceClient.from_connection_string(os.getenv("STORAGE_CONNNECTION_STRING"))

        # Access the container and blob
        try:
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

            # Download the blob
            blob_data = blob_client.download_blob().readall()
            return blob_data
        except Exception as e:
            logger.error(f"Error: {e}")
            return None

st.title("Search Client")

# input text control
text_input = st.text_input("Enter text to search for:")

# button to start the search
if st.button("Search"):
    # get the vector for the input text
    text_vector = get_text_vector(text_input)

    
    # create a search client
    endpoint = "https://acs-geba.search.windows.net"
    index_name = "images"
    credential = AzureKeyCredential(os.getenv("AZURE_AI_SEARCH_KEY"))
    client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)

    vector_query = VectorizedQuery(vector=text_vector, k_nearest_neighbors=2, fields="textVector", exhaustive=True)


    # search the index
    results = client.search(
        vector_queries=[vector_query],
        select=["name", "description", "url"]
    )

    # display the results
    for result in results:
        # download the image
        image_data = download_from_azure_storage(result["url"])

        # display the image
        st.image(image_data, use_column_width=True)

        st.write(result)

        
