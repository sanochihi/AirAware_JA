"""
air_quality_analysis_tool.py

著者: Vish Rajagopalan
会社: Cloudera
日付: 2025-05-21

説明:
このモジュールは、AirQualityAnalysisToolを定義します。これは、OpenAQ API、AWS S3
OpenAQデータアーカイブ、および地理的検索用の内部BoundingBoxExtractorToolを組み合わせて
使用して、指定されたロケーションと日付の空気質データを取得し、集計するために設計されています。
"""

from typing import Optional, List, Type
from datetime import datetime, date
import requests
import pandas as pd
import gzip
import os

from crewai.tools import BaseTool
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from .bounding_box_extractor_tool import BoundingBoxExtractorTool # 同じパッケージ内にある場合の通常インポート
# ユーティルスファイルからゲット_openaq_api_key関数をインポート
from .utils import get_openaq_api_key
from typing import List, Optional
anonymous_session = boto3.Session()  # 公开バケット用

class AirQualityAnalysisTool(BaseTool):
    name: str = "air_quality_analysis"
    description: str = "指定されたロケーションと日時の空気質データを取得し、集計した結果を返します。"
    parameters: Optional[List[dict]] = [
        {
            "name": "bounding_boxes",
            "type": "list[list[float]]",
            "description": (
                "List of bounding boxes with each box as a List of coordinates each represented as a flat list of four float values  [West,  South, East, North] to analyze air quality. Example: [[-34.3, 150.0, -33.2, 151.5], [...]]"
            ),
            "required": True,
        },      
        {
            "name": "locations",
            "type": "list[str]",
            "description": "空気質を分析するロケーション名のリスト。"
            "required": True,
        },          
        {
            "name": "start_date",
            "type": "str",
            "description": "分析の開始日（YYYY-MM-DD形式）。"
            "required": True,
        },
        {
            "name": "end_date",
            "type": "str",
            "description": "分析の終了日（YYYY-MM-DD形式）。"
            "required": True,
        },
        {
            "name": "aq_parameters",
            "type": "Optional[list[str]]",
            "description": "フィルタする空気質パラメータのオプションリスト（例: ['pm25','o3']）。Noneの場合は利用可能なすべてのパラメータが使用されます。"
            "required": False,
        },
    ]
    def _run(self, bounding_boxes: List[List[float]], locations: List[str], start_date: str, end_date: str, aq_parameters: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Args:
            bounding_boxes (list): 各ボックスが座標リスト[West, South, East, North]で表された境界ボックスのリスト。
            locations (list): 境界ボックスに対応するロケーション名のリスト。
            start_date (str): YYYY-MM-DD形式の分析開始日。
            end_date (str): YYYY-MM-DD形式の分析終了日。
            aq_parameters (list, optional): フィルタする空気質パラメータのリスト。省略時はすべての利用可能なパラメータを使用。

        Returns:
            pd.DataFrame: [date, parameter, unit, value, location_name]列を持つ集約された空気質データ。
        """
        

        # 開始日時と終了日時文字列を日時オブジェクトに変換
        try:
            start_date_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Please use YYYY-MM-DD.")

        # ステップ2: OpenAQからロケーションIDを取得
        def get_location_ids(bbox: List[str]) -> List[dict]:
            URL = "https://api.openaq.org/v3/locations?limit=100&page=1&order_by=id&sort_order=asc"
            params = {
                "bbox": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            }
            headers = {"X-API-Key": get_openaq_api_key()}
            print( f"DEBUG : \n params : {params}, \n headers : {headers}")
            response = requests.get(URL, headers=headers, params=params)
            response.raise_for_status()
            print("Debug : Response Location Details : ", response.json())
            return response.json().get("results", [])

        # ステップ3: boto3を使用してOpenAQ AWSバケットからデータを取得
        def fetch_sensor_data(location_ids: List[int], start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame: # 型ヒントを更新
            consolidated_df = pd.DataFrame()
            failed_locations = []  # データを設定できないロケーションを追追

            s3_client = anonymous_session.client('s3', region_name="us-east-1", config=Config(signature_version=UNSIGNED))
            source_bucket_name = "openaq-data-archive"

            for location_id in location_ids:
                for date in pd.date_range(start=start_date, end=end_date):
                    year, month, day = date.strftime("%Y"), date.strftime("%m"), date.strftime("%d")
                    prefix = f"records/csv.gz/locationid={location_id}/year={year}/month={month}/"
                    try:
                        response = s3_client.list_objects_v2(Bucket=source_bucket_name, Prefix=prefix)
                        if 'Contents' in response:
                            for obj in response['Contents']:
                                key = obj['Key']
                                if key.endswith(f"{year}{month}{day}.csv.gz"):
                                    print(f"Downloading: {key}")
                                    obj_data = s3_client.get_object(Bucket=source_bucket_name, Key=key)
                                    with gzip.GzipFile(fileobj=obj_data['Body']) as gz_file:
                                        daily_df = pd.read_csv(gz_file)
                                        consolidated_df = pd.concat([consolidated_df, daily_df], ignore_index=True)
                        else:
                            failed_locations.append(location_id)

                    except Exception as e:
                        print(f"Error fetching data for location ID {location_id}: {e}")
                        failed_locations.append(location_id)
            print("Sample Sensor Data from OPENAQ : \n", consolidated_df.head())
            if failed_locations:
                print(f"Locations with no data or errors: {failed_locations}")

            return consolidated_df

        # ステップ4: データを集約
        def aggregate_data(df: pd.DataFrame, parameters: Optional[List[str]] = None) -> pd.DataFrame:
            df['datetime'] = pd.to_datetime(df['datetime'])  # 日時値が正しく解析されることを確認
            df = df.set_index('datetime')  # インデックスとして'datetime'を設定

            if parameters:
                df = df[df['parameter'].isin(parameters)]  
            try : 
                # 'parameter'との競合を利けるため、インデックスをリセット
                df = df.reset_index()     
                print("DF :\n ", df.head())           
                daily_data = (
                    df.groupby(['parameter', pd.Grouper(key='datetime', freq='D')])
                    .agg(
                        value=('value', 'mean'),
                        units=('units', 'first')
                    )
                    .dropna()
                    .reset_index()
                )  
            except Exception as e : 
                print("Aggregation failed with Exception: ", e)
            daily_data['date'] = daily_data['datetime'].dt.date
            del daily_data['datetime']
            return daily_data

        # メインワークフロー
        all_data = []
        for bbox, location in zip(bounding_boxes, locations):
            try:
                bbox_openaq_format  = [bbox[1], bbox[0], bbox[3], bbox[2]]  
                print("FORMAT OF BBOX FOR OPENAQ: ", bbox_openaq_format)       
                location_data = get_location_ids(bbox_openaq_format)
                location_ids = [loc['id'] for loc in location_data]
                # Open AQはバウンディングボックスをwest, south, east, north形式で受け付ける

                print(f"Found {len(location_ids)} locations for bounding box (per openAQ format) {bbox_openaq_format} (Location: {location}). Downloading data...")

                consolidated_df = fetch_sensor_data(location_ids, start_date_dt, end_date_dt)
                if not consolidated_df.empty:               
                    aggregated_daily_data = aggregate_data(consolidated_df, aq_parameters)
                    aggregated_daily_data["location"] = location  # ロケーション列を追加
                    all_data.append(aggregated_daily_data)

            except Exception as e:
                print(f"Error processing bounding box {bbox} for location {location}: {e}")

        # すべてのデータを統合
        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            return result
        else:
            return pd.DataFrame(columns=["date", "parameter", "unit", "value", "location"])
        

tool = BoundingBoxExtractorTool()

if __name__ == '__main__':
    # 使用例:
    analysis_tool = AirQualityAnalysisTool()
    locations_to_analyze = [ "Sydney", "Singapore"]
    parameters_to_analyze=["pm25"]
    bboxes=[]
    for location in locations_to_analyze : 
        bbox = tool.run(location=location)
        print(  "Bounding box : ", bbox)
        bboxes.append(bbox)


    start = "2025-01-01"
    end = "2025-01-03"
    parameters_to_analyze = ["pm25"]

    try:
        
        results_df = analysis_tool.run(bounding_boxes = bboxes,locations=locations_to_analyze, start_date=start, end_date=end, aq_parameters=parameters_to_analyze)

        print("\nAggregated Air Quality Data:")
        print(results_df)
    except Exception as e:
        print(f"An error occurred during analysis: {e}")

