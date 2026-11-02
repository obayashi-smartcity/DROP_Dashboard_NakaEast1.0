# 中之島ダッシュボード

## ローカルでの作成と確認

```powershell
python -m unittest discover -s python -v
python python/prepare_nakanoshima_data.py `
  --users-csv .memo/datasource/mart_user.csv `
  --drops-csv .memo/datasource/mart_drop.csv `
  --output json/nakanoshima_dashboard.json
python -m http.server --bind 127.0.0.1 8000
```

ブラウザーで `http://127.0.0.1:8000` を開きます。生成物の`json/nakanoshima_dashboard.json`とPages用の`_site/`はGit管理対象外です。

## GitHub Pagesへの公開

このリポジトリには元CSVも生成JSONもコミットしません。workflowは手動実行時に専用Windows runner上のCSVを読み、JSONを生成してPages artifactにだけ格納します。

1. `nakanoshima-data`ラベルを付けた専用のWindows x64 self-hosted runnerを登録します。CSVはrunnerの作業ディレクトリ外に置きます。
2. リポジトリのActions変数`NAKANOSHIMA_DATA_DIR`に、`mart_user.csv`と`mart_drop.csv`を置いたディレクトリを設定します。
3. リポジトリ設定のPagesで公開元を`GitHub Actions`にします。
4. 保護されたブランチ上で`Deploy Nakanoshima dashboard` workflowを手動実行します。workflow_dispatch以外では起動しません。

公開時はPages artifactにJSONが含まれます。URLを告知しなくても、公開後は誰でもURLから閲覧・保存・共有できます。JSONには`account_id`、ニックネーム、投稿本文が含まれます。公開承認を得たデータだけをrunnerに配置してください。元CSV、画像URL、位置情報はartifactに含めません。

データ更新後の再公開は、専用runner上のCSVを更新してworkflowを再実行します。対象件数が0件、tenant不一致、キー欠損・投稿ID重複、日付不正があればJSON生成を中止します。