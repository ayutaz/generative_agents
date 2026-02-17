

# Generative Agents: Interactive Simulacra of Human Behavior

<p align="center" width="100%">
<img src="cover.png" alt="Smallville" style="width: 80%; min-width: 300px; display: block; margin: auto;">
</p>

このリポジトリは、研究論文「[Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)」に付属するものです。人間の行動を信憑性高くシミュレートする計算エージェント（Generative Agents）のコアシミュレーションモジュールと、そのゲーム環境を含んでいます。以下では、ローカルマシンでのシミュレーション環境の構築手順と、シミュレーションをデモアニメーションとしてリプレイする方法を説明します。

## <img src="https://joonsungpark.s3.amazonaws.com:443/static/assets/characters/profile/Isabella_Rodriguez.png" alt="Generative Isabella">   環境のセットアップ
環境をセットアップするには、OpenAI APIキーを含む`utils.py`ファイルを生成し、必要なパッケージをインストールする必要があります。

### Step 1. utilsファイルの生成
`reverie/backend_server`フォルダ（`reverie.py`が配置されている場所）に、`utils.py`という名前の新しいファイルを作成し、以下の内容をコピー＆ペーストしてください:
```
# OpenAI APIキーをコピー＆ペーストしてください
openai_api_key = "<Your OpenAI API>"
# あなたの名前を入力してください
key_owner = "<Name>"

maze_assets_loc = "../../environment/frontend_server/static_dirs/assets"
env_matrix = f"{maze_assets_loc}/the_ville/matrix"
env_visuals = f"{maze_assets_loc}/the_ville/visuals"

fs_storage = "../../environment/frontend_server/storage"
fs_temp_storage = "../../environment/frontend_server/temp_storage"

collision_block_id = "32125"

# 詳細ログ出力
debug = True
```
`<Your OpenAI API>`をご自身のOpenAI APIキーに、`<Name>`をご自身の名前に置き換えてください。

### Step 2. パッケージのインストール
Python 3.9.12で動作確認済みです。

[uv](https://docs.astral.sh/uv/)を使って依存関係をインストールします:

    uv sync

分析用パッケージ（gensim, scipy, scikit-learn等）も必要な場合:

    uv sync --extra analysis

テスト実行用パッケージが必要な場合:

    uv sync --extra test

サーバー起動時は`uv run`プレフィックスを付けてください（例: `uv run python manage.py runserver`）。

## <img src="https://joonsungpark.s3.amazonaws.com:443/static/assets/characters/profile/Klaus_Mueller.png" alt="Generative Klaus">   シミュレーションの実行
新しいシミュレーションを実行するには、環境サーバーとエージェントシミュレーションサーバーの2つを同時に起動する必要があります。

### Step 1. 環境サーバーの起動
環境はDjangoプロジェクトとして実装されているため、Djangoサーバーを起動する必要があります。まず、コマンドラインで`environment/frontend_server`（`manage.py`が配置されている場所）に移動し、以下のコマンドを実行してください:

    python manage.py runserver

次に、ブラウザで[http://localhost:8000/](http://localhost:8000/)にアクセスしてください。「Your environment server is up and running」というメッセージが表示されれば、サーバーは正常に動作しています。シミュレーション実行中は環境サーバーを稼働させ続ける必要があるため、このコマンドラインタブは開いたままにしてください。（注意: ChromeまたはSafariの使用を推奨します。Firefoxではフロントエンドの表示に若干の不具合が生じる場合がありますが、シミュレーション自体には影響しません。）

### Step 2. シミュレーションサーバーの起動
別のコマンドラインを開いてください（Step 1で使用したものは環境サーバーを実行中のため、そのままにしておいてください）。`reverie/backend_server`に移動し、`reverie.py`を実行します。

    python reverie.py
シミュレーションサーバーが起動します。コマンドラインに「Enter the name of the forked simulation: 」というプロンプトが表示されます。Isabella Rodriguez、Maria Lopez、Klaus Muellerの3エージェントによるシミュレーションを開始するには、以下のように入力してください:

    base_the_ville_isabella_maria_klaus
続いて、「Enter the name of the new simulation: 」と表示されます。現在のシミュレーションを識別するための任意の名前を入力してください（例: 「test-simulation」で構いません）。

    test-simulation
シミュレーションサーバーはそのまま稼働させておいてください。この段階で「Enter option: 」というプロンプトが表示されます。

### Step 3. シミュレーションの実行と保存
ブラウザで[http://localhost:8000/simulator_home](http://localhost:8000/simulator_home)にアクセスしてください。Smallvilleのマップと、マップ上のアクティブなエージェント一覧が表示されます。キーボードの矢印キーでマップ内を移動できます。このタブは開いたままにしてください。シミュレーションを実行するには、シミュレーションサーバーの「Enter option」プロンプトに対して以下のコマンドを入力します:

    run <step-count>
`<step-count>`にはシミュレートしたいゲームステップ数を整数で指定してください。例えば、100ゲームステップをシミュレートする場合は`run 100`と入力します。1ゲームステップはゲーム内の10秒に相当します。


シミュレーションが実行され、ブラウザ上でエージェントがマップ内を移動する様子が確認できます。シミュレーションの実行が完了すると、再び「Enter option」プロンプトが表示されます。この時点で、runコマンドを再入力してさらにステップを実行するか、`exit`と入力して保存せずに終了するか、`fin`と入力して保存してから終了できます。

保存したシミュレーションは、次回シミュレーションサーバーを起動する際に、フォーク元のシミュレーション名として指定することでアクセスできます。これにより、前回の中断箇所からシミュレーションを再開できます。

### Step 4. シミュレーションのリプレイ
既に実行済みのシミュレーションをリプレイするには、環境サーバーを稼働させた状態でブラウザから以下のアドレスにアクセスしてください: `http://localhost:8000/replay/<simulation-name>/<starting-time-step>`。`<simulation-name>`にはリプレイしたいシミュレーション名を、`<starting-time-step>`にはリプレイを開始したいタイムステップの整数値を指定してください。

例えば、以下のリンクにアクセスすると、事前にシミュレーション済みのサンプルがタイムステップ1から再生されます:
[http://localhost:8000/replay/July1_the_ville_isabella_maria_klaus-step-3-20/1/](http://localhost:8000/replay/July1_the_ville_isabella_maria_klaus-step-3-20/1/)

### Step 5. シミュレーションのデモ
リプレイではすべてのキャラクタースプライトが同一であることにお気づきかもしれません。リプレイ機能は主にデバッグ用途を想定しており、シミュレーションフォルダのサイズやビジュアルの最適化は優先していません。適切なキャラクタースプライトでシミュレーションをデモ表示するには、まずシミュレーションを圧縮する必要があります。`reverie`ディレクトリにある`compress_sim_storage.py`ファイルをテキストエディタで開き、対象のシミュレーション名を引数として`compress`関数を実行してください。これにより、シミュレーションファイルが圧縮され、デモの準備が整います。

デモを開始するには、ブラウザで以下のアドレスにアクセスしてください: `http://localhost:8000/demo/<simulation-name>/<starting-time-step>/<simulation-speed>`。`<simulation-name>`と`<starting-time-step>`は上記と同じ意味です。`<simulation-speed>`はデモの再生速度を制御するもので、1が最も遅く、5が最も速くなります。例えば、以下のリンクにアクセスすると、事前にシミュレーション済みのサンプルがタイムステップ1から中速で再生されます:
[http://localhost:8000/demo/July1_the_ville_isabella_maria_klaus-step-3-20/1/3/](http://localhost:8000/demo/July1_the_ville_isabella_maria_klaus-step-3-20/1/3/)

### Tips
OpenAIのAPIは、時間あたりのレート制限に達するとハングすることがあります。その場合はシミュレーションの再起動が必要になることがあります。現時点では、シミュレーションの停止・再実行が必要になった際にできるだけ進捗を失わないよう、こまめに保存することを推奨します。2023年初頭時点では、特に多数のエージェントが存在する環境では、シミュレーションの実行コストがかなり高くなる可能性があります。

## <img src="https://joonsungpark.s3.amazonaws.com:443/static/assets/characters/profile/Maria_Lopez.png" alt="Generative Maria">   シミュレーションの保存場所
保存されたシミュレーションはすべて`environment/frontend_server/storage`に、圧縮済みデモはすべて`environment/frontend_server/compressed_storage`に配置されます。

## テストの実行

OpenAI APIを呼ばずにオフラインで実行可能なpytestテストスイートが含まれています。

    uv sync --extra test
    uv run pytest -v

## <img src="https://joonsungpark.s3.amazonaws.com:443/static/assets/characters/profile/Sam_Moore.png" alt="Generative Sam">   カスタマイズ

シミュレーションをカスタマイズする方法は2つあります。

### エージェント履歴の作成とロード
1つ目は、シミュレーション開始時にエージェントに固有の履歴を設定する方法です。これを行うには、1) ベースシミュレーションを使ってシミュレーションを開始し、2) エージェント履歴を作成してロードします。具体的な手順は以下の通りです:

#### Step 1. ベースシミュレーションの起動
リポジトリには2つのベースシミュレーションが含まれています: 25エージェントの`base_the_ville_n25`と、3エージェントの`base_the_ville_isabella_maria_klaus`です。上記のStep 2までの手順に従って、いずれかのベースシミュレーションをロードしてください。

#### Step 2. 履歴ファイルのロード
「Enter option: 」プロンプトが表示されたら、以下のコマンドでエージェント履歴をロードします:

    call -- load history the_ville/<history_file_name>.csv
`<history_file_name>`は既存の履歴ファイル名に置き換えてください。リポジトリにはサンプルとして2つの履歴ファイルが含まれています: `base_the_ville_n25`用の`agent_history_init_n25.csv`と、`base_the_ville_isabella_maria_klaus`用の`agent_history_init_n3.csv`です。これらのファイルには各エージェントのメモリレコードがセミコロン区切りのリストで格納されており、ロードするとエージェントのメモリストリームにレコードが挿入されます。

#### Step 3. さらなるカスタマイズ
独自の履歴ファイルを作成して初期化をカスタマイズするには、ファイルを以下のフォルダに配置してください: `environment/frontend_server/static_dirs/assets/the_ville`。カスタム履歴ファイルのカラム形式は、サンプルの履歴ファイルと一致させる必要があります。そのため、リポジトリに含まれている既存ファイルをコピーして編集することから始めることを推奨します。

### 新しいベースシミュレーションの作成
より本格的なカスタマイズを行うには、独自のベースシミュレーションファイルを作成する必要があります。最も簡単な方法は、既存のベースシミュレーションフォルダをコピーし、必要に応じてリネーム・編集することです。エージェント名を変更しない場合は比較的簡単に行えます。ただし、エージェント名を変更したり、Smallvilleマップが収容できるエージェント数を増やしたりする場合は、[Tiled](https://www.mapeditor.org/)マップエディタを使用してマップを直接編集する必要があるかもしれません。


## <img src="https://joonsungpark.s3.amazonaws.com:443/static/assets/characters/profile/Eddy_Lin.png" alt="Generative Eddy">   著者と引用

**著者:** Joon Sung Park, Joseph C. O'Brien, Carrie J. Cai, Meredith Ringel Morris, Percy Liang, Michael S. Bernstein

本リポジトリのコードやデータを使用する場合は、以下の論文を引用してください。
```
@inproceedings{Park2023GenerativeAgents,
author = {Park, Joon Sung and O'Brien, Joseph C. and Cai, Carrie J. and Morris, Meredith Ringel and Liang, Percy and Bernstein, Michael S.},
title = {Generative Agents: Interactive Simulacra of Human Behavior},
year = {2023},
publisher = {Association for Computing Machinery},
address = {New York, NY, USA},
booktitle = {In the 36th Annual ACM Symposium on User Interface Software and Technology (UIST '23)},
keywords = {Human-AI interaction, agents, generative AI, large language models},
location = {San Francisco, CA, USA},
series = {UIST '23}
}
```

## <img src="https://joonsungpark.s3.amazonaws.com:443/static/assets/characters/profile/Wolfgang_Schulz.png" alt="Generative Wolfgang">   謝辞

本プロジェクトのゲームアセットをデザインしてくださった以下の3名の素晴らしいアーティストを応援していただければ幸いです。特に、ここに含まれるアセットをご自身のプロジェクトで使用される予定の方はぜひお願いいたします:
* 背景アート: [PixyMoon (@_PixyMoon\_)](https://twitter.com/_PixyMoon_)
* 家具・インテリアデザイン: [LimeZu (@lime_px)](https://twitter.com/lime_px)
* キャラクターデザイン: [ぴぽ (@pipohi)](https://twitter.com/pipohi)

また、Lindsay Popowski、Philip Guo、Michael Terry、そしてCenter for Advanced Study in the Behavioral Sciences (CASBS) コミュニティの皆様に、貴重な知見、議論、サポートをいただいたことに感謝いたします。最後に、Smallvilleに登場するすべての場所は、Joonが学部生・大学院生時代に通った実在の場所にインスピレーションを得ています。長年にわたり支えてくださったすべての方々に感謝します。


