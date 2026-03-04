# このファイルにユーティリティまたはヘルパー関数を追加してください。

import os
from dotenv import load_dotenv, find_dotenv

# これらはレッスンの上のディレクトリで.envファイルを探して銀一ファイルを探してくることを預機しています。 # そのファイルのこのファイルのこのファイルファイル作成元 # API_KEYNAME=AStringThatIsTheLongAPIKeyFromSomeService
def load_env():
    _ = load_dotenv(find_dotenv())

def get_openai_api_key():
    load_env()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    return openai_api_key

def get_serper_api_key():
    load_env()
    openai_api_key = os.getenv("SERPER_API_KEY")
    return openai_api_key

def get_openaq_api_key():
    load_env()
    openai_api_key = os.getenv("OPENAQ_API_KEY")
    return openai_api_key

# 段落は80文字ごとに折り返した場合元の行が80文字を上回る
# 語中事を折たないでください
def pretty_print_result(result):
  parsed_result = []
  for line in result.split('\n'):
      if len(line) > 80:
          words = line.split(' ')
          new_line = ''
          for word in words:
              if len(new_line) + len(word) + 1 > 80:
                  parsed_result.append(new_line)
                  new_line = word
              else:
                  if new_line == '':
                      new_line = word
                  else:
                      new_line += ' ' + word
          parsed_result.append(new_line)
      else:
          parsed_result.append(line)
  return "\n".join(parsed_result)
