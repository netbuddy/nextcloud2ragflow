"""Simplest example of files_dropdown_menu + notification."""
import os
import tempfile
from contextlib import asynccontextmanager
from os import path
from typing import Annotated

import requests
from fastapi import BackgroundTasks, Depends, FastAPI, responses


from nc_py_api import FsNode, NextcloudApp
from nc_py_api.ex_app import AppAPIAuthMiddleware, LogLvl, nc_app, run_app, set_handlers
from nc_py_api.files import ActionFileInfoEx


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_handlers(app, enabled_handler)
    yield


APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)

def upload_file_to_kb(file_path, kb_name, token='ragflow-xxxxxxxxxxxxx', parser_id='naive'):
    """  
    Uploads a file to a knowledge base.  

    Args:  
    - file_path: Path to the file to upload.  
    - kb_name: Name of the target knowledge base.  
    - parser_id: ID of the chosen file parser (defaults to 'naive').  
    - token: API token for authentication.  
    """
    url = 'http://192.168.213.11:7080/v1/api/document/upload'  # Replace with your actual API URL  
    files = {'file': open(file_path, 'rb')}  # The file to upload  
    data = {'kb_name': kb_name, 'parser_id': parser_id, 'run': '0'}  # Additional form data  
    headers = {'Authorization': f'Bearer {token}'}  # Replace with your actual Bearer token  

    response = requests.post(url, files=files, data=data, headers=headers)

    if response.status_code == 200:
        print("File uploaded successfully:", response.json())
    else:
        print("Failed to upload file:", response.status_code, response.text)
def upload_file_to_ragflow(input_file: FsNode, nc: NextcloudApp):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # 构造临时文件路径，保持原始文件名
            temp_file_path = os.path.join(temp_dir, input_file.name)
            
            # 下载文件到临时路径
            with open(temp_file_path, 'wb') as temp_file:
                nc.files.download2stream(input_file, temp_file)
            
            nc.log(LogLvl.WARNING, f"File downloaded to {temp_file_path}")
            print(f"Temporary file path: {temp_file_path}")

            # 设置上传参数
            file_to_upload = temp_file_path
            knowledge_base_name = 'docker'
            # Assume you have already obtained your token and set it here  
            token = 'ragflow-cwZGYzYzRjOGI5MTExZWY5ZTIyMDI0Mm'

            # Call the function to upload the file  
            upload_file_to_kb(file_to_upload, knowledge_base_name, token=token)

            nc.notifications.create(f"{input_file.name} finished!", f"nextcloud is waiting for you!")
    except Exception as e:
        nc.log(LogLvl.ERROR, str(e))
        nc.notifications.create("Error occurred", "Error information was written to log file")


@APP.post("/file_to_ragflow")
async def file_to_ragflow(
    files: ActionFileInfoEx,
    nc: Annotated[NextcloudApp, Depends(nc_app)],
    background_tasks: BackgroundTasks,
):
    for one_file in files.files:
        background_tasks.add_task(upload_file_to_ragflow, one_file.to_fs_node(), nc)
    return responses.Response()


def enabled_handler(enabled: bool, nc: NextcloudApp) -> str:
    print(f"enabled={enabled}")
    try:
        if enabled:
            nc.ui.files_dropdown_menu.register_ex(
                "to_ragflow",
                "To RagFlow",
                "/file_to_ragflow",
                mime="pdf",
                icon="img/icon.svg",
            )
    except Exception as e:
        return str(e)
    return ""


if __name__ == "__main__":
    run_app(
        "main:APP",
        log_level="trace",
    )
