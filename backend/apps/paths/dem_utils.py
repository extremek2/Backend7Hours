"""
DEM 파일 유틸리티
한국 지형 데이터(SRTM 30m) 활용 - PostGIS 통합
"""
import rasterio
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, List
from django.contrib.gis.geos import LineString, Point


class KoreaDEM:
    """한국 DEM 데이터 핸들러 - PostGIS 통합"""
    
    def __init__(self, dem_path: str = "/app/data/dem/korea_dem.tif"):
        self.dem_path = Path(dem_path)
        if not self.dem_path.exists():
            raise FileNotFoundError(f"DEM 파일을 찾을 수 없습니다: {dem_path}")
        
        self._dataset = None
    
    @property
    def dataset(self):
        """DEM 데이터셋 (lazy loading)"""
        if self._dataset is None:
            self._dataset = rasterio.open(self.dem_path)
        return self._dataset
    
    def get_elevation(self, lat: float, lon: float) -> Optional[float]:
        """
        특정 좌표의 고도 가져오기
        
        Args:
            lat: 위도 (33-39°N)
            lon: 경도 (124-132°E)
        
        Returns:
            고도 (미터), 범위 밖이면 None
        """
        try:
            row, col = self.dataset.index(lon, lat)
            
            if not (0 <= row < self.dataset.height and 0 <= col < self.dataset.width):
                return None
            
            elevation = self.dataset.read(1)[row, col]
            
            # nodata 값 처리 (-32768 또는 비정상 값)
            if elevation == self.dataset.nodata or elevation < -100:
                return None
            
            return float(elevation)
        
        except Exception as e:
            return None
    
    def add_elevation_to_linestring(self, geom: LineString) -> LineString:
        """
        LineString의 모든 좌표에 고도 값 추가 (2D -> 3D)
        
        Args:
            geom: LineString (SRID 4326, 2D 또는 3D)
        
        Returns:
            LineString (SRID 4326, 3D with elevation)
        """
        if not geom or geom.empty:
            return geom
        
        coords_3d = []
        dem_data = self.dataset.read(1)
        
        for coord in geom.coords:
            lon, lat = coord[0], coord[1]
            
            try:
                row, col = self.dataset.index(lon, lat)
                if 0 <= row < self.dataset.height and 0 <= col < self.dataset.width:
                    elev = dem_data[row, col]
                    if elev != self.dataset.nodata and elev > -100:
                        coords_3d.append((lon, lat, float(elev)))
                    else:
                        coords_3d.append((lon, lat, 0.0))
                else:
                    coords_3d.append((lon, lat, 0.0))
            except:
                coords_3d.append((lon, lat, 0.0))
        
        return LineString(coords_3d, srid=4326)
    
    def get_elevation_stats(self, geom: LineString) -> dict:
        """
        경로의 고도 통계 계산
        
        Args:
            geom: LineString (SRID 4326)
        
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
        if not geom or geom.empty:
            return None
        
        elevations = []
        dem_data = self.dataset.read(1)
        
        for coord in geom.coords:
            lon, lat = coord[0], coord[1]
            try:
                row, col = self.dataset.index(lon, lat)
                if 0 <= row < self.dataset.height and 0 <= col < self.dataset.width:
                    elev = dem_data[row, col]
                    if elev != self.dataset.nodata and elev > -100:
                        elevations.append(float(elev))
            except:
                continue
        
        if not elevations:
            return None
        
        # 누적 상승/하강 계산
        elevation_gain = 0
        elevation_loss = 0
        for i in range(1, len(elevations)):
            diff = elevations[i] - elevations[i-1]
            if diff > 0:
                elevation_gain += diff
            else:
                elevation_loss += abs(diff)
        
        return {
            'min_elevation': min(elevations),
            'max_elevation': max(elevations),
            'avg_elevation': sum(elevations) / len(elevations),
            'elevation_gain': elevation_gain,
            'elevation_loss': elevation_loss,
            'total_change': elevation_gain + elevation_loss
        }
    
    def estimate_difficulty_level(self, geom: LineString) -> int:
        """
        경로의 난이도 추정 (1: 쉬움, 2: 보통, 3: 어려움)
        
        Args:
            geom: LineString (SRID 4326)
        
        Returns:
            1, 2, 또는 3
        """
        stats = self.get_elevation_stats(geom)
        if not stats:
            return 2
        
        elevation_diff = stats['max_elevation'] - stats['min_elevation']
        total_change = stats['total_change']
        
        # 고도 차이와 누적 변화를 모두 고려
        if elevation_diff < 100 and total_change < 150:
            return 1  # 쉬움
        elif elevation_diff < 300 and total_change < 500:
            return 2  # 보통
        else:
            return 3  # 어려움
    
    def get_elevation_profile(self, geom: LineString, num_samples: int = 100) -> List[dict]:
        """
        경로의 고도 프로파일 생성
        
        Args:
            geom: LineString (SRID 4326)
            num_samples: 샘플링 포인트 수
        
        Returns:
            [{'distance': 거리(m), 'elevation': 고도(m)}, ...]
        """
        if not geom or geom.empty:
            return []
        
        # 경로 길이 계산 (미터)
        length_m = geom.transform(5179, clone=True).length
        
        profile = []
        dem_data = self.dataset.read(1)
        
        for i in range(num_samples):
            # 경로를 따라 균등하게 샘플링
            fraction = i / (num_samples - 1) if num_samples > 1 else 0
            point = geom.interpolate(fraction, normalized=True)
            
            lon, lat = point.x, point.y
            distance = length_m * fraction
            
            try:
                row, col = self.dataset.index(lon, lat)
                if 0 <= row < self.dataset.height and 0 <= col < self.dataset.width:
                    elev = dem_data[row, col]
                    if elev != self.dataset.nodata and elev > -100:
                        profile.append({
                            'distance': round(distance, 1),
                            'elevation': round(float(elev), 1)
                        })
                        continue
            except:
                pass
            
            profile.append({
                'distance': round(distance, 1),
                'elevation': None
            })
        
        return profile
    
    def close(self):
        """DEM 파일 닫기"""
        if self._dataset is not None:
            self._dataset.close()
            self._dataset = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 전역 싱글톤 인스턴스
_dem_instance = None

def get_dem() -> KoreaDEM:
    """DEM 인스턴스 가져오기 (싱글톤)"""
    global _dem_instance
    if _dem_instance is None:
        _dem_instance = KoreaDEM()
    return _dem_instance