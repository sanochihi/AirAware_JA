"""
Bounding Box Extractor Tool

著者: Vish Rajagopalan
会社: Cloudera
日付: 2025-05-21

説明:
このツールは、Nominatim OpenStreetMap APIをクエリして、指定されたロケーション名の
地理的境界ボックス座標(南、北、西、東)を取得します。
"""
"""
Bounding Box Extractor Tool

著者: Vish Rajagopalan
会社: Cloudera
日付: 2025-05-21

説明:
このツールは、Nominatimを使用して中心座標を取得し、指定されたロケーション名の
都市中心周辺のカスタム地理的境界ボックスを返します。
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
import json
import argparse
import requests
from math import cos, radians


class UserParameters(BaseModel):
    """ツールの構成に使用されるパラメータ。APIキーやユーザーエージェントなどを含む場合があります。"""
    pass


class ToolParameters(BaseModel):
    """エージェントからツールに渡される引数。"""
    location: str = Field(description="境界ボックスを取得するロケーションの名前。")
    radius_km: Optional[float] = Field(default=15, description="都市中心周辺の境界ボックスの半径(km)。")


class BoundingBoxExtractor:
    @staticmethod
    def create_bbox_from_center(lat, lon, radius_km=15):
        """緯度/経度と指定半径(km)から境界ボックスを作成します。"""
        lat_offset = radius_km / 111  # 1度物正一粗約111 km
        lon_offset = radius_km / (111 * cos(radians(lat)))  # 緯度を作拫長で調整

        return [
            lat - lat_offset,  # 海南
            lon - lon_offset,  # 西
            lat + lat_offset,  # 海北
            lon + lon_offset   # 東
        ]

    @staticmethod
    def run_tool(config: UserParameters, args: ToolParameters) -> Any:
        """都市中心周辺の境界ボックスを生成します。"""
        url = f"https://nominatim.openstreetmap.org/search?q={args.location}&format=json&limit=1"
        headers = {"User-Agent": "AirAware Data For Good (vishrajagopalan@gmx.com)"}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                display_name = data[0]['display_name']

                bbox = BoundingBoxExtractor.create_bbox_from_center(lat, lon, radius_km=args.radius_km)
                return {
                    "location": display_name,
                    "center": {"lat": lat, "lon": lon},
                    "radius_km": args.radius_km,
                    "bounding_box": bbox
                }
            else:
                return {"error": f"Location not found: {args.location}"}

        except requests.exceptions.RequestException as e:
            return {"error": f"Error fetching location {args.location}: {e}"}


OUTPUT_KEY = "tool_output"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-params", required=True, help="ツール構成")
    parser.add_argument("--tool-params", required=True, help="ツール引数")
    args = parser.parse_args()

    # JSON を辞書に解析してください
    user_dict = json.loads(args.user_params)
    tool_dict = json.loads(args.tool_params)

    # Pydantic モデルに辞書を検証してください
    config = UserParameters(**user_dict)
    params = ToolParameters(**tool_dict)

    # ツールを実行してください
    output = BoundingBoxExtractor.run_tool(config, params)
    print(OUTPUT_KEY, output)
