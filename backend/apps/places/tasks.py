from .services import fetch_kcisa_places, save_kcisa_to_place
from .services import fetch_ktour_places, save_ktour_to_place

def update_all_places():
    # KCISA
    kcisa_rows = fetch_kcisa_places()
    save_kcisa_to_place(kcisa_rows)

    # 한국관광공사
    kto_rows = fetch_ktour_places()
    save_ktour_to_place(kto_rows)