# convert "ObjectId" to string
from dotenv import load_dotenv
from datetime import datetime, timedelta
import io
import json  # json
from bson import ObjectId  # Import ObjectId from bson library
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from pymongo import MongoClient  # mongoDB driver
from flask_pymongo import PyMongo

from flask_cors import cross_origin
import httpx
import requests
import jwt
import os
import asyncio
# from flask_jwt import JWT, jwt_required, current_identity

# from openpyxl import load_workbook

app = Flask(__name__)


CORS(app)  # Allow CORS for all domains on all routes

# ALLOWED_EXTENSIONS = {'xlsx', 'csv'}

# MongoDB connection configuration
MONGO_URI = "mongodb+srv://peelaxv:peelaxv123@cluster0.djocv6a.mongodb.net/Feedback?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)  # mongoDB URI
db = client['Feedback']  # database name
collection = db['student_feedbacks']  # collection name

load_dotenv()  # This loads the variables from .env into the environment


# test connection
@app.route("/", methods=["GET"])
def test_connection():
    return "hello this is flask server!"


@app.route("/flask-seed", methods=["POST"])
def flask_seed():
    try:
        client_data = request.json

        collection.insert_many(client_data)

        return jsonify({"success": True, "message": "Seeding Success"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/flask-delete", methods=["GET"])
def flask_delete():
    try:
        result = collection.delete_many({})
        return jsonify({"success": True, "message": f"Deleted {result.deleted_count} documents from the collection."})
    except Exception as e:
        # Internal Server Error
        return jsonify({"success": False, "error": str(e)}), 500


# retrieve course by courseNo
@app.route('/course', methods=['GET'])
def get_course():
    try:
        course_no = int(request.args.get("courseNo"))

        result = list(collection.find({"courseNo": course_no}, {"_id": 0}))

        if result:
            return jsonify(result)
        else:
            return jsonify({"message": "Course not found"}), 404
    except Exception as e:
        return jsonify({"error": "An error occurred can not retrive specific course", "details": str(e)}), 500


# retrieve courses (got array of course object)
@app.route('/courses', methods=['GET'])
def get_courses():

    # Retrieve all courses from MongoDB
    courses = list(collection.find({}, {"_id": 0}))

    return jsonify(courses)


# retrive course by cmuAccount and courseNo
# sorted
@app.route("/api/user_course", methods=["GET"])
def user_course():
    try:
        semester_order = {
            "1": 1,
            "2": 2,
            "summer": 3,  # "1" over "2" and "2" over "summer"
        }
        cmu_account = str(request.args.get("cmuAccount", ""))
        course_no_str = request.args.get("courseNo", "")

        if not cmu_account or not course_no_str.isdigit() or int(course_no_str) == 0:
            return jsonify({"success": False, "message": "cmuAccount and courseNo are required"}), 400

        course_no = int(course_no_str)

        # fields_to_include = {"cmuAccount": 1, "courseName": 1,
        #                      "courseNo": 1, "academicYear": 1, "semester": 1, "_id": 0}

        # courses = list(collection.find(
        #     {"cmuAccount": cmu_account, "courseNo": course_no}, fields_to_include))

        courses = list(collection.find(
            {"cmuAccount": cmu_account, "courseNo": course_no}, {"_id": 0}))

        # Sort courses by academicYear and semester with updated priority
        courses_sorted = sorted(courses, key=lambda x: (
            x['academicYear'], semester_order.get(x['semester'], 0)))

        return jsonify(courses_sorted)

    except Exception as e:

        return jsonify({"success": False, "Server error": str(e)}), 500


# retrive course by cmuAccount and courseNo
# sorted
# just header for testing
@app.route("/api/user_course/header", methods=["GET"])
def user_course_header():
    try:
        semester_order = {
            "1": 1,
            "2": 2,
            "summer": 3,  # "1" over "2" and "2" over "summer"
        }
        cmu_account = str(request.args.get("cmuAccount", ""))
        course_no_str = request.args.get("courseNo", "")

        if not cmu_account or not course_no_str.isdigit() or int(course_no_str) == 0:
            return jsonify({"success": False, "message": "cmuAccount and courseNo are required"}), 400

        course_no = int(course_no_str)

        fields_to_include = {"cmuAccount": 1, "courseName": 1,
                             "courseNo": 1, "academicYear": 1, "semester": 1, "_id": 0}

        courses = list(collection.find(
            {"cmuAccount": cmu_account, "courseNo": course_no}, fields_to_include))

        # Sort courses by academicYear and semester with updated priority
        courses_sorted = sorted(courses, key=lambda x: (
            x['academicYear'], semester_order.get(x['semester'], 0)))

        return jsonify(courses_sorted)

    except Exception as e:

        return jsonify({"success": False, "Server error": str(e)}), 500


# retrieve courses by cmuAccount
# not sort yet
# (got array of course object)
@app.route("/api/user_courses", methods=["GET"])
def user_courses():
    try:

        cmu_account = str(request.args.get("cmuAccount"))

        # Specify the fields to include in the results
        # fields_to_include = {"cmuAccount": 1, "courseName": 1,
        #                      "courseNo": 1, "academicYear": 1, "semester": 1, "_id": 0}

        # Make sure to define semester_order if it's being used for sorting
        semester_order = {'summer': 3, '2': 2, '1': 1}

        courses = list(collection.find(
            {"cmuAccount": cmu_account}, {"_id": 0}))

        # Sort courses by academicYear and semester with updated priority
        courses_sorted = sorted(courses, key=lambda x: (
            x['academicYear'], semester_order.get(x['semester'], 0)))

        # Since the _id field is not included in the projection, no need to convert it to a string
        return jsonify(courses_sorted)
    except Exception as e:

        return jsonify({"success": False, "Error retrieve user courses": str(e)}), 500


API_URL_SENTIMENT = "https://api-inference.huggingface.co/models/Chonkator/feedback_sentiment_analysis"  # sentiment
API_URL_LABEL = "https://api-inference.huggingface.co/models/Chonkator/feedback_topic_classifier"  # label
API_TOKEN = "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"
headers = {"Authorization": f"Bearer {API_TOKEN}"}


def query(payload, URL):
    try:
        response = requests.post(URL, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print("Error querying the API:", e)
        return None


def user_upload_logic():
    try:
        # Extract query parameters
        course_name = str(request.args.get("courseName"))
        course_no = int(request.args.get("courseNo"))
        academic_year = int(request.args.get("academicYear"))
        semester = str(request.args.get("semester"))

        # Parse JSON request body
        request_body = request.get_json()

        # Convert to array data structure
        comments_array = request_body.get("comments", [])
        cmu_account = request_body.get("cmuAccount")

        batch_size = 10
        batches = [comments_array[i:i + batch_size]
                   for i in range(0, len(comments_array), batch_size)]

        all_predicted_labels = []
        all_predicted_sentiments = []

        for batch in batches:
            # Assuming 'query' is a function that sends requests to your ML models and returns predictions
            # Replace 'API_URL_LABEL' and 'API_URL_SENTIMENT' with your actual API URLs
            label_predictions = query({"inputs": batch}, API_URL_LABEL)
            sentiment_predictions = query({"inputs": batch}, API_URL_SENTIMENT)

            if label_predictions is None or sentiment_predictions is None:
                print("Skipping batch due to API error.")
                continue

            predicted_labels_batch = [result[0]["label"]
                                      for result in label_predictions]
            predicted_sentiments_batch = [result[0]["label"]
                                          for result in sentiment_predictions]

            all_predicted_labels.extend(predicted_labels_batch)
            all_predicted_sentiments.extend(predicted_sentiments_batch)

        teaching_method_comments, assessment_comments, content_comments = [], [], []

        for i, comment_text in enumerate(comments_array):
            comment = {"text": comment_text,
                       "sentiment": all_predicted_sentiments[i], "label": all_predicted_labels[i]}
            if comment["label"].lower() == "teaching_method":
                teaching_method_comments.append(comment)
            elif comment["label"].lower() == "exam":
                assessment_comments.append(comment)
            elif comment["label"].lower() == "content":
                content_comments.append(comment)

        existing_course = collection.find_one({
            "cmuAccount": cmu_account,
            "courseName": course_name,
            "courseNo": course_no,
            "academicYear": academic_year,
            "semester": semester,
        })

        if existing_course:
            return jsonify({"success": True, "message": "Already have exact cmuAccount, courseName, courseNo, semester, academicYear document"})
        else:
            new_course = {
                "cmuAccount": cmu_account,
                "courseName": course_name,
                "courseNo": course_no,
                "academicYear": academic_year,
                "semester": semester,
                "teachingMethodComments": teaching_method_comments,
                "assessmentComments": assessment_comments,
                "contentComments": content_comments
            }
            collection.insert_one(new_course)
            return jsonify({"success": True, "message": "Insert as new course success"})
    except Exception as e:
        return jsonify({"success": False, "message": "Fail to add course due to some error", "error": str(e)}), 500


# post course by cmuAccount
# data pass to ML
# not support .csv yet
# for some reason this route work on second attemp
@app.route("/api/user_upload", methods=["POST"])
def user_upload_course():
    response = user_upload_logic()
    if isinstance(response, tuple) and response[1] == 500:
        print("Retrying due to server error...")
        response = user_upload_logic()
    return response


# delete course by cmuAccount
@app.route("/api/user_course_course_feedback_delete", methods=["DELETE"])
def user_delete_course():
    pass


# server configuration
if __name__ == '__main__':
    app.run(host="127.0.0.1", debug=True, port=5000)
