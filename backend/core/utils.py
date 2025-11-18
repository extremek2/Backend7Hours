import os
import uuid

def generate_unique_filename(filename):
    # 원본 파일명(filename)을 받아 UUID 기반의 고유한 파일명을 생성
    name, ext = os.path.splitext(filename)
    new_filename = f"{uuid.uuid4()}{ext}"
    return new_filename


def create_upload_path(path):
    # 폴더 경로(path)를 인자로 받아, Django ImageField.upload_to에 사용
    def upload_path_handler(instance, filename):
        # 1. 고유한 파일명 생성
        unique_filename = generate_unique_filename(filename)
        # 2. 인자로 받은 path와 파일명 결합
        return os.path.join(path, unique_filename)    
    return upload_path_handler