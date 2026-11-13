"""Exercise settings windows from Qt's outer event loop, without nested qWait."""
import json
import platform
import sys
import traceback
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QSpinBox, QSystemTrayIcon
from platform_support import APP_VERSION


def run_interval_checks(pet, output, checks):
    events=[]
    done=False
    watchdog=QTimer(pet)
    watchdog.setSingleShot(True)

    def mark(event):
        events.append(event)
        (output/'dialog-events.json').write_text(json.dumps(events,indent=2),encoding='utf-8')

    def finish(error=None):
        nonlocal done
        if done:return
        done=True
        watchdog.stop()
        watchdog.deleteLater()
        if pet.tray is not None:pet.tray.hide()
        result={'ok':error is None,'version':APP_VERSION,'checks':list(checks),
                'click_reactions':pet.click_history,'platform':sys.platform,
                'machine':platform.machine(),'qt_platform':QApplication.platformName(),
                'tray_available':QSystemTrayIcon.isSystemTrayAvailable()}
        if error:result['error']=error
        (output/'smoke-test.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        QApplication.instance().exit(1 if error else 0)

    def later(callback, delay=0):
        def guarded():
            if done:return
            try:callback()
            except Exception:finish(traceback.format_exc())
        QTimer.singleShot(delay,guarded)

    def check_tray_visible():
        assert pet.isVisible() and pet.frame_timer.isActive()
        checks.append('system tray hides and restores the window and its animation')
        finish()

    def restore_tray():
        assert not pet.isVisible() and not pet.frame_timer.isActive()
        action=next(a for a in pet.tray.contextMenu().actions() if a.text()=='显示休比')
        if sys.platform=='darwin':action.trigger()
        else:pet.tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
        later(check_tray_visible,100)

    def after_cancel():
        mark('cancel-finished')
        assert pet.interval_dialog is None
        assert pet.settings['idle_interval']==7 and not pet.menu_open and pet.frame_timer.isActive()
        checks.append('custom interval dialog accepts and saves seconds; pause stops both schedules')
        pet.toggle_option('random_idle',False)
        assert not pet.idle_timer.isActive() and not pet.walk_timer.isActive()
        checks.append('disabling automatic actions stops both schedules')
        if QSystemTrayIcon.isSystemTrayAvailable():
            pet.test_mode=False
            pet.make_tray()
            assert pet.tray is not None and pet.tray.isVisible()
            pet.hide_pet()
            later(restore_tray,100)
        else:finish()

    def after_accept():
        mark('accept-finished')
        assert pet.interval_dialog is None and pet.settings['idle_interval']==7
        stored=json.loads(pet.settings_path.read_text(encoding='utf-8'))
        assert stored['idle_interval']==7
        pet.choose_interval('idle_interval','待机动作间隔')
        dialog=pet.interval_dialog
        pet.choose_interval('walk_interval','散步间隔')
        assert pet.interval_dialog is dialog
        dialog.setIntValue(99)
        dialog.finished.connect(lambda _:later(after_cancel))
        later(dialog.reject,100)

    def fill():
        mark('fill')
        dialog=pet.interval_dialog
        assert dialog is not None and dialog.isVisible()
        spin=dialog.findChild(QSpinBox)
        spin.setValue(7)
        assert dialog.intValue()==7
        dialog.grab().save(str(output/'interval-settings.png'))
        dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
        mark('accept-click-returned')

    def start():
        mark('open-start')
        pet.choose_interval('idle_interval','待机动作间隔')
        dialog=pet.interval_dialog
        assert dialog is not None
        if sys.platform=='darwin':
            assert dialog.parentWidget() is None
            assert dialog.windowType()==Qt.WindowType.Window
            assert dialog.windowModality()==Qt.WindowModality.NonModal
        checks.append('custom interval dialog opens without blocking the event loop')
        mark('open-returned')
        dialog.finished.connect(lambda _:later(after_accept))
        later(fill,400)

    watchdog.timeout.connect(lambda:finish('Settings-window test timed out: '+repr(events)))
    watchdog.start(12000)
    later(start)
