# UDP Monitor

Windows 向けのリアルタイム UDP ネットワーク診断ツールです。

## 実装済みの機能（v0.1〜v0.5相当）

- ダークテーマの Dashboard / Monitor / Events / Sessions / Settings ページ切替
- 日本語・英語の表示切替、JSON 設定保存と構造化ログ
- UDP Echo・TCP接続・ICMP Ping の3方式を切り替え可能な計測（RTT / Packet Loss / Jitter / UDP Health Score）
- PyQtGraph によるリアルタイムグラフ
- SQLite へのセッション記録、CSV エクスポート、複数セッションの比較画面
- 手動イベント記録とセッションごとのタイムライン（Discord/VRChat関連の自動検出は未実装、手動でのカテゴリ分類のみ対応）

## Setup

Python 3.12 以降を使用してください。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
udp-monitor
```
