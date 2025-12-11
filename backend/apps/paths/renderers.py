import io
import requests
import polyline
from shapely.geometry import LineString
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from PIL import Image, ImageDraw
from .utils import GisUtils  
from django.conf import settings

CONFIG = settings.THUMBNAIL_RENDER_CONFIG

def render_with_naver_api(path_obj) -> io.BytesIO:
    
    """
    네이버 Static Map API를 호출하여 경로 이미지를 가져오고 BytesIO로 반환
    """
    if not path_obj.geom:
        raise ValueError("Path object must have geometry data.")
    
    naver_cfg = CONFIG['NAVER']
    LINE_WIDTH = CONFIG.get('LINE_WIDTH', 3)

    # 좌표 인코딩
    coords_list = [(c[1], c[0]) for c in path_obj.geom.coords]  # (lng, lat) -> (lat, lng)
    encoded_path = polyline.encode(coords_list)

    center_lng, center_lat, zoom_level = GisUtils.calculate_map_center_and_zoom(path_obj.geom)

    params = {
        'path': f"weight:{LINE_WIDTH}|color:{CONFIG['LINE_COLOR']}|enc:{encoded_path}",
        'center': f"{center_lng},{center_lat}",
        'w': CONFIG['IMAGE_WIDTH'],
        'h': CONFIG['IMAGE_HEIGHT'],
        'level': zoom_level,
        'maptype': naver_cfg['MAP_TYPE'],
        'scale': naver_cfg['SCALE'],
    }

    headers = {
        'X-NCP-APIGW-API-KEY-ID': naver_cfg['CLIENT_ID'],
        'X-NCP-APIGW-API-KEY': naver_cfg['CLIENT_SECRET'],
    }

    res = requests.get(naver_cfg['API_URL'], params=params, headers=headers, timeout=10)
    res.raise_for_status()
    img_data = io.BytesIO(res.content)
    return img_data


def render_with_contextily(path_obj) -> io.BytesIO:
    """
    Contextily를 사용하여 경로와 지도 배경 렌더링
    """
    if not path_obj.geom:
        raise ValueError("Path object must have geometry data.")

    ctx_cfg = CONFIG['CONTEXTILY']
    IMAGE_WIDTH = CONFIG['IMAGE_WIDTH']
    IMAGE_HEIGHT = CONFIG['IMAGE_HEIGHT']
    LINE_COLOR_HEX = CONFIG['LINE_COLOR_HEX']
    LINE_WIDTH = ctx_cfg.get('LINE_WIDTH', 3)
    DPI = ctx_cfg.get('DPI', 100)
    MIN_MAP_EXTENT = ctx_cfg.get('MIN_MAP_EXTENT', 2000)
    PADDING_RATIO = ctx_cfg.get('PADDING_RATIO', 0.2)

    # 3D -> 2D
    geom_2d = LineString([(pt[0], pt[1]) for pt in path_obj.geom.coords])
    gdf = gpd.GeoDataFrame([{'id': path_obj.id}], geometry=[geom_2d], crs="EPSG:4326")
    gdf_web = gdf.to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(IMAGE_WIDTH / DPI, IMAGE_HEIGHT / DPI), dpi=DPI, frameon=False)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    gdf_web.plot(ax=ax, linewidth=LINE_WIDTH, color=LINE_COLOR_HEX, zorder=2)
    ax.set_axis_off()

    # 지도 영역 계산
    xmin, ymin, xmax, ymax = gdf_web.total_bounds
    data_width = xmax - xmin
    data_height = ymax - ymin
    center_x = (xmin + xmax) / 2
    center_y = (ymin + ymax) / 2

    map_width = max(data_width, MIN_MAP_EXTENT) * (1 + 2 * PADDING_RATIO)
    map_height = max(data_height, MIN_MAP_EXTENT) * (1 + 2 * PADDING_RATIO)

    target_aspect = IMAGE_WIDTH / IMAGE_HEIGHT
    current_aspect = map_width / map_height

    if current_aspect > target_aspect:
        map_height = map_width / target_aspect
    else:
        map_width = map_height * target_aspect

    final_xmin = center_x - map_width / 2
    final_xmax = center_x + map_width / 2
    final_ymin = center_y - map_height / 2
    final_ymax = center_y + map_height / 2

    ax.set_xlim(final_xmin, final_xmax)
    ax.set_ylim(final_ymin, final_ymax)
    ax.set_aspect('equal')

    # 배경 지도
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs=gdf_web.crs.to_string(), zorder=1)

    out = io.BytesIO()
    plt.savefig(out, format='png', dpi=DPI, pad_inches=0)
    plt.close(fig)
    out.seek(0)
    return out


def render_polyline_on_static_map(static_map_img: io.BytesIO, path_coords, center_lat, center_lng, zoom):
    """
    Static Map 이미지 위에 polyline을 그림
    """
    img = Image.open(static_map_img).convert("RGBA")
    draw = ImageDraw.Draw(img)

    img_w, img_h = CONFIG['IMAGE_WIDTH'], CONFIG['IMAGE_HEIGHT']
    line_color = CONFIG['LINE_COLOR_HEX']

    pixel_coords = [
        GisUtils.latlng_to_pixel(lat, lng, center_lat, center_lng, zoom, img_w, img_h)
        for lat, lng in path_coords
    ]
    draw.line(pixel_coords, fill=line_color, width=7)

    out = io.BytesIO()
    img.save(out, format="PNG")
    out.seek(0)
    return out
