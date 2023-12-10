import urllib.request
import json
import os, sys
import ssl
import dotenv
from azure.storage.blob import BlobServiceClient
from PIL import Image
import io

dotenv.load_dotenv("../.env")

# code was modified from Microsoft provided sample code in Endpoint consume section (portal)

def allowSelfSignedHttps(allowed):
    # bypass the server certificate verification on client side
    if allowed and not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None):
        ssl._create_default_https_context = ssl._create_unverified_context

allowSelfSignedHttps(True) # this line is needed if you use self-signed certificate in your scoring service.


def download_from_azure_storage(url):
    
    try:
        # extract container name and filename from the url
        container_name = url.split('/')[3]
        blob_name = url.split('/')[4]

        # Create a blob service client
        blob_service_client = BlobServiceClient.from_connection_string(os.getenv("STORAGE_CONNNECTION_STRING"))

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        # Download the blob
        blob_data = blob_client.download_blob().readall()
        return blob_data
    except Exception as e:
        return None

# check for parameters on command line
if len(sys.argv) > 1:
    prompt = sys.argv[1]
else:
    prompt = input("Enter a prompt: ")

data = {"description": prompt}

body = str.encode(json.dumps(data))

url = 'https://ml-geba-img.westeurope.inference.ml.azure.com/score'
# Replace this with the primary/secondary key or AMLToken for the endpoint
api_key = os.getenv("PROMPT_FLOW_KEY")
if not api_key:
    raise Exception("A key should be provided to invoke the endpoint")

# The azureml-model-deployment header will force the request to go to a specific deployment.
# Remove this header to have the request observe the endpoint traffic rules
headers = {'Content-Type':'application/json', 'Authorization':('Bearer '+ api_key), 'azureml-model-deployment': 'ml-geba-img-1' }

req = urllib.request.Request(url, body, headers)

try:
    response = urllib.request.urlopen(req)

    result = response.read()

    # convert result to json and extract url
    result = json.loads(result)
    result = result.get('url')

    # retrieve image from Azure Storage
    image = download_from_azure_storage(result)

    if image:
        # display image
        if len(sys.argv) > 1:
            # don't open image if running from command line
            print(result)
        else:
            image = Image.open(io.BytesIO(image))
            image.show()
            
    else:
        print("Image not found")

except urllib.error.HTTPError as error:
    print("The request failed with status code: " + str(error.code))

    # Print the headers - they include the requert ID and the timestamp, which are useful for debugging the failure
    print(error.info())
    print(error.read().decode("utf8", 'ignore'))