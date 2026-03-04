import os
from crewai import LLM, Crew, Agent, Task
from agent_tools.bounding_box_extractor_tool import BoundingBoxExtractorTool
from agent_tools.air_quality_analysis_tool import AirQualityAnalysisTool
from agent_tools.weather_tools import HistoricalWeatherTool
from agent_tools.input_parser_tool import InputParserTool 

MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")


class AirQualityAnalysisCrew:
    """空気質分析ワークフローのクラスベースの実装。"""

    def __init__(self, user_input: str):
        self.user_input = user_input
        self.llm = self._configure_llm()
        self.tools = self._initialize_tools()
        self.agents = {}
        self.tasks = {}
        self.crew = None

        self._setup_agents()
        self._setup_tasks()
        self._initialize_crew()

    @staticmethod
    def _configure_llm() -> LLM:
        """LLMを設定して返します。"""
        return LLM(
            model=MODEL_NAME,
            temperature=0.7,
            max_tokens=1000,
            top_p=0.9,
            frequency_penalty=0.1,
            presence_penalty=0.1,
            stop=["END"],
            seed=42,
        )

    @staticmethod
    def _initialize_tools():
        """ツールを初期化して返します。"""
        return {
            "input_parser_tool": InputParserTool(),
            "bounding_box_extractor_tool": BoundingBoxExtractorTool(),
            "air_quality_tool": AirQualityAnalysisTool(),
            "weather_tool": HistoricalWeatherTool(),
        }

# ラボ作業: ラボガイドから詳細を入力してください
    def _setup_agents(self):
        """すべてのエージェントをセットアップします。"""
        # ステップ1: エージェントを個別に定義
            role="", # ラボ作業: ラボガイドから詳細を入力してください
            goal="", # ラボ作業: ラボガイドから詳細を入力してください
            backstory="", # ラボ作業: 詳細を入力してください
            verbose=True,
            allow_delegation=False,
            tools=[self.tools[""]], # ラボ作業: 詳細を入力してください
        )
        bounding_box_retriever = Agent(
            role="", # ラボ作業: ラボガイドから詳細を入力してください
            goal="", # ラボ作業: ラボガイドから詳細を入力してください
            backstory="", # ラボ作業: ラボガイドから詳細を入力してください
            verbose=True,
            allow_delegation=False,
            tools=[self.tools[""]], # ラボ作業: ラボガイドから詳細を入力してください
        )
        weather_data_integrator = Agent(
            role="過去の気象データスペシャリスト",
            goal="指定されたロケーション日付の過去の気象要約を取得します。",
            backstory="過去の気象学的データ分析の専門家。",
            verbose=True,
            allow_delegation=False,
            tools=[self.tools["weather_tool"]],
        )
        air_quality_retriever = Agent(
            role="空気質データ取得エージェント",
            goal="指定されたロケーション日付範囲についてOpenAQから空気質データを取得するアシスタント。",
            backstory="空気質データ取得の経験が豊富で、複数の汚染物質データポイント(PM2.5、PM10、NO2、O3など)の取得に特化しています。",
            verbose=True,
            allow_delegation=False,
            tools=[
                self.tools["bounding_box_extractor_tool"],
                self.tools["air_quality_tool"]
    ],
        )
        air_quality_analyst = Agent(
            role="空気質分析家",
            goal="空気質データおよび過去の気象データを分析してレポートを生成します。",
            backstory="空気質分析および気象学的研究の経験があります。",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
        )

        # ステップ2: エージェントをself.agentsに追加
        self.agents = {
            "input_parser_agent": input_parser_agent,
            "bounding_box_retriever": bounding_box_retriever,
            "weather_data_integrator": weather_data_integrator,
            "air_quality_retriever": air_quality_retriever,
            "air_quality_analyst": air_quality_analyst,
        }

    def _setup_tasks(self):
        """すべてのタスクをセットアップします。"""
        # ステップ1: タスクを個別に定義
        parse_user_input_task = Task(
            description=f"", # ラボ作業: ラボガイドから詳細を入力してください,
            agent=self.agents[""], # ラボ作業: ラボガイドから詳細を入力してください,
            expected_output=(
                "" # ラボ作業: ラボガイドから詳細を入力してください,
            ),
        )
        get_bounding_boxes_task = Task(
            description="",# ラボ作業: ラボガイドから詳細を入力してください,
            agent=self.agents[""], # ラボ作業: ラボガイドから詳細を入力してください,
            expected_output="", # ラボ作業: ラボガイドから詳細を入力してください,
            context=[parse_user_input_task],
        )
        get_weather_data_task = Task(
            description="各ロケーションについて、境界ボックス(南、西、北、東)とこ〉文中の開始日付と終了日付を使用して、気象ツールをクエリして、提供された開始日付と終了日付の間の過去の気象条件の簡潈を検索します。空気質に影響を与える円帽気象側面(気温、風、降水を中心に焦を当てます。",
            agent=self.agents["weather_data_integrator"],
            expected_output="指定された各ロケーションの過去の気象条件の集計を含む辞書またはリスト。",
            context=[parse_user_input_task, get_bounding_boxes_task],
        )
        get_air_quality_data_task = Task(
            description="air_quality_toolを使用して、各ロケーション(開始日付から終了日付まで)の空気質データを取得します。各ロケーションの境界ボックスのみを使用してください。aq_parametersアトリブュートによって特定のパラメータが提供されている場合、それらに焦を当ててください。データをpandas DataFrameとして返します。",
            agent=self.agents["air_quality_retriever"],
            expected_output="指定されたロケーション、日付、およびパラメータの空気質データを含むpandas DataFrame。",
            context=[parse_user_input_task, get_bounding_boxes_task],
        )
        analysis_task = Task(
            description="提供された空気質データ(pm10、value、units、date、locationなどのパラメータを含む)を、指定されたロケーションおよび日付について分析します。候一一触的な過去の気象情報(気温、風、降水、湿度)を考慣してください。空気質のトレンドを特定し、関連する場合を平均値を計算し、気象条件が空気質に与えりうる相関またはや影響を議論してください。各ロケーションの空気質状況を要約した詳細なレポートを提供し、主な調査結果と気象パターンに関逼した注目すべき観察を含めてください。提供されたロケーションを比較するための事実と観察を含め、總合的な空気質について話をてくための信頻できる知識ㄞソースを含めてください。",
            agent=self.agents["air_quality_analyst"],
            expected_output="各ロケーションの空気質分析に鉤て包括的なレポート。トレンド、平均値、しく及び過去の気象条件との佋的な関係についてのḭ声を含います。策刷に要約を何齢、結論を醵孔を含める。",
            context=[get_air_quality_data_task, get_weather_data_task],
        )

        # ステップ2: タスクをself.tasksに追加
        self.tasks = {
            "parse_user_input_task": parse_user_input_task,
            "get_bounding_boxes_task": get_bounding_boxes_task,
            "get_weather_data_task": get_weather_data_task,
            "get_air_quality_data_task": get_air_quality_data_task,
            "analysis_task": analysis_task,
        
    }

    def _initialize_crew(self):
        """クルーを初期化してエージェント、タスクを設定します。"""
        self.crew = Crew(
            agents=list(self.agents.values()),
            tasks=list(self.tasks.values()),
            verbose=True,
        )

    def execute(self):
        """ワークフローを実行し、レポートを返します。"""
        return self.crew.kickoff()


# テスト用
import argparse

# テスト用
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ユーザー入力に基づいて空気質分析を実行します。")
    parser.add_argument(
        "--user-input",
        help="空気質分析のための自然言語クエリィ。例: 'ニューデリーとチョンナィの2025年1月1日かで1月3日までの空気質を分析し、PM2.5とPM10に焼点を当ててください。'",
    )
    args = parser.parse_args()

    # 入力がない場合のデフォルト値
    user_query = args.user_input or "ニューデリーとチェンナイの2025年1月1日から1月3日までの空気質を分析し、PM2.5とPM10に焦点を当ててください。"

    try:
        analysis_crew = AirQualityAnalysisCrew(user_input=user_query)
        report = analysis_crew.execute()
        print("\n--- 空気質分析レポート ---")
        print(report)
    except ValueError as e:
        print(f"エラー: {e}")
    except Exception as e:
        print(f"予返しないエラーが発しました: {e}")
