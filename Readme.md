


### アプリ実行 
uv run streamlit run ./superviser.py 

### pg vector　作成
docker compose up -d

### mcp server

- Time MCP Server
時間とタイムゾーンの変換機能を提供するモデル コンテキスト プロトコル サーバー。
このサーバーにより、LLM は現在の時間情報を取得し、IANA タイムゾーン名を使用してタイムゾーン変換を実行し、システムのタイムゾーンを自動検出できるようになります。

- Chroma MCP Server
このサーバーは Chroma を利用したデータ取得機能を提供し、AI モデルが生成されたデータとユーザー入力に基づいてコレクションを作成し、
ベクトル検索、全文検索、メタデータ フィルタリングなどを使用してそのデータを取得できるようにします。
