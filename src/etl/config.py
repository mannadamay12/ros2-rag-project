from clearml import Task
from pymongo import MongoClient
import os
# from dotenv import load_dotenv

# load_dotenv()

def init_clearml():
    task = Task.init(project_name="ROS2-RAG", task_name="ETL-Pipeline")
    return task

def get_mongo_client():
    client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
    db = client['ros2_rag']
    return db