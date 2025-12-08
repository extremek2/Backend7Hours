from django.contrib.gis.geos import LineString
import polyline
import math


class GisUtils:
    # --------------------------
    # GIS 계산
    # --------------------------
    @staticmethod
    def create_linestring(coords):
        try:
            return LineString(coords, srid=4326)
        except Exception:
            return None
    
    
    # 일단 거리 계산은 DB에 위임해서 이 과정은 없어도 되지만 만일을 위해 남겨둠
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
    def estimate_level(geom: LineString) -> int:
        """
        경로 난이도 추정 (DEM 기반 + fallback)
        - geom: LineString (2D 또는 3D, z값이 None일 수도 있음)
        - 반환: 1(쉬움), 2(보통), 3(어려움)
        """
        from apps.paths.dem_utils import get_dem
        
        if not geom or geom.empty:
            return 2  # 기본 난이도

        try:
            dem = get_dem()

            # 3D 좌표 생성: DEM이 null 처리
            geom_3d_coords = []
            for coord in geom.coords:
                lon, lat = coord[0], coord[1]
                z = coord[2] if len(coord) > 2 and coord[2] is not None else 0.0
                geom_3d_coords.append((lon, lat, z))
            geom_3d = LineString(geom_3d_coords, srid=4326)

            # DEM으로 난이도 계산
            geom_3d = dem.add_elevation_to_linestring(geom_3d)
            return dem.estimate_difficulty_level(geom_3d)

        except Exception as e:
            print(f"[DEM 난이도 계산 실패] {e}, fallback 사용")

            # fallback: z값 기반, null이면 0.0
            elevations = [pt[2] if len(pt) > 2 and pt[2] is not None else 0.0 for pt in geom]
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
        """
        coords에 DEM 기반 실제 고도 값 채우기 (업그레이드)
        coords가 dict 형식이든 (lat, lng) 튜플이든 모두 처리
        """
        from apps.paths.dem_utils import get_dem
        try:
            dem = get_dem()
            coords_3d = []
            
            for c in coords:
                # dict 타입일 때
                if isinstance(c, dict):
                    lat = c.get("lat")
                    lon = c.get("lng")
                    ele = c.get("z")  # 기존 z 값이 있으면 사용
                # tuple/list 타입일 때
                elif isinstance(c, (list, tuple)):
                    lat, lon = c
                    ele = None
                else:
                    continue
                
                # DEM에서 실제 고도 가져오기
                if ele is None:
                    ele = dem.get_elevation(lat, lon)
                    if ele is None:
                        ele = 0.0
                
                coords_3d.append((lon, lat, ele))  # GEOS는 (x=lon, y=lat, z)
            
            return coords_3d
        except Exception as e:
            print(f"[DEM 고도 채우기 실패] {e}, 기본값 사용")
            # fallback: 기존 방식 (z=0)
            coords_3d = []
            for c in coords:
                if isinstance(c, dict):
                    lat = c.get("lat")
                    lon = c.get("lng")
                    ele = c.get("z", 0.0)
                elif isinstance(c, (list, tuple)):
                    lat, lon = c
                    ele = 0.0
                else:
                    continue
                coords_3d.append((lon, lat, ele))
            return coords_3d
        
    # --------------------------
    # DEM 관련 메서드 (새로 추가)
    # --------------------------
    @staticmethod
    def add_elevation_to_linestring(geom: LineString) -> LineString:
        """
        LineString에 DEM 기반 실제 고도 값 추가 (2D -> 3D)
        
        Args:
            geom: LineString (SRID 4326)
        
        Returns:
            LineString with elevation (3D)
        """
        try:
            dem = get_dem()
            return dem.add_elevation_to_linestring(geom)
        except Exception as e:
            print(f"[고도 추가 실패] {e}")
            return geom
    
    @staticmethod
    def get_elevation_stats(geom: LineString) -> dict:
        """
        경로의 고도 통계 가져오기
        
        Returns:
            {
                'min_elevation': 최저 고도,
                'max_elevation': 최고 고도,
                'avg_elevation': 평균 고도,
                'elevation_gain': 누적 상승,
                'elevation_loss': 누적 하강,
                'total_change': 총 고도 변화
            }
        """
        from apps.paths.dem_utils import get_dem
        try:
            dem = get_dem()
            return dem.get_elevation_stats(geom)
        except Exception as e:
            print(f"[고도 통계 계산 실패] {e}")
            return None
    
    @staticmethod
    def get_elevation_profile(geom: LineString, num_samples: int = 100) -> list:
        """
        경로의 고도 프로파일 가져오기 (차트용)
        
        Args:
            geom: LineString (SRID 4326)
            num_samples: 샘플링 포인트 수
        
        Returns:
            [{'distance': 거리(m), 'elevation': 고도(m)}, ...]
        """
        from apps.paths.dem_utils import get_dem
        try:
            dem = get_dem()
            return dem.get_elevation_profile(geom, num_samples)
        except Exception as e:
            print(f"[고도 프로파일 생성 실패] {e}")
            return []
        
        
    # --------------------------
    # polyline 디코딩 
    # --------------------------
    @staticmethod
    def decode_polyline(polyline_str):
        """
        polyline 문자열 -> [(lat, lng, z), ...] 리스트로 변환
        GEOS LineString용 (lon, lat) 튜플로 반환
        """
        try:
            coords = polyline.decode(polyline_str)  # [(lat, lng), ...]
            return [(lng, lat, 0.0) for lat, lng in coords]  # z=0.0
        except Exception as e:
            print(f"[Polyline 디코딩 오류] {e}")
            return []
    
    # --------------------------
    # 지도 중심점 및 줌 레벨
    # --------------------------
    @staticmethod
    def calculate_map_center_and_zoom(geom: LineString) -> tuple[float, float, int]:
        """
        경로의 Bounding Box 기반으로 중심점과 적절한 Zoom Level 계산
        (Naver Static Map 600x600px 기준 경험적 보정 포함)
        
        반환: (중심 경도, 중심 위도, 줌 레벨)
        """
        if not geom or len(geom.coords) == 0:
            # (서울 시청 근처 중심)
            return 126.9779, 37.5665, 12

        min_lng, min_lat, max_lng, max_lat = geom.extent

        center_lng = (min_lng + max_lng) / 2
        center_lat = (min_lat + max_lat) / 2

        # 경도/위도 범위
        span_lng = max_lng - min_lng
        span_lat = max_lat - min_lat
        max_span = max(span_lng, span_lat)

        # # Naver Static Map 600x600px 경험적 Zoom 레벨 계산
        # # 참고: map_scale=2, tile_size=256 기준
        # if max_span < 0.002:        # 약 200m 미만
        #     zoom_level = 17
        # elif max_span < 0.004:      # 약 400m 미만
        #     zoom_level = 16
        # elif max_span < 0.006:      # 약 600m 미만
        #     zoom_level = 15
        # elif max_span < 0.008:      # 약 800m 미만
        #     zoom_level = 14
        # elif max_span < 0.01:       # 약 1km 미만
        #     zoom_level = 13
        # elif max_span < 0.015:      # 약 1.5km 미만
        #     zoom_level = 12
        # elif max_span < 0.025:      # 약 2.5km 미만
        #     zoom_level = 11
        # elif max_span < 0.05:       # 약 5km 미만
        #     zoom_level = 10
        # elif max_span < 0.1:        # 약 10km 미만
        #     zoom_level = 9
        # else:                        # 10km 이상
        #     zoom_level = 8
        
        zoom_level = GisUtils.span_to_zoom(max_span)

        return center_lng, center_lat, zoom_level

    @staticmethod
    def latlng_to_pixel(lat, lng, center_lat, center_lng, zoom, img_w, img_h):
        """
        위도/경도를 Naver Static Map 이미지 픽셀 좌표로 변환
        - center_lat/center_lng: 지도 중심
        - zoom: 지도 Zoom Level (Naver 기준)
        - img_w/img_h: 이미지 크기

        Naver 공식 projection과 경험적 보정 적용
        """
        # 기본 Tile Size와 scale
        TILE_SIZE = 256
        scale = 2 ** zoom

        def lon_to_x(lon):
            return (lon + 180.0) / 360.0

        def lat_to_y(lat):
            lat_rad = math.radians(lat)
            return 0.5 - math.log(math.tan(math.pi / 4 + lat_rad / 2)) / (2 * math.pi)

        center_x = lon_to_x(center_lng)
        center_y = lat_to_y(center_lat)

        x = (lon_to_x(lng) - center_x) * TILE_SIZE * scale + img_w / 2
        y = (lat_to_y(lat) - center_y) * TILE_SIZE * scale + img_h / 2

        return x, y
    
    @staticmethod
    def naver_color_to_pillow(hex_color: str) -> str:
        """
        Naver의 0xAARRGGBB 형식을 Pillow에서 사용 가능한 #RRGGBBAA 로 변환
        """
        if hex_color.startswith("0x"):
            hex_color = hex_color[2:]

        if len(hex_color) != 8:
            raise ValueError(f"Invalid Naver color format: {hex_color}")

        aa = hex_color[0:2]
        rr = hex_color[2:4]
        gg = hex_color[4:6]
        bb = hex_color[6:8]

        # Pillow expects #RRGGBBAA
        return f"#{rr}{gg}{bb}{aa}"
    
    @staticmethod
    def span_to_zoom(max_span: float, img_size_px: int = 600, padding: float = 0.1) -> int:
        """
        max_span(경도/위도 단위) 값을 받아서 적절한 Zoom Level을 계산합니다.
        
        Args:
            max_span (float): 경로의 최대 범위 (경도 또는 위도)
            img_size_px (int): 생성할 이미지 크기 (가로/세로, 정사각형 가정)
            padding (float): 이미지 여백 비율 (0~1)
            
        Returns:
            int: 적절한 Zoom Level
        """
        TILE_SIZE = 256  # 네이버/구글 등 타일 기준
        # 경로의 최대 span에 padding 적용
        effective_span = max_span * (1 + padding)
        
        # Zoom Level 공식: zoom = log2(360 * img_size_px / (effective_span * TILE_SIZE))
        zoom = math.log2((360 * img_size_px) / (effective_span * TILE_SIZE))
        
        # 현실적인 Zoom Level 범위 제한
        zoom = max(1, min(int(round(zoom)), 20))
        return zoom