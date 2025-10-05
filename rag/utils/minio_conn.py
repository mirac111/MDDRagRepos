#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import logging
import time
import urllib3  # ADD THIS
import ssl      # ADD THIS  
import os       # ADD THIS
from minio import Minio
from minio.error import S3Error
from io import BytesIO
from rag import settings
from rag.utils import singleton


@singleton
class RAGFlowMinio:
    def __init__(self):
        self.conn = None
        self.__open__()

    def __open__(self):
        try:
            if self.conn:
                self.__close__()
        except Exception:
            pass

        try:
            scriptDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            clientCertFile = os.path.join(scriptDir, 'certs', 'public.crt')
            clientKeyFile = os.path.join(scriptDir, 'certs', 'private.key')
            serverCertFile = os.path.join(scriptDir, 'certs', 'server-cert.pem')
            
            logging.info(f"Looking for client certificates at: {clientCertFile}")
            logging.info(f"Looking for server certificate at: {serverCertFile}")
            
            # FORCE: Both client and server certificates must exist
            if not os.path.exists(clientCertFile):
                raise Exception(f"REQUIRED: Client certificate not found: {clientCertFile}")
            if not os.path.exists(clientKeyFile):
                raise Exception(f"REQUIRED: Client private key not found: {clientKeyFile}")
            if not os.path.exists(serverCertFile):
                raise Exception(f"REQUIRED: Server certificate not found: {serverCertFile}")
            
            # Create SSL context
            sslContext = ssl.create_default_context()
            
            # STEP 1: Load client certificate for authentication
            logging.info(f"Loading client certificate: {clientCertFile}")
            sslContext.load_cert_chain(clientCertFile, clientKeyFile)
            
            # STEP 2: Load server certificate for verification
            logging.info(f"Loading server certificate for verification: {serverCertFile}")
            sslContext.load_verify_locations(serverCertFile)
            
            # STEP 3: Enable STRICT server certificate verification
            sslContext.check_hostname = True           # Verify hostname matches certificate
            sslContext.verify_mode = ssl.CERT_REQUIRED # Require valid server certificate
            
            # STEP 4: Create HTTP client with strict verification
            httpClient = urllib3.PoolManager(
                ssl_context=sslContext,
                cert_reqs='CERT_REQUIRED'  # Server MUST have valid certificate
            )
            
            logging.info("MinIO: PRODUCTION MODE - Using BOTH client authentication AND server verification")
            
            # STEP 5: Create MinIO connection
            self.conn = Minio(settings.MINIO["host"],
                            access_key=settings.MINIO["user"],
                            secret_key=settings.MINIO["password"],
                            secure=True,
                            http_client=httpClient
                            )
            
            logging.info(f"MinIO PRODUCTION connection established: {settings.MINIO['host']}")
            
        except Exception:
            logging.exception(
                "Fail to connect %s " % settings.MINIO["host"])

    def __close__(self):
        del self.conn
        self.conn = None

    def health(self):
        bucket, fnm, binary = "txtxtxtxt1", "txtxtxtxt1", b"_t@@@1"
        if not self.conn.bucket_exists(bucket):
            self.conn.make_bucket(bucket)
        r = self.conn.put_object(bucket, fnm,
                                 BytesIO(binary),
                                 len(binary)
                                 )
        return r

    def put(self, bucket, fnm, binary):
        for _ in range(3):
            try:
                if not self.conn.bucket_exists(bucket):
                    self.conn.make_bucket(bucket)

                r = self.conn.put_object(bucket, fnm,
                                         BytesIO(binary),
                                         len(binary)
                                         )
                return r
            except Exception:
                logging.exception(f"Fail to put {bucket}/{fnm}:")
                self.__open__()
                time.sleep(1)

    def rm(self, bucket, fnm):
        try:
            self.conn.remove_object(bucket, fnm)
        except Exception:
            logging.exception(f"Fail to remove {bucket}/{fnm}:")

    def get(self, bucket, filename):
        for _ in range(1):
            try:
                r = self.conn.get_object(bucket, filename)
                return r.read()
            except Exception:
                logging.exception(f"Fail to get {bucket}/{filename}")
                self.__open__()
                time.sleep(1)
        return

    def obj_exist(self, bucket, filename):
        try:
            if not self.conn.bucket_exists(bucket):
                return False
            if self.conn.stat_object(bucket, filename):
                return True
            else:
                return False
        except S3Error as e:
            if e.code in ["NoSuchKey", "NoSuchBucket", "ResourceNotFound"]:
                return False
        except Exception:
            logging.exception(f"obj_exist {bucket}/{filename} got exception")
            return False

    def get_presigned_url(self, bucket, fnm, expires):
        for _ in range(10):
            try:
                return self.conn.get_presigned_url("GET", bucket, fnm, expires)
            except Exception:
                logging.exception(f"Fail to get_presigned {bucket}/{fnm}:")
                self.__open__()
                time.sleep(1)
        return

    def remove_bucket(self, bucket):
        try:
            if self.conn.bucket_exists(bucket):
                objects_to_delete = self.conn.list_objects(bucket, recursive=True)
                for obj in objects_to_delete:
                    self.conn.remove_object(bucket, obj.object_name)
                self.conn.remove_bucket(bucket)
        except Exception:
            logging.exception(f"Fail to remove bucket {bucket}")

