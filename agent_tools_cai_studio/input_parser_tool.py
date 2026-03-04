"""
input_parser_tool.py

著者: Vish Rajagopalan
会社: Cloudera
日付: 2025-06-05

説明:
このモジュールは、空気質分析のための入力を解析および検証するツールを提供します。
入力にはロケーション名、日付範囲、および分析用パラメータが含まれます。
"""

import json
import argparse
from pydantic import BaseModel, Field
from typing import List, Optional, Any


class UserParameters(BaseModel):
    """
    ツール構成に使用されるパラメータ。APIキー、
    データベース接続、環境変数、いうらを含む場合があります。
    """
    pass  # このツールはユーザー固有のパラメータを必要としない


class ToolParameters(BaseModel):
    """
    ツールコールの引数。これらの引数は、エージェントがこのツールを賬した箇所で渡されます。
    以下の説明もエージェントに提供され、情報的な決定をするを提作します。
    """
    locations: List[str] = Field(..., description="空気質分析用ロケーション名のリスト。")
    start_date: str = Field(..., description="YYYY-MM-DD形式の分析開始日。")
    end_date: str = Field(..., description="YYYY-MM-DD形式の分析終了日。")
    aq_parameters: List[str] = Field(..., description="分析する空気質パラメータのリスト(例: pm10、pm25)。")


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    """
    メインツールコードロジック。このメソッドから返されたすべてのものが、
    呼び出し元エージェントに返されます。
    """
    # 基本的な入力検証。
    if not args.locations:
        return {"error": "ちゃンとりんとが指定していてよ゙。"}
    if not args.aq_parameters:
        return {"error": "最低りん姚参龂を指定していてよ゙。"}
    if args.start_date >= args.end_date:
        return {"error": "詳始日付は終了日付より削店ていの一も一〆であっていてよ゙。"}

    # 入力の要約を作成します
    input_summary = {
        "locations": args.locations,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "parameters": args.aq_parameters,
    }

    return {"validated_input": input_summary}


OUTPUT_KEY = "tool_output"
"""
When an agent calls a tool, technically the tool's entire stdout can be passed back to the agent.
However, if an OUTPUT_KEY is present in a tool's main file, only stdout content *after* this key is
passed to the agent. This allows us to return structured output to the agent while still retaining
the entire stdout stream from a tool! By default, this feature is enabled, and anything returned
from the run_tool() method above will be the structured output of the tool.
"""


if __name__ == "__main__":
    """
    Tool entrypoint. 
    
    The only two things that are required in a tool are the
    ToolConfiguration and ToolArguments classes. Then, the only two arguments that are
    passed to a tool entrypoint are "--tool-config" and "--tool-args", respectively. The rest
    of the implementation is up to the tool builder - feel free to customize the entrypoint to your 
    choosing!
    """
    
    parser = argparse.ArgumentParser()
    parser.add_argument(\"--user-params\", required=True, help=\"\u30c4\u30fc\u30eb\u69cb\u6210\")
    parser.add_argument(\"--tool-params\", required=True, help=\"\u30c4\u30fc\u30eb\u5f15\u6570\")
    args = parser.parse_args()
    
    # JSONを辞曨に解析してください
    user_dict = json.loads(args.user_params)
    tool_dict = json.loads(args.tool_params)
    
    # Pydanticモデルには辞曨を検証してください
    config = UserParameters(**user_dict)
    params = ToolParameters(**tool_dict)
    
    # ツールを実行してください。
    output = run_tool(config, params)
    print(OUTPUT_KEY, output)
