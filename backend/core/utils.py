import os
import uuid

def generate_unique_filename(filename):
    # 원본 파일명(filename)을 받아 UUID 기반의 고유한 파일명을 생성
    name, ext = os.path.splitext(filename)
    new_filename = f"{uuid.uuid4()}{ext}"
    return new_filename


# 인자를 받는 함수를 클래스로 대체합니다.
class UploadFilePathGenerator:
    def __init__(self, path):
        self.path = path 

    def __call__(self, instance, filename):
        unique_filename = generate_unique_filename(filename)
        # instance 정보(예: owner.id)를 경로에 사용하려면 여기에 추가 로직 필요
        return os.path.join(self.path, unique_filename)

    # 🔑 핵심 해결책: deconstruct() 메서드 구현
    def deconstruct(self):
        # 1. 경로 (path)
        path = f'{self.__class__.__module__}.{self.__class__.__name__}'
        
        # 2. 인자 (args): __init__에 전달된 인자들을 튜플로 반환
        args = (self.path,)
        
        # 3. 키워드 인자 (kwargs): 현재는 사용하지 않으므로 빈 딕셔너리
        kwargs = {}
        
        return path, args, kwargs