import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib  # noqa: E402

from src.core.logging_config import setup_logging  # noqa: E402
from src.gui.main_window import BeholderWindow  # noqa: E402

_APP_ID = "com.beholder.app"


def main() -> None:
    setup_logging()
    GLib.set_prgname(_APP_ID)
    GLib.set_application_name("Beholder")
    app = Adw.Application(application_id=_APP_ID)
    app.connect("activate", on_activate)
    app.run(None)


def on_activate(app: Adw.Application) -> None:
    window = BeholderWindow(application=app)
    window.present()


if __name__ == "__main__":
    main()


# "A natureza não se apressa, e ainda assim tudo se realiza." — Lao Tsé
