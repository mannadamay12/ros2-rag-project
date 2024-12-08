# extract_to_files.py
from pymongo import MongoClient
import os
import json
from typing import Dict, Any

def export_mongodb_to_files(output_dir: str = "exported_docs"):
   # Connect to MongoDB
   client = MongoClient('mongodb://localhost:27017/')
   db = client['ros2_rag']
   collection = db['documentation']

   # Create output directory
   os.makedirs(output_dir, exist_ok=True)

   # Export documents by subdomain
   for subdomain in collection.distinct('subdomain'):
       subdomain_dir = os.path.join(output_dir, subdomain)
       os.makedirs(subdomain_dir, exist_ok=True)

       for doc in collection.find({'subdomain': subdomain}):
           # Create filename from title or URL
           filename = doc['content'].get('title', '').replace(' ', '_')
           if not filename:
               filename = doc['source']['url'].split('/')[-1]
           
           filepath = os.path.join(subdomain_dir, f"{filename}.txt")

           with open(filepath, 'w', encoding='utf-8') as f:
               # Write metadata
               f.write(f"Title: {doc['content'].get('title', '')}\n")
               f.write(f"URL: {doc['source']['url']}\n")
               f.write(f"Section: {doc['metadata'].get('parent_section', '')}\n")
               f.write("-" * 80 + "\n\n")

               # Write main content
               f.write(doc['content'].get('body', ''))

               # Write code blocks
               if doc['content'].get('code_snippets'):
                   f.write("\n\nCode Examples:\n")
                   for code in doc['content']['code_snippets']:
                       f.write(f"\nLanguage: {code['language']}\n")
                       f.write(code['code'] + "\n")

if __name__ == "__main__":
   export_mongodb_to_files()