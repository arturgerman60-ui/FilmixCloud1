"""Lightweight internationalisation (RU / EN).

The UI calls ``t("key")`` to fetch a localized string. Language is switched at
runtime; registered observers are notified so open widgets can relabel.
"""
from __future__ import annotations

from typing import Callable, Dict, List

_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ru": {
        # App / nav
        "app_title": "FunPay AutoResponder",
        "nav_dashboard": "Дашборд",
        "nav_rules": "Автоответы",
        "nav_templates": "Шаблоны",
        "nav_settings": "Настройки",
        "nav_logs": "Логи",
        "nav_stats": "Статистика",
        "start": "Запустить",
        "stop": "Остановить",
        "running": "Работает",
        "stopped": "Остановлен",
        "online": "Онлайн",
        "offline": "Оффлайн",
        # Dashboard
        "dash_processed": "Обработано сообщений",
        "dash_replies": "Отправлено ответов",
        "dash_earned": "Заработано",
        "dash_uptime": "Время работы",
        "dash_status": "Состояние",
        "dash_account": "Аккаунт",
        "dash_recent": "Последние события",
        "dash_no_account": "Аккаунт не выбран",
        # Rules
        "rules_title": "Правила автоответов",
        "rules_add": "Добавить правило",
        "rules_edit": "Изменить",
        "rules_delete": "Удалить",
        "rules_enabled": "Вкл.",
        "rules_name": "Название",
        "rules_priority": "Приоритет",
        "rules_match_type": "Тип совпадения",
        "rules_pattern": "Шаблон / ключевые слова",
        "rules_response": "Ответ",
        "rules_empty": "Правил пока нет. Создайте первое!",
        "match_keyword": "Ключевые слова",
        "match_regex": "Регулярное выражение",
        "match_exact": "Точное совпадение",
        "match_contains": "Содержит",
        "match_any": "Любое сообщение",
        # Templates
        "tpl_title": "Шаблоны сообщений",
        "tpl_add": "Новый шаблон",
        "tpl_name": "Название",
        "tpl_body": "Текст (переменные: {username}, {game}, {price})",
        "tpl_generate_ai": "Сгенерировать через ИИ",
        "tpl_empty": "Шаблонов пока нет.",
        # Settings
        "set_general": "Основные",
        "set_timing": "Задержки и анти-бан",
        "set_filters": "Фильтры",
        "set_network": "Сеть и прокси",
        "set_notify": "Уведомления",
        "set_ai": "Искусственный интеллект",
        "set_account": "Аккаунт FunPay",
        "set_language": "Язык интерфейса",
        "set_theme": "Тема оформления",
        "set_poll_min": "Опрос, мин (сек)",
        "set_poll_max": "Опрос, макс (сек)",
        "set_reply_min": "Задержка ответа мин (сек)",
        "set_reply_max": "Задержка ответа макс (сек)",
        "set_headless": "Скрытый браузер (headless)",
        "set_autostart": "Автозапуск с Windows",
        "set_tray_close": "Сворачивать в трей при закрытии",
        "set_proxy_enable": "Использовать прокси",
        "set_save": "Сохранить",
        "set_saved": "Настройки сохранены",
        "set_export": "Экспорт настроек",
        "set_import": "Импорт настроек",
        "set_login": "Логин",
        "set_password": "Пароль",
        "set_golden_key": "golden_key (cookie)",
        "set_test_login": "Проверить вход",
        # Logs
        "logs_title": "Журнал событий",
        "logs_clear": "Очистить",
        "logs_autoscroll": "Автопрокрутка",
        # Stats
        "stats_title": "Статистика",
        "stats_by_day": "По дням",
        "stats_top_rules": "Топ правил",
        "stats_reset": "Сбросить статистику",
        # Tray
        "tray_show": "Показать",
        "tray_settings": "Настройки",
        "tray_stats": "Статистика",
        "tray_start": "Запустить бота",
        "tray_stop": "Остановить бота",
        "tray_exit": "Выход",
        # Misc
        "confirm": "Подтвердите",
        "confirm_delete": "Удалить этот элемент?",
        "confirm_exit": "Выйти из приложения?",
        "yes": "Да",
        "no": "Нет",
        "cancel": "Отмена",
        "save": "Сохранить",
        "error": "Ошибка",
        "success": "Готово",
        "warning": "Внимание",
    },
    "en": {
        "app_title": "FunPay AutoResponder",
        "nav_dashboard": "Dashboard",
        "nav_rules": "Auto-replies",
        "nav_templates": "Templates",
        "nav_settings": "Settings",
        "nav_logs": "Logs",
        "nav_stats": "Statistics",
        "start": "Start",
        "stop": "Stop",
        "running": "Running",
        "stopped": "Stopped",
        "online": "Online",
        "offline": "Offline",
        "dash_processed": "Messages processed",
        "dash_replies": "Replies sent",
        "dash_earned": "Earned",
        "dash_uptime": "Uptime",
        "dash_status": "Status",
        "dash_account": "Account",
        "dash_recent": "Recent activity",
        "dash_no_account": "No account selected",
        "rules_title": "Auto-reply rules",
        "rules_add": "Add rule",
        "rules_edit": "Edit",
        "rules_delete": "Delete",
        "rules_enabled": "On",
        "rules_name": "Name",
        "rules_priority": "Priority",
        "rules_match_type": "Match type",
        "rules_pattern": "Pattern / keywords",
        "rules_response": "Response",
        "rules_empty": "No rules yet. Create your first one!",
        "match_keyword": "Keywords",
        "match_regex": "Regular expression",
        "match_exact": "Exact match",
        "match_contains": "Contains",
        "match_any": "Any message",
        "tpl_title": "Message templates",
        "tpl_add": "New template",
        "tpl_name": "Name",
        "tpl_body": "Body (variables: {username}, {game}, {price})",
        "tpl_generate_ai": "Generate with AI",
        "tpl_empty": "No templates yet.",
        "set_general": "General",
        "set_timing": "Timing & anti-ban",
        "set_filters": "Filters",
        "set_network": "Network & proxy",
        "set_notify": "Notifications",
        "set_ai": "Artificial intelligence",
        "set_account": "FunPay account",
        "set_language": "Interface language",
        "set_theme": "Theme",
        "set_poll_min": "Poll min (sec)",
        "set_poll_max": "Poll max (sec)",
        "set_reply_min": "Reply delay min (sec)",
        "set_reply_max": "Reply delay max (sec)",
        "set_headless": "Headless browser",
        "set_autostart": "Start with Windows",
        "set_tray_close": "Minimize to tray on close",
        "set_proxy_enable": "Use proxy",
        "set_save": "Save",
        "set_saved": "Settings saved",
        "set_export": "Export settings",
        "set_import": "Import settings",
        "set_login": "Login",
        "set_password": "Password",
        "set_golden_key": "golden_key (cookie)",
        "set_test_login": "Test login",
        "logs_title": "Event log",
        "logs_clear": "Clear",
        "logs_autoscroll": "Auto-scroll",
        "stats_title": "Statistics",
        "stats_by_day": "By day",
        "stats_top_rules": "Top rules",
        "stats_reset": "Reset statistics",
        "tray_show": "Show",
        "tray_settings": "Settings",
        "tray_stats": "Statistics",
        "tray_start": "Start bot",
        "tray_stop": "Stop bot",
        "tray_exit": "Exit",
        "confirm": "Confirm",
        "confirm_delete": "Delete this item?",
        "confirm_exit": "Exit the application?",
        "yes": "Yes",
        "no": "No",
        "cancel": "Cancel",
        "save": "Save",
        "error": "Error",
        "success": "Done",
        "warning": "Warning",
    },
}


class I18N:
    def __init__(self, language: str = "ru") -> None:
        self._language = language if language in _TRANSLATIONS else "ru"
        self._observers: List[Callable[[str], None]] = []

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        if language in _TRANSLATIONS and language != self._language:
            self._language = language
            for obs in list(self._observers):
                try:
                    obs(language)
                except Exception:
                    pass

    def t(self, key: str) -> str:
        table = _TRANSLATIONS.get(self._language, {})
        return table.get(key, _TRANSLATIONS["en"].get(key, key))

    def add_observer(self, callback: Callable[[str], None]) -> None:
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: Callable[[str], None]) -> None:
        if callback in self._observers:
            self._observers.remove(callback)

    def available_languages(self) -> list[str]:
        return list(_TRANSLATIONS.keys())


# Global singleton used by the UI.
_i18n = I18N()


def init_i18n(language: str) -> I18N:
    _i18n.set_language(language)
    return _i18n


def get_i18n() -> I18N:
    return _i18n


def t(key: str) -> str:
    return _i18n.t(key)
