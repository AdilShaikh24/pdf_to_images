import os

class CommonUtil:
    TEMP_DATA_FOLDER = "/tmp"
    GOOGLE_CREDENTIAL_FILE = "path.json"

    @staticmethod
    def get_auth_id():
        return "auth_id"

    @staticmethod
    def get_temp_folder_path(path):
        full_path = os.path.join(CommonUtil.TEMP_DATA_FOLDER, str(path))
        return full_path

    @staticmethod
    def copy_file_from_storage(storage_path, bucket, local_path):
        blob = bucket.get_blob(storage_path)
        if blob is None:
            raise Exception("storage path {} not found".format(storage_path))
        with open(local_path, "wb") as file_obj:
            blob.download_to_file(file_obj)

    @staticmethod
    def copy_file_to_storage(local_path, bucket, storage_path):
        blob = bucket.blob(storage_path)
        blob.upload_from_filename(filename=local_path)

    @staticmethod
    def get_blob(storage_path, bucket):
        blob = bucket.get_blob(storage_path)
        return blob
