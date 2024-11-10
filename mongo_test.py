from pymongo import MongoClient

# Connect to MongoDB server (assuming it's running on localhost and port 27017)
client = MongoClient("mongodb://localhost:27017/")

# Access a test database
db = client.test_database

# Access a test collection within the test database
collection = db.test_collection

# Insert a sample document
sample_document = {"name": "RAG Test", "description": "Testing MongoDB connection"}
collection.insert_one(sample_document)

# Retrieve and print the document
retrieved_document = collection.find_one({"name": "RAG Test"})
print("Retrieved Document:", retrieved_document)

# Clean up (optional): delete the test document
collection.delete_one({"name": "RAG Test"})

# Close the connection
client.close()
