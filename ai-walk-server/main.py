import os
import json  # JSON 변환 위해 필요
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi import HTTPException

app = FastAPI()

# Docker Container 내부에서 Ollama 접근 URL
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

class Diary(BaseModel):
    pathId: int
    distance: float
    duration: int
    pathName: str

class DiaryResponse(BaseModel):
    diary: str

@app.post("/generate-diary")
async def generate_diary(data: Diary):
    prompt = f"""
반려견 산책 데이터를 기반으로 따뜻하고 감성적인 산책 기록을 만들어줘.

- 거리: {data.distance}km
- 시간: {data.duration}분
- 산책로 이름: {data.pathName}

조건:
1. 글자 수 100~150자.
2. 데이터 기반으로만 작성.
3. 한국어로만 작성.
4. 마지막 줄에 반려견 칭찬 한 문장.

"""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",  
            json={"model": "qwen2.5:7b", "prompt": prompt, "stream": False},
            timeout=180)
        response.raise_for_status()
        
        result = response.json()
        
        # ✅ stream=False일 때는 한 번에 응답
        diary_text = result.get("response", "")
        
        if not diary_text:
            raise HTTPException(status_code=500, detail="다이어리 생성 실패")
        
        return DiaryResponse(diary=diary_text)
        
    except requests.exceptions.ConnectionError as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Ollama 서버 연결 실패: {str(e)}"
        )
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="응답 시간 초과")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"오류 발생: {str(e)}")

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)  # ✅ 8002