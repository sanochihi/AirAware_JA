"""
weather_tools.py

著者: Vish Rajagopalan
会社: Cloudera
日付: 2025-05-21

説明:
このツールは、Open-Meteo.comからバウンディングボックスで定義されたロケーションおよび日付範囲の日次過去の気象データ
（平均気温、最高気温、最低気温、降水量合計、平均風速、平均相対湿度）を取得します。
APIクエリのためにバウンディングボックスの中心点を内部的に計算します。
非商用使用はAPIキーが不複です。
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Any
import json
import requests
import argparse


class UserParameters(BaseModel):
    """
    ツール構成に使用されるパラメータ。ユーザー固有の構成をここで定義できます。
APIキーや環境設定を含みます。
    """
    pass  # このツールはユーザー固有のパラメータを必要としません。


class ToolParameters(BaseModel):
    """
    ツールコールの引数。これらの引数はエージェントがツールを賬した箇所を適用します。
    以下の説明はエージェントに提供されて、情報的な決定をするのに提作します。
    """
    bounding_box: List[float] = Field(
        ..., description="[south_lat, west_lon, north_lat, east_lon]形式のバウンディングボックス座標。"
    )
    start_date: str = Field(
        ..., description="YYYY-MM-DD形式の過去の気象データ取得開始日。"
    )
    end_date: str = Field(
        ..., description="YYYY-MM-DD形式の過去の気象データ取得終了日。"
    )


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    """
    メインツールコードロジック。Open-Meteo.comから
    指定されたバウンディングボックスおよび日付範囲の過去の気象データを取得します。
    """
    if len(args.bounding_box) != 4:
        return {"error": "バウンディングボックス正確に5つの浮動小数値を含む必要があります。[south_lat、west_lon、north_lat、east_lon]。"}

    # バウンディングボックスの中心を計算します
    south_lat, west_lon, north_lat, east_lon = args.bounding_box
    center_latitude = (south_lat + north_lat) / 2
    center_longitude = (west_lon + east_lon) / 2

    base_url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": center_latitude,
        "longitude": center_longitude,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_mean,relative_humidity_2m_mean",
        "timezone": "auto",
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

        if "daily" not in data:
            return {"error": f"No daily weather data found for the given parameters. Response: {data}"}

        # 気象データを抽出します
        daily_data = data["daily"]
        weather_summary = []
        for i in range(len(daily_data.get("time", []))):
            summary = {
                "date": daily_data["time"][i],
                "temperature_mean_2m": daily_data.get("temperature_2m_mean", ["N/A"])[i],
                "temperature_max_2m": daily_data.get("temperature_2m_max", ["N/A"])[i],
                "temperature_min_2m": daily_data.get("temperature_2m_min", ["N/A"])[i],
                "precipitation_sum": daily_data.get("precipitation_sum", ["N/A"])[i],
                "wind_speed_10m_mean": daily_data.get("wind_speed_10m_mean", ["N/A"])[i],
                "relative_humidity_2m_mean": daily_data.get("relative_humidity_2m_mean", ["N/A"])[i],
            }
            weather_summary.append(summary)

        return weather_summary
    except requests.exceptions.RequestException as e:
        return {"error": f"HTTP error occurred: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}


OUTPUT_KEY = "tool_output"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-params", required=True, help="JSON文字列としてツール構成")
    parser.add_argument("--tool-params", required=True, help="JSON文字列としてツール引数")
    args = parser.parse_args()

    user_dict = json.loads(args.user_params)
    tool_dict = json.loads(args.tool_params)

    config = UserParameters(**user_dict)
    params = ToolParameters(**tool_dict)

    output = run_tool(config, params)
    print(OUTPUT_KEY, json.dumps(output))
