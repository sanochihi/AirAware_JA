"""
weather_tools.py

著者: Vish Rajagopalan
会社: Cloudera
日付: 2025-05-21

説明:
このモジュールは、過去の気象データを取得するためのツールを提供します。
気象ツール入力用のModelクラスを含め、
訪問と日付範囲に基づいてOpen-Meteo.comから日醱過去の気象情報を取得します。
"""

from typing import Type
import requests
from pydantic import BaseModel, Field
from crewai.tools import BaseTool 
from typing import List, Optional



class OpenMeteoWeatherInput(BaseModel):
    """バウンディングボックスを使用したOpenMeteoHistoricalWeatherToolの入力。"""
    # バウンディングボックス形式: [south_latitude, west_longitude, north_latitude, east_longitude]
    bounding_box: List[float] = Field(..., description="[south_lat, west_lon, north_lat, east_lon]形式のバウンディングボックス座標。")
    start_date: str = Field(..., description="過去の気象データ取得開始日（YYYY-MM-DD形式）。")
    end_date: str = Field(..., description="過去の気象データ取得終了日（YYYY-MM-DD形式）。")

# バウンディングボックス(箜)は三捕の作成元で定義された矩形領域でいて:
# 三種を代表しているかな(最小経度, 最小緯度)と
# 二を代表しているかな(最大経度, 最大緯度)。
# これは本質的に、地図上またはデータセット内で地理的範囲を定義する停止。 

class HistoricalWeatherTool(BaseTool):
    """バウンディングボックスと日付範囲で定義された場所の
    日次過去の気象データ(平均気温、最高/最低気温、降水量合計、
    平均風速、平均相対湿度)をOpen-Meteo.comから取得します。ツールは
    内部的にバウンディングボックスの中心点をAPIクエリ用に計算します。"""
    name: str = "HistoricalWeatherTool"
    description: str = (
        "訪問と日付範囲からOpen-Meteo.com(非蔵利使用はAPIキー不要)を使用して、
        日醱的な過去の気象情報(平均気温、最高気温、最低気温、
        降水量種、平均風速、举賛湿度)を取得します。
        ツールはAPIクエリのために内部的に訪問の中心点を計算します。"
    )
    args_schema: Type[BaseModel] = OpenMeteoWeatherInput

    def _run(self, bounding_box: List[float], start_date: str, end_date: str) -> str:
        if len(bounding_box) != 4:
            return "Error: Bounding box must contain exactly 4 float values: [south_lat, west_lon, north_lat, east_lon]."

        # バウンディングボックスは[south_lat, west_lon, north_lat, east_lon]形式
        south_lat, west_lon, north_lat, east_lon = bounding_box[0], bounding_box[1], bounding_box[2], bounding_box[3]
        
        # バウンディングボックスの中後を計算
        center_latitude = (south_lat + north_lat) / 2
        center_longitude = (west_lon + east_lon) / 2

        base_url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": center_latitude,
            "longitude": center_longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_mean,relative_humidity_2m_mean",
            "timezone": "auto" # 日常統計データに対してタイムゾーンを指定することをお勧めします
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # HTTPエラーを起取る
            data = response.json()

            if "daily" not in data:
                return f"No daily weather data found for the bounding box {bounding_box} between {start_date} and {end_date}. API response: {data}"

            daily_data = data["daily"]
            times = daily_data.get("time", [])
            temp_means = daily_data.get("temperature_2m_mean", [])
            temp_maxs = daily_data.get("temperature_2m_max", [])
            temp_mins = daily_data.get("temperature_2m_min", [])
            precipitations = daily_data.get("precipitation_sum", [])
            wind_speeds_mean = daily_data.get("wind_speed_10m_mean", [])
            humidities_mean = daily_data.get("relative_humidity_2m_mean", [])

            weather_summary = []
            for i in range(len(times)):
                summary = {
                    "date": times[i],
                    "temperature_mean_2m": temp_means[i] if i < len(temp_means) else "N/A",
                    "temperature_max_2m": temp_maxs[i] if i < len(temp_maxs) else "N/A",
                    "temperature_min_2m": temp_mins[i] if i < len(temp_mins) else "N/A",
                    "precipitation_sum": precipitations[i] if i < len(precipitations) else "N/A",
                    "wind_speed_10m_mean": wind_speeds_mean[i] if i < len(wind_speeds_mean) else "N/A",
                    "relative_humidity_2m_mean": humidities_mean[i] if i < len(humidities_mean) else "N/A"
                }
                weather_summary.append(summary)

            return str(weather_summary) # LLM処理のために文字列として返す
        except requests.exceptions.RequestException as e:
            return f"Error fetching weather data from Open-Meteo for bounding box {bounding_box}: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"
        
# テストのみ用
# from bounding_box_extractor_tool import BoundingBoxExtractorTool
# def main(location: str, start_date: str, end_date: str):
#     """
#     ロケーションのバウンディングボックスを取得し、後に歴史的な気象裕を取得するメイン関数。

#     Args:
#         location (str): ロケーション名。
#         start_date (str): YYYY-MM-DD形式の探気料開始日。
#         end_date (str): YYYY-MM-DD形式の探気料終了日。
#     """
#     bbox_extractor = BoundingBoxExtractorTool()
#     weather_tool = HistoricalWeatherTool()

#     print(f"Getting bounding box for {location}...")
#     bounding_box = bbox_extractor.run(location=location)

#     if isinstance(bounding_box, str):
#         print(f"Error: {bounding_box}")
#         return

#     print(f"Bounding box for {location}: {bounding_box}")
#     print(f"Fetching weather details for {location} from {start_date} to {end_date}...")
#     weather_details = weather_tool.run(bounding_box=bounding_box, start_date=start_date, end_date=end_date)
    
#     print("\nWeather Details:")
#     print(weather_details)

# if __name__ == "__main__":
#     # 使用例:
#     location_name = "Tokyo"
#     start = "2025-01-01"
#     end = "2025-01-03"
#     main(location_name, start, end)

#     print("\n" + "="*50 + "\n")

#     location_name = "London"
#     start = "2025-01-01"
#     end = "2025-01-03"
#     main(location_name, start, end)
    
#     print("\n" + "="*50 + "\n")

#     location_name = "Frankfurt"
#     start = "2025-01-01"
#     end = "2025-01-03"
#     main(location_name, start, end)
    
    
#     location_name = "Chennai"
#     start = "2025-01-01"
#     end = "2025-01-03"
#     main(location_name, start, end)
    
#     location_name = "New Delhi, India"
#     start = "2025-01-01"
#     end = "2025-01-03"
#     main(location_name, start, end)