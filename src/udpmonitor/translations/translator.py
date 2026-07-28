"""Application translation service."""

from collections.abc import Callable


class Translator:
    """Provide localized strings and notification on language changes."""

    _strings = {
        "ja": {"app": "UDP Monitor", "dashboard": "ダッシュボード", "monitor": "モニター", "sessions": "セッション", "settings": "設定", "overview": "ネットワーク品質のリアルタイム概要", "ready": "準備完了", "waiting": "計測待ち", "health": "UDP Health", "rtt": "RTT", "loss": "Packet Loss", "jitter": "Jitter", "future": "この機能は準備中です", "future_body": "ネットワーク計測機能は Version 0.2 以降で追加します。", "language": "言語", "restore": "次回起動時に最後のページを開く", "ja_name": "日本語", "en_name": "English", "start": "監視を開始", "stop": "監視を停止", "refresh": "更新", "export_csv": "CSV エクスポート", "session_empty": "保存されたセッションはありません"},
        "en": {"app": "UDP Monitor", "dashboard": "Dashboard", "monitor": "Monitor", "sessions": "Sessions", "settings": "Settings", "overview": "Real-time network quality overview", "ready": "Ready", "waiting": "Waiting for measurement", "health": "UDP Health", "rtt": "RTT", "loss": "Packet Loss", "jitter": "Jitter", "future": "This feature is being prepared", "future_body": "Network measurements will arrive in Version 0.2 and later.", "language": "Language", "restore": "Open the last page on next launch", "ja_name": "Japanese", "en_name": "English", "start": "Start monitoring", "stop": "Stop monitoring", "refresh": "Refresh", "export_csv": "Export CSV", "session_empty": "No saved sessions."},
    }

    def __init__(self, language: str) -> None:
        """Initialize with a supported language."""
        self.language = language if language in self._strings else "ja"
        self._listeners: list[Callable[[], None]] = []

    def text(self, key: str) -> str:
        """Return a localized string."""
        return self._strings[self.language].get(key, key)

    def set_language(self, language: str) -> None:
        """Select a language and update subscribers."""
        if language in self._strings and language != self.language:
            self.language = language
            for listener in tuple(self._listeners):
                listener()

    def subscribe(self, listener: Callable[[], None]) -> None:
        """Subscribe to language change notifications."""
        self._listeners.append(listener)
