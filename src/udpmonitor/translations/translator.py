"""Application translation service."""

from collections.abc import Callable


class Translator:
    """Provide localized strings and notification on language changes."""

    _strings = {
        "ja": {"app": "UDP Monitor", "dashboard": "ダッシュボード", "monitor": "モニター", "sessions": "セッション", "settings": "設定", "overview": "ネットワーク品質のリアルタイム概要", "ready": "準備完了", "waiting": "計測待ち", "health": "UDP Health", "rtt": "RTT", "loss": "Packet Loss", "jitter": "Jitter", "future": "この機能は準備中です", "future_body": "ネットワーク計測機能は Version 0.2 以降で追加します。", "language": "言語", "restore": "次回起動時に最後のページを開く", "ja_name": "日本語", "en_name": "English", "start": "監視を開始", "stop": "監視を停止", "refresh": "更新", "export_csv": "CSV エクスポート", "session_empty": "保存されたセッションはありません", "probe_type": "計測方式", "probe_udp_echo": "UDP Echo（RTT/Loss/Jitterを正確に計測。相手がEchoサーバーである必要あり）", "probe_tcp_connect": "TCP接続（多くのサーバーで動作。UDP固有の問題は検出不可）", "probe_icmp_ping": "ICMP Ping（OS標準pingを使用。管理者権限不要）", "compare": "比較", "compare_sessions": "セッション比較", "compare_need_two": "比較には2つ以上のセッションを選択してください", "compare_host": "対象", "compare_sample_count": "計測数", "compare_success_rate": "成功率", "compare_avg_rtt": "平均 RTT", "compare_avg_jitter": "平均 Jitter", "compare_avg_loss": "平均 Loss", "compare_duration": "継続時間", "close": "閉じる", "connection_settings": "接続設定", "host": "ホスト", "udp_port": "UDPポート（UDP Echo用）", "tcp_port": "TCPポート（TCP接続計測用）", "interval_seconds": "計測間隔（秒）", "timeout_seconds": "タイムアウト（秒）", "events": "イベント", "record_event": "記録", "event_description_placeholder": "何が起きたかを入力（例：Discordが切断）", "event_time": "時刻", "event_category": "分類", "event_description": "内容", "event_hint_active": "監視中のセッションにイベントを記録できます。", "event_hint_inactive": "監視を開始するとイベントを記録できます。過去のセッションのタイムラインは閲覧できます。", "event_category_manual": "手動", "event_category_discord": "Discord", "event_category_vrchat": "VRChat"},
        "en": {"app": "UDP Monitor", "dashboard": "Dashboard", "monitor": "Monitor", "sessions": "Sessions", "settings": "Settings", "overview": "Real-time network quality overview", "ready": "Ready", "waiting": "Waiting for measurement", "health": "UDP Health", "rtt": "RTT", "loss": "Packet Loss", "jitter": "Jitter", "future": "This feature is being prepared", "future_body": "Network measurements will arrive in Version 0.2 and later.", "language": "Language", "restore": "Open the last page on next launch", "ja_name": "Japanese", "en_name": "English", "start": "Start monitoring", "stop": "Stop monitoring", "refresh": "Refresh", "export_csv": "Export CSV", "session_empty": "No saved sessions.", "probe_type": "Probe strategy", "probe_udp_echo": "UDP Echo (accurate RTT/loss/jitter; target must run an Echo service)", "probe_tcp_connect": "TCP connect (works against most servers; can't see UDP-specific issues)", "probe_icmp_ping": "ICMP ping (uses the OS ping command; no admin rights required)", "compare": "Compare", "compare_sessions": "Session comparison", "compare_need_two": "Select two or more sessions to compare.", "compare_host": "Target", "compare_sample_count": "Samples", "compare_success_rate": "Success rate", "compare_avg_rtt": "Avg RTT", "compare_avg_jitter": "Avg jitter", "compare_avg_loss": "Avg loss", "compare_duration": "Duration", "close": "Close", "connection_settings": "Connection settings", "host": "Host", "udp_port": "UDP port (for UDP Echo)", "tcp_port": "TCP port (for TCP connect probing)", "interval_seconds": "Interval (seconds)", "timeout_seconds": "Timeout (seconds)", "events": "Events", "record_event": "Record", "event_description_placeholder": "What happened (e.g. Discord disconnected)", "event_time": "Time", "event_category": "Category", "event_description": "Description", "event_hint_active": "You can log an event for the running session.", "event_hint_inactive": "Start monitoring to log new events. Past sessions' timelines are still browsable.", "event_category_manual": "Manual", "event_category_discord": "Discord", "event_category_vrchat": "VRChat"},
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
