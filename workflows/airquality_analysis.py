import os
from typing import List, Optional
from crewai import LLM, Crew, Agent, Task
from agent_tools.bounding_box_extractor_tool import BoundingBoxExtractorTool
from agent_tools.air_quality_analysis_tool import AirQualityAnalysisTool
from agent_tools.weather_tools import HistoricalWeatherTool # HistoricalWeatherToolを含むweather_tools.pyがあると仮定
from agent_tools.utils import get_openai_api_key, get_serper_api_key # 使用している特定の関数をインポート
MODEL_NAME=os.getenv("MODEL_NAME", "openai/gpt-4o-mini")
# LLMの設定
llm = LLM(
    model=MODEL_NAME,  # 使用するプロバイダー/モデル名
    temperature=0.7,  # より詳細な分析のために気温を低めに設定
    max_tokens=1000,  # 包括的なレポートのために最大トークン数を増やす
    top_p=0.9,
    frequency_penalty=0.1,
    presence_penalty=0.1,
    stop=["END"],
    seed=42
)


# APIキーを読み込または安全に管理していることを確認してください
openai_api_key = os.environ.get("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY 環境変数が設定されていません。")

# ツールを初期化してください
bounding_box_extractor_tool = BoundingBoxExtractorTool()
air_quality_tool = AirQualityAnalysisTool()
weather_tool = HistoricalWeatherTool()



def create_air_quality_analysis_crew(locations: List[str], start_date: str, end_date: str, aq_parameters: Optional[List[str]] = None):
# 指定されたロケーションの空気質分析クルーを作戛して実行してください。

    # エージェント1: バウンディングボックス取得者
    bounding_box_retriever = Agent(
        role="地理空間データスペシャリスト",
        goal="指定されたロケーションの境界ボックス座標を取得します。",
        backstory="地理情報検索と空間データ分析の専門家です。",
        verbose=True,
        allow_delegation=False,
        tools=[bounding_box_extractor_tool],
    )

    # タスク1: バウンディングボックスを取得する
    get_bounding_boxes_task = Task(
        description=f"以下の各ロケーション: {locations} について、'bounding_box_extractor'ツールを使用して境界ボックス座標を検索します。各ロケーションに対応する境界ボックスを返します。", 
        agent=bounding_box_retriever,
        expected_output="各指定ロケーションの境界ボックス座標(南、西、北、東)を含む辞書またはリスト。", 
    )

    # エージェント2: 気象情報統合者
    weather_data_integrator = Agent(
        role="過去の気象データスペシャリスト",
        goal="指定されたロケーションと日付の過去の気象要約を取得します。",
        backstory="環境分析に関連する過去の気象データの取得と要約に精通しています。",
        verbose=True,
        allow_delegation=False,
        tools=[weather_tool],
    )

    # タスク2: 気象情報を取得する
    get_weather_data_task = Task(
        description=f"以下の各ロケーション: {locations} について、境界ボックス(南、西、北、東)を使用して気象ツールをクエリし、{start_date}から{end_date}の間の関連する過去の気象条件の簡潔な要約を見つけます。空気質に影響を与える可能性のある主要な気象側面(例: 気温、風、降水量)に焦点を当てます。", 
        agent=weather_data_integrator,
        expected_output="各指定都市の過去の気象条件の簡潔な要約を含む辞書またはリスト。", 
        context=[get_bounding_boxes_task], 
    )

    # エージェント3: 空気質データ取得者
    air_quality_retriever = Agent(
        role="空気質データ取得エージェント",
        goal="指定されたロケーションと日付範囲のOpenAQから空気質データを取得します。",
        backstory="OpenAQデータベースから空気質データを取得することを専門としています。",
        verbose=True,
        allow_delegation=False,
        tools=[air_quality_tool],
    )
    
    # タスク3: 空気質データを取得する
    get_air_quality_data_task = Task(
        description=f"以下のロケーション: {locations} について、{start_date}から{end_date}の期間で各ロケーションの境界ボックスを使用してair_quality_toolを使って空気質データを取得します。特定のパラメータ({aq_parameters})が提供されている場合は、それらに焦点を当てます。データをpandas DataFrameとして返します。", 
        agent=air_quality_retriever,
        expected_output="指定されたロケーション、日付、およびパラメータの空気質データを含むpandas DataFrame。", 
        context=[get_bounding_boxes_task],  # AirQualityAnalysisToolはロケーションを必要とします
    )

    # エージェント4: 空気質分析者
    air_quality_analyst = Agent(
        role="空気質分析家",
        goal="収集した空気質データおよび対応する気象情報を分析し、空気質状況に関する包括的なレポートを生成します。", 
        backstory="大気汚染分析と気象条件との関係を専門とする経験豊富な環境科学者です。", 
        verbose=True,
        allow_delegation=False,
        llm=llm,  # 構成されたLLMを使用
        context=[get_air_quality_data_task] + [get_weather_data_task],
    )

    # タスク4: データを分析してレポートを生成する
    analysis_task = Task(
        description="指定されたロケーションと日付について提供された空気質データ(pm10、value、units、date、locationなどのパラメータを含む)を分析します。同じ期間の過去の気象情報(気温、風、降水、湿度)を考慮してください。空気質のトレンドを特定し、関連する場合は平均値を計算し、気象条件が空気質に与える可能性のある相関や影響について議論します。各都市の空気質状況を要約した詳細なレポートを提供し、主要な調査結果と気象パターンに関連する注目すべき観察を含めます。", 
        agent=air_quality_analyst,
        expected_output="各都市の空気質分析に関する包括的なレポート。トレンド、平均値、および過去の気象条件との潜在的な関係に関する議論を含みます。"
    )


    # Crewを義務づける
    agents = [bounding_box_retriever, weather_data_integrator, air_quality_retriever, air_quality_analyst]
    tasks = [get_bounding_boxes_task, get_weather_data_task, get_air_quality_data_task, analysis_task]


    crew = Crew(
        agents=agents,
        tasks=tasks,
        verbose=True,
    )

    # Crewを実行して分析レポートを取得してください
    report = crew.kickoff()
    return report


# ワークフローをテストするためだけ
# if __name__ == "__main__":
#     locations = ["New Delhi, India", "Chennai, India"]
#     analysis_start_date = "2024-12-31"
#     analysis_end_date = "2025-01-02"
#     parameters_of_interest = ["pm25, pm10"]  # Optional

#     try:
#         analysis_report = create_air_quality_analysis_crew(
#             locations=locations,
#             start_date=analysis_start_date,
#             end_date=analysis_end_date,
#             aq_parameters=parameters_of_interest
#         )
#         print("\n--- Air Quality Analysis Report ---")
#         print(analysis_report)
#     except ValueError as e:
#         print(f"Error: {e}")
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")