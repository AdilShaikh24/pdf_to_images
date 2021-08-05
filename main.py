import sys
import time
import tempfile
import os
from flask import Flask, request, jsonify, Response
from google.cloud import datastore
from google.cloud import storage
from pdf2image import convert_from_path, page_count
import json
from auth_decorator import authorize_request
import shutil
import datetime
from datetime import timedelta
from util.common_util import CommonUtil
from util.log_service import get_logger

os.environ['LD_LIBRARY_PATH'] = os.getcwd() + "/shared_lib"
# For Locally Only
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CommonUtil.GOOGLE_CREDENTIAL_FILE

datastore_client = datastore.Client()
storage_client = storage.Client()

logService = get_logger("Pdf Extraction..")

app = Flask(__name__)


@app.route('/', methods=['POST'])
@authorize_request
def image_extraction():
    logService.info("Image extraction..")
    start_time = time.time()
    try:
        json_data = request.data
        data_dict = json.loads(json_data)
        user_key = data_dict['user_key']
        doc_id = data_dict['doc_id']
        project_id = data_dict['project_id']
        first_page = data_dict['first_pg']
        last_page = data_dict['last_pg']

        print(data_dict)

        temp_folder = os.path.join(CommonUtil.get_temp_folder_path(project_id), str(doc_id))
        if not os.path.isdir(temp_folder):
            os.makedirs(temp_folder)
        datastore, bucket = authenticate_services_service_account(temp_folder, project_id)

        doc_key = datastore.key('TextDocument', int(doc_id))
        text_document = datastore.get(doc_key)
        pdf_file_name = text_document['file_name']
        pdf_file_storage_path = text_document['file_path'][1:]
        while first_page <= last_page:
            img_file_name = "{}_image_{}.jpg".format(pdf_file_name, str(first_page))
            img_file_storage_path = "ocr_annotation/{}//{}/{}".format(user_key, pdf_file_storage_path, img_file_name)
            img_blob = CommonUtil.get_blob(img_file_storage_path, bucket)
            if img_blob:
                logService.info("Image:{0} already extracted..".format(str(first_page)))
                first_page += 1
            else:
                logService.info("Image:{0} is not found. Image extraction process started..".format(str(first_page)))
                break
        if first_page > last_page:
            return Response("All images are already extracted.", 200)
        pdf_file_local_path = "{}/{}_{}".format(temp_folder, user_key, pdf_file_name)
        CommonUtil.copy_file_from_storage(pdf_file_storage_path, bucket, pdf_file_local_path)

        try:
            pages = convert_from_path(pdf_file_local_path, dpi=210, first_page=first_page,
                                          last_page=last_page, fmt="jpg")
            # print(os.listdir("/tmp"))
            saving_extracted_pages(temp_folder, pages, text_document, user_key, start_time, first_page, bucket)
        finally:
            try:
                if os.path.isdir(temp_folder):
                    logService.info("cleaning intermediate files")
                    shutil.rmtree(temp_folder, ignore_errors=True)
                    logService.info("successfully cleaned intermediate files")
            except:
                exp = sys.exc_info()
                error_message = "Error while cleaning folder {} not found. type {}, value {}, traceback {}"\
                                .format(temp_folder, exp[0], exp[1], exp[2])
                logService.info(error_message)
    except:
        exp = sys.exc_info()
        error_message = "error while processing pdf extraction. type {}, value {}, traceback {}"\
                        .format(exp[0], exp[1], exp[2])
        logService.error(error_message)
        return Response("Error during image extraction:" + str(error_message), 500)
    return Response("Successfully images extracted..", 200)


@app.route('/count-pdf', methods=['GET', 'POST'])
@authorize_request
def count_pdf():
    try:
        logService.info("Pdf page count..")
        count = 0
        json_data = request.data
        data_dict = json.loads(json_data)
        user_key = data_dict['user_key']
        doc_id = data_dict['doc_id']
        project_id = data_dict['project_id']

        temp_folder = os.path.join(CommonUtil.get_temp_folder_path(project_id), str(doc_id))
        if not os.path.isdir(temp_folder):
            os.makedirs(temp_folder)
        datastore, bucket = authenticate_services_service_account(temp_folder, project_id)

        doc_key = datastore.key('TextDocument', int(doc_id))
        text_document = datastore.get(doc_key)
        pdf_file_name = text_document['file_name']
        pdf_file_storage_path = text_document['file_path'][1:]

        pdf_file_local_path = "{}/{}_{}".format(temp_folder, user_key, pdf_file_name)
        CommonUtil.copy_file_from_storage(pdf_file_storage_path, bucket, pdf_file_local_path)
        try:
            count = page_count(pdf_file_local_path)
        finally:
            try:
                if os.path.isdir(temp_folder):
                    logService.info("cleaning intermediate files")
                    shutil.rmtree(temp_folder, ignore_errors=True)
                    logService.info("successfully cleaned intermediate files")
            except:
                exp = sys.exc_info()
                error_message = "Error while cleaning folder {} not found. type {}, value {}, traceback {}" \
                    .format(temp_folder, exp[0], exp[1], exp[2])
                logService.info(error_message)
        logService.info("Total pages in pdf: {}".format(str(count)))
        return jsonify(count)
    except:
        exp = sys.exc_info()
        error_message = "Error during pdf page count. type {}, value {}, traceback {}".format(exp[0], exp[1], exp[2])
        logService.error(error_message)
        return Response(error_message, 500)

@app.route('/generate_download_signed_url_v4', methods=['POST'])
@authorize_request
def generate_download_signed_url_v4():
    """Generates a v4 signed URL for downloading a blob.

    Note that this method requires a service account key file. You can not use
    this if you are using Application Default Credentials from Google Compute
    Engine or from the Google Cloud SDK.
    """

    json_data = request.data
    data_dict = json.loads(json_data)
    logService.info(data_dict)
    user_key = data_dict['user_key']
    project_id = data_dict['project_id']
    file_path = data_dict['file_path']

    temp_folder = CommonUtil.get_temp_folder_path(project_id)
    if not os.path.isdir(temp_folder):
        os.makedirs(temp_folder)

    datastore, bucket = authenticate_services_service_account(temp_folder, project_id)
    blob = bucket.blob(file_path)

    url = blob.generate_signed_url(
        version='v4',
        # This URL is valid for 15 minutes
        expiration=datetime.timedelta(minutes=120),
        # Allow GET requests using this URL.
        method='PUT')

    print('Generated GET signed URL:')
    print(url)
    print('You can use this URL with any user agent, for example:')
    print('curl \'{}\''.format(url))
    return Response(url, 200)

def example_task_handler(payload):
    """Log the request payload."""
    payload = payload
    print('Received task with payload: {}'.format(payload))
    print(datetime.datetime.now())
    return Response('Printed task payload: {}'.format(payload), 200)


def saving_extracted_pages(temp_folder, pages, doc, user_key, start_time, first_page, bucket):
    logService.info("Saving Extracted Images..")
    for page in pages:
        img_file_name = "{}_image_{}.jpg".format(doc['file_name'], str(first_page))
        img_file_local_path = os.path.join(temp_folder, img_file_name)
        page.save(img_file_local_path, "JPEG")
        first_page += 1
        try:
            img_file_storage_path = "ocr_annotation/{}/{}/{}".format(user_key, doc['file_path'], img_file_name)
            CommonUtil.copy_file_to_storage(img_file_local_path, bucket, img_file_storage_path)
        finally:
            try:
                os.remove(img_file_local_path)
            except:
                exp = sys.exc_info()
                error_message = "Error while deleting image {}. type{}, value {}, traceback {}".format(img_file_local_path, exp[0], exp[1], exp[2])
                logService.error(error_message)
    end_time = time.time()
    logService.info(timedelta(seconds=end_time - start_time))


def authenticate_services_service_account(temp_folder, project_id):
    service_account_local_path = os.path.join(temp_folder, "service-account.json")
    application_config_key = datastore_client.key("ApplicationConfig", project_id)
    application_config = datastore_client.get(application_config_key)
    with open(service_account_local_path, "w") as file_obj:
        file_obj.write(application_config['value'])
    datastore = datastore_client.from_service_account_json(service_account_local_path)
    storage = storage_client.from_service_account_json(service_account_local_path)
    bucket_name = project_id + ".appspot.com"
    bucket = storage.bucket(bucket_name)
    return datastore, bucket


if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.

    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.3', port=8080, debug=True)


