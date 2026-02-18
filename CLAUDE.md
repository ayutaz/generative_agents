# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

「Generative Agents: Interactive Simulacra of Human Behavior」（Park et al., 2023）の公式実装。GPTベースのLLMを用いて人間の行動をシミュレートする計算エージェントのフレームワーク。エージェントは仮想世界「Smallville」で生活し、認知モジュールとメモリシステムを通じて相互に対話する。

## 開発環境セットアップ

Python 3.12で動作確認済み。

```bash
uv sync                    # 基本依存のインストール
uv sync --extra analysis   # 分析用パッケージも含める
uv sync --extra test       # テスト用パッケージも含める
```

APIキー設定は`.env`ファイルで管理（`.gitignore`対象）。`.env.example`をコピーして設定:
```bash
cp .env.example .env
# .envを編集してAPIキーを設定
```

`.env`の必須項目:
```
OPENAI_API_KEY=<your-openai-api-key>
```

オプション項目（デフォルト値あり）:
```
MAZE_ASSETS_LOC=../../environment/frontend_server/static_dirs/assets
FS_STORAGE=../../environment/frontend_server/storage
FS_TEMP_STORAGE=../../environment/frontend_server/temp_storage
COLLISION_BLOCK_ID=32125
DEBUG=true
```

## サーバー起動

2つのターミナルが必要:

```bash
# ターミナル1: Djangoフロントエンドサーバー
cd environment/frontend_server
uv run python manage.py runserver
# → http://localhost:8000/

# ターミナル2: シミュレーションバックエンド
cd reverie/backend_server
uv run python reverie.py
# プロンプトでフォーク元シミュレーション名と新規名を入力
```

シミュレーションCLIコマンド:
- `run <ステップ数>` — 指定ステップ数を実行
- `fin` — 保存して終了
- `exit` — 保存せず終了
- `call -- load history the_ville/agent_history_init_n3.csv` — 履歴読み込み

リプレイ: `http://localhost:8000/replay/<sim-name>/<step>/`
デモ: `http://localhost:8000/demo/<sim-name>/<step>/<speed>/`（speed: 1=最遅, 5=最速）

## 依存関係管理

依存関係の正規ソース（source of truth）は`pyproject.toml`。`uv.lock`で再現可能なインストールを保証。

```bash
# パッケージの追加
uv add <package>

# パッケージの削除
uv remove <package>

# optional-dependenciesへの追加（例: analysis グループ）
uv add --optional analysis <package>

# ロックファイルの更新
uv lock

# 依存関係のインストール（.venvに同期）
uv sync
```

## テスト

pytestベースのテストスイート。OpenAI APIを呼ばずにオフラインで実行可能。

```bash
uv sync --extra test       # テスト用パッケージのインストール
uv run pytest -v           # 全テスト実行
```

テスト構成:
- `tests/conftest.py` — `utils.py`・GPT関連モジュールのスタブ注入
- `tests/test_path_finder.py` — パス探索アルゴリズム
- `tests/test_global_methods.py` — ユーティリティ関数
- `tests/test_scratch.py` — 作業記憶（Scratch）
- `tests/test_spatial_memory.py` — 空間記憶（MemoryTree）
- `tests/test_associative_memory.py` — 連想記憶（AssociativeMemory）
- `tests/test_retrieve_pure.py` — 検索モジュールの純粋関数
- `tests/test_reflect_triggers.py` — 内省トリガー
- `tests/fixtures/` — テスト用フィクスチャJSON

## アーキテクチャ

### 2層構成

- **`reverie/`** — シミュレーションバックエンド（Pythonスクリプト）
- **`environment/`** — WebフロントエンドUI（Django 4.2 LTS + SQLite）

### エージェント（Persona）の構造

エントリーポイントは`reverie/backend_server/reverie.py`の`ReverieServer`クラス。各エージェントは`persona/persona.py`の`Persona`クラスで定義される。

**3つのメモリシステム**（`persona/memory_structures/`）:
- **AssociativeMemory**（`associative_memory.py`）— 長期記憶。イベント・思考・会話を`ConceptNode`（主語-述語-目的語の三つ組）として格納。キーワードとembeddingでインデックス化
- **SpatialMemory**（`spatial_memory.py`）— 空間記憶。World → Sector → Arena → Objects の階層木構造
- **Scratch**（`scratch.py`）— 作業記憶。現在位置、時刻、アイデンティティ属性、現在の計画、ハイパーパラメータ（視野範囲、注意帯域幅）

**6つの認知モジュール**（`persona/cognitive_modules/`）— 各ステップでこの順に実行:
1. **perceive.py** — 視野範囲内のイベントを検出し記憶に格納
2. **retrieve.py** — cosine similarityでembeddingを検索し関連記憶を取得
3. **plan.py** — 日次計画（マクロ）と次アクション（ミクロ）を生成
4. **reflect.py** — 最近のイベントから焦点を生成し、洞察を作成
5. **execute.py** — 計画をタイル移動に変換（path_finder.py使用）、ペルソナ間対話処理
6. **converse.py** — エージェント間の対話生成

### GPTプロンプト管理

`persona/prompt_template/`配下に110以上のテンプレートファイル（`.txt`）がバージョン管理されている:
- `run_gpt_prompt.py` — 各認知機能に対応するプロンプトを実行
- `gpt_structure.py` — OpenAI APIラッパー
- `v1/`, `v2/`, `v3_ChatGPT/`, `safety/` — プロンプトのバージョン別テンプレート

### ワールド表現

`maze.py`の`Maze`クラスが2Dタイルグリッドを管理。衝突ブロック、アリーナ/セクター/ワールドの割り当て、ゲームオブジェクト位置を保持。マップデータはTiledエディタ形式。

### データ永続化

- シミュレーション保存先: `environment/frontend_server/storage/`
- 圧縮デモ: `environment/frontend_server/compressed_storage/`
- 圧縮ツール: `reverie/compress_sim_storage.py`の`compress()`関数

## 主要な依存関係

- Django 4.2 LTS（Webフレームワーク）
- openai 0.27.0（GPT API、**v1.0未満必須** — legacy API使用）
- gensim 4.x（embeddingによるメモリ検索）
- numpy, scipy, scikit-learn（数値計算・類似度計算）
- nltk（自然言語処理）
- pytest（テストフレームワーク、optional `test` グループ）

## ベースシミュレーション

- `base_the_ville_isabella_maria_klaus` — 3エージェント版（軽量テスト向け）
- `base_the_ville_n25` — 25エージェント版（フル規模）

## 注意事項

- CI/CDパイプライン・リンター設定は未構築
- OpenAI APIのレート制限とコストに注意。頻繁な保存を推奨
- `utils.py`はAPIキーを含むため.gitignore対象。絶対にコミットしない
- フロントエンドのDjango SECRET_KEYはハードコードされている（開発用のみ）
