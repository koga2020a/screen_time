# sclog.py 試験項目

## PCアクティビティのログ記録
```
python sclog.py log-pc-activity
```

## 視聴時間の確認（T/F/E）
```
python sclog.py check-watch-time
```

## 全PCの利用時間合計を取得
```
python sclog.py get-total-usage
```

## 特定PCの利用状況を取得
```
python sclog.py get-pc-usage 616bd16a-d9c1-4c41-8b96-414646d6d218 9e7ec6df-31af-4e88-ba60-66783d50bc08
```

## 許可された視聴時間を取得
```
python sclog.py get-allowed-time 616bd16a-d9c1-4c41-8b96-414646d6d218
```

## 利用状況の詳細チェック（通常モード）
```
python sclog.py check-usage
```

## 利用状況の詳細チェック（ホバーモード）
```
python sclog.py check-usage --message-mode hover
```

## 利用状況の詳細チェック（巨大表示モード）
```
python sclog.py check-usage --message-mode giant
```

## 視聴可能かどうかの確認（T/F/E）
```
python sclog.py is-able-watch
```

## 視聴時間の追加（30分追加）
```
python sclog.py insert-watch-log 616bd16a-d9c1-4c41-8b96-414646d6d218 30
```

## ファイル出力を使用する例
```
python sclog.py check-usage --output result.txt
```

## 複数のメッセージモードをファイル出力
```
python sclog.py check-usage --message-mode fileout --output result
```

## Shift-JISでの出力例
```
python sclog.py check-usage --encoding sjis --output result_sjis.txt
```

