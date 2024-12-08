from pymongo import MongoClient
from pprint import pprint

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client['ros2_rag']
collection = db['documentation']

# Find the specific document
doc = collection.find_one({
    "source.url": "https://github.com/ros2/ros2/"
})

if doc:
    print("\nDocument found!")
    print("\nDocument structure:")
    print("------------------")
    print(f"ID: {doc['id']}")
    print(f"Type: {doc['type']}")
    print(f"Subdomain: {doc['subdomain']}")
    print("\nSource info:")
    print(f"URL: {doc['source']['url']}")
    print(f"Repository: {doc['source']['repo']}")
    print(f"Branch: {doc['source']['branch']}")
    
    print("\nContent preview (first 200 chars):")
    print("------------------")
    print(doc['content']['body'][:900] + "...")
else:
    print("Document not found!") 