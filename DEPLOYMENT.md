# GitHub Pages 公開手順

## 初回設定

リポジトリの **Settings > Pages > Build and deployment** で、次の公開元を選択します。

- Source: **Deploy from a branch**
- Branch: デフォルトブランチ
- Folder: **/(root)**

保存後、公開元ブランチへのpushでサイトが更新されます。ルートの `index.html` がトップページです。GitHub Pagesのブランチ公開ではPages側のビルドが行われますが、リポジトリ独自のPagesデプロイworkflowやPython実行環境は使いません。

## データ更新

1. `.memo/datasource/mart_user.csv` と `.memo/datasource/mart_drop.csv` をローカルで更新します。CSVはGitに追加しません。
2. テストとJSON生成を実行します。

   ```powershell
   python -m unittest discover -s python -v
   python python/prepare_nakanoshima_data.py `
     --users-csv .memo/datasource/mart_user.csv `
     --drops-csv .memo/datasource/mart_drop.csv `
     --output json/nakanoshima_dashboard.json
   ```

3. `json/nakanoshima_dashboard.json` の差分を確認し、公開してよいデータであることを確認します。
4. JSONと必要なアプリ変更をコミットし、デフォルトブランチへpushします。

PagesはPythonを実行しません。CSVが変わってもJSONは自動生成されないため、更新のたびにローカル生成したJSONをコミットしてください。投稿画像はファイルをリポジトリにコピーせず、JSONに記録されたURLをブラウザーから参照します。

## 公開データの注意

Pagesはインターネット上に公開されます。JSONにはアカウントID、ニックネーム、登録日時、年代、性別、投稿本文、対象投稿の座標、画像URLが含まれます。公開承認済みのデータのみをJSONに含めてください。CARTO APIキーはブラウザーに配信されるため、公開キーとして扱ってください。

`.memo/` はGitignore対象であり、現在Git追跡されていません。ただし、Gitignoreは追跡済みファイルを除外しません。公開前には `git status` とコミット内容を確認してください。