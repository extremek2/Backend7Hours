import requests
from django.contrib.gis.geos import LineString, Point
from django.contrib.auth import get_user_model
from django.contrib.gis.db.models.functions import Distance
from .models import Path
from datetime import datetime
from urllib.parse import unquote
from geopy.distance import distance as geopy_distance


User = get_user_model() # 런타임에서 CustomUser 클래스 반환

class PathService:
    BASE_URL = "https://apis.data.go.kr/B551011/Durunubi/courseList"

    # --------------------------
    # 위치 기반 추천
    # --------------------------
       
    @staticmethod
    def get_or_create_paths(lat: float, lng: float, radius_m: int = 5000):
        """위치 기반 DB 검색 → 없으면 외부 API 호출 후 저장"""
        point = Point(lng, lat, srid=4326)
        
        # DB에서 반경 내 경로 조회 (km 아닌 m 로 통일)
        paths = Path.objects.annotate(distance_m=Distance("geom", point))\
                            .filter(distance_m__lte=radius_m)

        if paths.exists():
            return paths

        # DB에 없으면 외부 API 호출
        api_data = PathService.fetch_duurunubi_data()
        if not api_data:
            return []

        admin_user = User.objects.get(email="admin@example.com")
        
        new_paths = []
        for item in api_data:
            gpx_url = item.get("gpxpath")
            if not gpx_url:
                continue
            
            # 1. GPX 시작 좌표만 가져옴 (성능 개선)
            start_coord = PathService.fetch_gpx_start_coord(gpx_url)
            if not start_coord:
                continue
            
            # 2. 시작 좌표가 사용자 위치 기준 radius_m 안에 있는지 체크 (단일 지점 비교)
            user_point = (lat, lng)
            start_point = (start_coord["lat"], start_coord["lng"])
            
            if geopy_distance(user_point, start_point).m > radius_m:
                continue
            
            
            # --- 경로 저장 로직 (필터링 통과 후) ---
            
            # 3. 필터링을 통과한 경우, 전체 GPX 데이터를 다시 가져와서 저장
            # 성능 최적화를 위해, 실제 저장할 때만 전체 GPX를 파싱 필요
            coords = PathService.fetch_gpx_coords(gpx_url)
            if not coords:
                 continue
            # JSON 객체 형식으로 변환
            geom = PathService.create_linestring(PathService.fill_z_values(coords))  
            
            if not geom:
                continue
                                
            
            # 외부 API는 km 단위 제공, m 단위로 변환
            distance_m = float(item.get("crsDstnc") or 0) * 1000
            duration_min = item.get("crsTotlRqrmHour") or 0
            
            new_paths.append(Path(
                auth_user=admin_user,
                path_name=item.get("crsKorNm"),
                path_comment=item.get("crsSummary"),
                distance=distance_m,
                duration=duration_min,
                level=int(item.get("crsLevel", 2)),
                is_private=False,
                geom=geom,
            ))
            
        if new_paths:
            Path.objects.bulk_create(new_paths)

        # 새로 저장된 경로 포함해서 반환
        return Path.objects.annotate(distance_m=Distance("geom", point))\
                           .filter(distance_m__lte=radius_m)

    # --------------------------
    # 사용자 입력 처리
    # --------------------------
    @staticmethod
    def create_from_user_input(user_id, path_name=None, path_comment=None,
                        coords_json=None, start_time=None, end_time=None,
                        level=None, distance=None, duration=None, 
                        thumbnail=None, is_private=None):
        """사용자가 보낸 좌표를 저장 (JSON 객체, 서버에서 z값 채움)"""
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

        coords_3d = PathService.fill_z_values(coords_json)
        geom = PathService.create_linestring(coords_3d)
        
        # distance가 제공되지 않으면 계산
        if distance is None:
            distance = PathService.calculate_distance(geom)

        # duration이 제공되지 않으면 start_time과 end_time으로 계산
        if duration is None and start_time and end_time:
            duration = int((end_time - start_time).total_seconds() / 60)
        # if start_time and end_time:
        #     duration = int((end_time - start_time).total_seconds() / 60)

        # level이 제공되지 않으면 추정
        if level is None:
            level = PathService.estimate_level(geom)

        # level = PathService.estimate_level(geom)

        path = Path.objects.create(
            auth_user=user,
            path_name=path_name or f"Path_{user.id}_{datetime.now().strftime('%Y%m%d%H%M')}",
            path_comment=path_comment,
            distance=distance,
            duration=duration,
            level=level,
            thumbnail=thumbnail,
            is_private=is_private if is_private is not None else False,
            geom=geom,
        )
        return path

    # --------------------------
    # 외부 API
    # --------------------------
    @staticmethod
    def fetch_duurunubi_data():
        serviceKey = unquote("Um%2Bqj6eBcNF3%2FgXOHnehh%2BpF5QvECe9Q4DGbptVAij9wB3Flsx5KDTC5hPaf5kq636FuXDi0eG1jy8KjF8BfJQ%3D%3D")
        """두루누비 API 호출"""
        params = {
            "serviceKey": serviceKey,
            "MobileOS": "ETC",
            "MobileApp": "7hours",
            "_type": "json",
            "numOfRows": 10,  # 총 307개 -> 임시로 10개 설정
            "pageNo": 1,
        }
        try:
            res = requests.get(PathService.BASE_URL, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
            items = data["response"]["body"]["items"]["item"]
            return items
        except Exception as e:
            print(f"[두루누비 API 오류] {e}")
            return []

    @staticmethod
    def fetch_gpx_coords(gpx_url):
        """GPX 파일에서 좌표 x,y,z 추출 → JSON 객체로 반환"""
        try:
            res = requests.get(gpx_url, timeout=5)
            res.raise_for_status()
            from xml.etree import ElementTree as ET
            tree = ET.fromstring(res.text)
            ns = {"gpx": "http://www.topografix.com/GPX/1/1"}
            coords = []
            for trkpt in tree.findall(".//gpx:trkpt", ns):
                lat = float(trkpt.attrib["lat"])
                lon = float(trkpt.attrib["lon"])
                ele_el = trkpt.find("gpx:ele", ns)
                ele = float(ele_el.text) if ele_el is not None else 0.0
                coords.append({"lat": lat, "lng": lon, "z": ele})
            return coords
        except Exception as e:
            print(f"[GPX 파싱 오류] {e}")
            return []

    @staticmethod
    def fetch_gpx_start_coord(gpx_url):
        """GPX 파일에서 경로의 첫 번째 좌표 (lat, lng, z)만 추출합니다."""
        try:
            res = requests.get(gpx_url, timeout=5)
            res.raise_for_status()
            
            from xml.etree import ElementTree as ET
            root = ET.fromstring(res.text)
            ns = {"gpx": "http://www.topografix.com/GPX/1/1"}
            
            # 첫 번째 trkpt 태그만 찾습니다.
            trkpt = root.find(".//gpx:trkpt", ns)
            
            if trkpt is None:
                return None

            lat = float(trkpt.attrib["lat"])
            lon = float(trkpt.attrib["lon"])
            ele_el = trkpt.find("gpx:ele", ns)
            ele = float(ele_el.text) if ele_el is not None else 0.0
            
            # 첫 번째 좌표만 반환
            return {"lat": lat, "lng": lon, "z": ele}
            
        except Exception as e:
            # print(f"[GPX 시작 좌표 파싱 오류] {e}") # 디버깅 시 필요
            return None

    # --------------------------
    # GIS 계산
    # --------------------------
    @staticmethod
    def create_linestring(coords):
        try:
            return LineString(coords, srid=4326)
        except Exception:
            return None

    @staticmethod
    def calculate_distance(geom):
        """
        LineString(SRID 4326)의 정확한 길이를 미터(m) 단위로 계산합니다.
        이를 위해 대한민국에 적합한 투영 좌표계(5179)로 변환합니다.
        """
        if not geom or geom.empty:
            return 0
            
        try:
            # LineString을 미터 단위 SRID(5179)로 변환하고 길이를 측정
            # .length는 변환 후 미터(m) 단위로 반환됩니다.
            # clone=True는 원본 geom을 변경하지 않기 위함
            distance_m = geom.transform(5179, clone=True).length 
            return distance_m
        except Exception as e:
            # 변환 중 오류 발생 시, 0 또는 대체 값 반환
            print(f"[거리 계산 오류] {e}")
            return 0

    @staticmethod
    def estimate_level(geom):
        if not geom or geom.empty:
            return 2
        elevations = [pt[2] for pt in geom if len(pt) == 3]
        if not elevations:
            return 2
        diff = max(elevations) - min(elevations)
        if diff < 30:
            return 1
        elif diff < 100:
            return 2
        return 3

    @staticmethod
    def fill_z_values(coords):
        """coords가 dict 형식이든 (lat, lng) 튜플이든 모두 처리"""
        coords_3d = []
        for c in coords:
            # dict 타입일 때
            if isinstance(c, dict):
                lat = c.get("lat")
                lon = c.get("lng")
                ele = c.get("z", 0.0)
            # tuple/list 타입일 때
            elif isinstance(c, (list, tuple)):
                lat, lon = c
                ele = 0.0
            else:
                continue

            coords_3d.append((lon, lat, ele))  # GEOS는 (x=lon, y=lat, z)
        return coords_3d