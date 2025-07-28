# Farm_AIagent5 - 農業AIエージェントシステム

次世代の農業管理を実現するLangGraphベースのマルチエージェントシステム

## 🌾 プロジェクト概要

Farm_AIagent5は、日本の農業従事者向けに設計された革新的なAIエージェントシステムです。LINEを通じた自然な対話により、農作業の記録・管理・計画を自動化し、農家の皆様の「考える時間を0にする」ことを目指しています。

### 主な特徴

- **LINE中心のユーザーインターフェース**: 普段使い慣れたLINEで全ての操作が完結
- **自然言語処理**: 日本語での自然な作業報告を構造化データに自動変換
- **マルチエージェント アーキテクチャ**: LangGraphによる専門特化エージェントの協調動作
- **Human-in-the-Loop**: 重要なデータ更新時の安全な確認フロー
- **パーソナライゼーション**: ユーザー固有の専門用語や作業パターンの学習

## 🏗️ システムアーキテクチャ

### エージェント構成

```
SupervisorAgent (司令塔)
├── ReadAgent (データ読み取り専門)
├── WriteAgent (データ書き込み専門)
├── RecommendationAgent (作業提案専門)
└── NotificationAgent (通知専門)
```

### 技術スタック

- **AI Framework**: Python 3.9+, LangChain, LangGraph
- **LLM**: Google Gemini Pro/Flash
- **Database**: MongoDB Atlas (Motor による非同期アクセス)
- **UI/UX**: LINE Messaging API + LIFF
- **Infrastructure**: Google Cloud (Functions, Cloud Run, Pub/Sub)
- **Monitoring**: LangSmith

## 📊 データベース設計

MongoDB を使用したドキュメント指向設計：

- **farmers**: 農家マスター（LINEアカウント連携）
- **fields**: 圃場マスター（位置情報、現在作付け状況）
- **tasks**: タスク管理（作業予定・実績）
- **farm_data**: 時系列データ（センサー、気象、手動入力）
- **agent_states**: LangGraph セッション状態の永続化

## 🚀 開発ロードマップ

### Phase 1: 基盤構築 (3週間)
- [x] システム設計・要件定義
- [x] MongoDB スキーマ設計
- [ ] Supervisor + ReadAgent による基本的なLINE Q&A

### Phase 2: コア機能実装 (3週間)
- [ ] WriteAgent による作業記録登録機能
- [ ] Human-in-the-Loop 確認フロー
- [ ] LIFF 基本ダッシュボード

### Phase 3: AI機能高度化 (4週間)
- [ ] RecommendationAgent による作業提案
- [ ] 高度なデータ分析・可視化機能
- [ ] LIFF アプリケーションの機能拡張

### Phase 4: 自律システム実現 (4週間)
- [ ] NotificationAgent によるプロアクティブ通知
- [ ] 非同期処理基盤（Cloud Pub/Sub）
- [ ] 本番運用に向けたセキュリティ・監視機能

## 🎯 プロジェクトゴール

### 定性目標
農業従事者が圃場のどこにいても、LINEを開けば「次に何をすべきか」が分かり、思考の負荷なく自信を持って作業に集中できる状態を実現する。

### 定量目標 (KPI)
- 農作業の判断・思考時間を平均10分から **0分** に短縮
- 新人作業員の判断迷い時間を週平均60分から **5分未満** に短縮
- LINE経由での作業記録・タスク完了率 **95%以上** を維持
- AIの応答時間を平均 **3秒以内** に実現

## 📁 プロジェクト構成

```
Farm_AIagent5/
├── src/                                    # メインソースコード
│   ├── agents/                            # AIエージェント
│   │   ├── base_agent.py                 # ベースエージェントクラス
│   │   ├── supervisor.py                 # 司令塔エージェント
│   │   ├── read_agent.py                 # データ読み取りエージェント
│   │   └── graph.py                      # LangGraphワークフロー定義
│   ├── api/                              # API エンドポイント
│   │   └── webhook.py                    # LINE Webhook ハンドラー
│   ├── models/                           # データモデル
│   │   ├── state.py                      # エージェント状態定義
│   │   └── mongodb_saver.py              # MongoDB チェックポイントセーバー
│   ├── config.py                         # 設定管理
│   ├── database.py                       # データベース接続
│   └── main.py                           # FastAPI アプリケーション
├── docs/                                 # 設計書・要件定義書
│   ├── 2025-07-28_プロジェクトタスクリスト.md
│   ├── LangGraph_マルチエージェント_要件定義書_v4.md
│   └── 2025-07-26_MongoDB_総合設計書.md
├── requirements.txt                      # Python依存関係
├── run.py                               # 開発用起動スクリプト
├── test_basic.py                        # 基本テストスクリプト
├── CLAUDE.md                            # Claude Code 用ガイダンス
└── README.md                            # このファイル
```

## 🛠️ 開発環境セットアップ

### Phase 1 基盤構築完了
基本的なLangGraphマルチエージェントシステムと LINE Webhook 基盤が実装されました。

### 実行方法

1. **依存関係のインストール**
```bash
pip install -r requirements.txt
```

2. **環境変数の設定** 
`.env` ファイルに必要な設定を記述：
```bash
# MongoDB
MONGODB_URI=mongodb+srv://...
MONGODB_DATABASE=agri_ai_db

# LINE Bot
LINE_CHANNEL_ACCESS_TOKEN=your-token
LINE_CHANNEL_SECRET=your-secret

# Google Gemini
GOOGLE_API_KEY=your-api-key
```

3. **開発サーバーの起動**
```bash
python run.py
```

4. **基本テストの実行**
```bash
python test_basic.py
```

### 前提条件
- Python 3.9+
- MongoDB Atlas アカウント
- Google Cloud Platform アカウント
- LINE Developers アカウント

### 環境変数
```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json

# MongoDB
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/

# LINE
LINE_CHANNEL_ACCESS_TOKEN=your-line-channel-access-token
LINE_CHANNEL_SECRET=your-line-channel-secret

# LLM
GOOGLE_API_KEY=your-gemini-api-key
```

## 🤝 コントリビューション

このプロジェクトは現在設計・開発段階です。フィードバックやご提案がございましたら、Issues または Pull Requests をお送りください。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルをご確認ください。

## 👥 開発チーム

- **Project Lead**: [tomiyasu0428](https://github.com/tomiyasu0428)
- **AI Assistant**: Claude (Anthropic)

---

**"Think Zero, Act Smart" - 考える時間をゼロに、スマートな農業を**