## 勉強会資料

AIエージェント作成8.pptx

## 制限事項

動かすためには以下のキーの入手が必要です

OPEN_API_KEY
TAVILY_KEY

langfuseはなくても動きます
LANGFUSE＿XXXX

long term memoryの動作を利用しない場合はpg vecotrは必要ありません
long term memoryを動かす場合は、composeの内容と.envの内容を確認してpg vectorを作成して下さい

## アプリモード

#### baseモード
supervisorで単純なマルチエージェントを構築

#### toolsモード
ローカルツールをsupervisorのマルチエージェントで利用する設定を追加

#### mcpモード
MCPサーバをsupervisorのマルチエージェントで利用する設定を追加

#### memory shortモード
MCPサーバをsupervisorのマルチエージェントで利用す設定にさらに揮発性の会話の大事なところだけ保存する記憶を追加

#### memory longモード
MCPサーバをsupervisorのマルチエージェントで利用す設定にさらに不揮発性の会話の大事なところだけ保存する記憶を追加

## アプリ実行 

```
uv run streamlit run ./superviser.py 
```

## モード切り替え

ソースコードのmain関数内のmode変数の値を変える

## ローカルツール

現在時刻を返す

## mcp server

- Time MCP Server
時間とタイムゾーンの変換機能を提供するモデル コンテキスト プロトコル サーバー。
このサーバーにより、LLM は現在の時間情報を取得し、IANA タイムゾーン名を使用してタイムゾーン変換を実行し、システムのタイムゾーンを自動検出できるようになります。

- Chroma MCP Server
このサーバーは Chroma を利用したデータ取得機能を提供し、AI モデルが生成されたデータとユーザー入力に基づいてコレクションを作成し、
ベクトル検索、全文検索、メタデータ フィルタリングなどを使用してそのデータを取得できるようにします。

## pg vector　作成

```
docker compose up -d
```


