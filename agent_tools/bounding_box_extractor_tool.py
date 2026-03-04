from typing import Optional
import requests
from crewai.tools import BaseTool
from math import cos, radians

class BoundingBoxExtractorTool(BaseTool):
    """与えられた位置を中心に訪問を作成するツール。"""

    name: str = "bounding_box_extractor"
    description: str = (
        "給えられた位置のNominatim緊縦緒/粗様を使用し、中心を中心に[North、West、South、East]等として訪問を產出します。"
    )
    parameters: Optional[list[dict]] = [
        {
            "name": "location",
            "type": "string",
            "description": "境界ボックスを取得するロケーションの名前。"
            "required": True,
        },
        {
            "name": "radius_km",
            "type": "number",
            "description": "ロケーション中心からの半径(キロメートル)。"
            "required": False,
        }
    ]
    return_direct: bool = False

    def _create_bbox_from_point(self, lat, lon, radius_km=10):
        """緯度経度と指定した半径(km)を用いて境界ボックスを作成します。"""
        lat_offset = radius_km / 111  # 1度物正一粗約111 km
        lon_offset = radius_km / (111 * cos(radians(lat)))

        return [
            lat - lat_offset,  # 海南
            lon - lon_offset,  # 西
            lat + lat_offset,  # 海北
            lon + lon_offset   # 東
        ]

    def _run(self, location: str, radius_km: int = 10) -> list[str] | str:
        """ツールを実行し、ロケーション中心の周りの境界ボックスを取得します。"""
        url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json&limit=1"
        headers = {"User-Agent": "CrewAI Tool (vishrajagopalan@gmx.com)"}
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                display_name = data[0]['display_name']

                bbox = self._create_bbox_from_point(lat, lon, radius_km=radius_km)

                print(f"Location: {display_name}")
                print(f"Center: lat={lat}, lon={lon}")
                print(f"Generated Bounding Box (±{radius_km}km): {bbox}")
                return bbox
            else:
                return f"Location not found: {location}"
        except requests.exceptions.RequestException as e:
            return f"Error fetching location {location}: {e}"

# ==============================================================================
# BoundingBoxExtractorToolをテストするためのメイン関数
# ==============================================================================
if __name__ == "__main__":
    bbox_tool = BoundingBoxExtractorTool()

    locations_to_test = [
        "Tokyo, Japan",
        "Melbourne, Australia",
        "New York, USA",
        "New Delhi, India"
    ]

    print("--- Starting BoundingBoxExtractorTool Test ---")
    for location in locations_to_test:
        print(f"\n>>> Testing with location: '{location}'")
        try:
            result = bbox_tool._run(location=location, radius_km=15)  # 15km半径
            print(f"<<< Result for '{location}': {result}")
        except Exception as e:
            print(f"Error for '{location}': {e}")
    print("\n--- Test complete ---")
