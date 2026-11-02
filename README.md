# 中之島 DROP ダッシュボード

中之島イベントのアカウント登録と投稿を確認する静的ダッシュボードです。HTML・CSS・JavaScriptで構成し、投稿画像はCSVに記録されたURLからブラウザーで直接読み込みます。

## ページ

- **Summary**: 登録推移、投稿数、最新データ時刻を表示します。
- **アカウント登録**: 登録日時、年代、性別を表示します。
- **投稿**: 投稿カードと地図を表示します。画像または地図上の投稿地点を選ぶと投稿詳細を開きます。

## データと生成物

入力元は `.memo/datasource/mart_user.csv` と `.memo/datasource/mart_drop.csv` です。`.memo/` はローカルの入力データや作業メモを置く場所で、Git管理・公開の対象ではありません。

`python/prepare_nakanoshima_data.py` は中之島イベントの対象データを抽出し、アカウントIDで登録と投稿を紐づけ、`json/nakanoshima_dashboard.json` を生成します。JSONには公開対象の登録属性、投稿本文、画像URL、対象投稿の座標が含まれます。画像ファイル自体はコピーしません。

入力CSVは `.memo/` に置き、Gitには追加しません。生成した `json/nakanoshima_dashboard.json` はダッシュボードの公開データとしてGit追跡します。公開前にJSONの差分と、登録属性・投稿本文・座標・画像URLが公開可能な内容であることを確認してください。

## ローカルで実行

Python 3.10以上を使用してください。外部Pythonパッケージは不要です。

```powershell
python -m unittest discover -s python -v
python python/prepare_nakanoshima_data.py `
  --users-csv .memo/datasource/mart_user.csv `
  --drops-csv .memo/datasource/mart_drop.csv `
  --output json/nakanoshima_dashboard.json
python -m http.server --bind 127.0.0.1 8000
```

ブラウザーで <http://127.0.0.1:8000/> を開きます。`.memo/datasource/` に入力CSVがない場合、JSON生成コマンドは実行できません。

## GitHub Pagesへの公開と更新

リポジトリの **Settings > Pages > Build and deployment** で、Sourceを **Deploy from a branch**、Branchをデフォルトブランチ、Folderを **/(root)** に設定します。ルートの `index.html` がトップページです。公開元ブランチへのpush後、GitHub Pagesが更新されます。

データを更新するときは、ローカルの `.memo/datasource/` にあるCSVを更新し、テストとJSON生成を実行します。JSONの差分を確認してから、アプリの変更とJSONをコミット・pushしてください。GitHub PagesはPythonを実行しないため、JSON生成はローカルで行います。詳しい手順は [DEPLOYMENT.md](DEPLOYMENT.md) を参照してください。

Pagesサイトはインターネット上に公開されます。`.memo/` のCSVはGit追跡されないため公開元には含まれませんが、Gitに追加したJSONやソースファイルは公開され得ます。`.gitignore` は既に追跡されているファイルを非公開にするものではありません。