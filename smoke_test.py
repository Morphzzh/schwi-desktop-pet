"""Exercise real Qt mouse events and timers in source and packaged application."""
import json
import traceback
import platform
import sys
import time
from pathlib import Path
from PySide6.QtCore import QPoint, QPointF, QEvent, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QSystemTrayIcon


def wait_until(predicate, timeout=3500):
    deadline = time.monotonic() + timeout / 1000
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(25)
    assert predicate(), 'Animation did not reach the expected state before timeout'


def run_smoke_test(pet, output: Path):
    output.mkdir(parents=True,exist_ok=True)
    checks=[]
    try:
        pet.settings['random_idle']=False
        pet.idle_timer.stop()
        pet.move(pet.keep_on_screen(QPoint(300,180)))
        QTest.qWait(100)
        assert pet.isVisible() and pet.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert pet.windowFlags() & Qt.WindowType.FramelessWindowHint
        checks.append('visible transparent frameless native window')
        original=pet.current_pixmap().toImage()
        assert original.pixelColor(0,0).alpha()==0
        checks.append('transparent sprite corners')
        pet.grab().save(str(output/'window-idle.png'))
        point=QPoint(pet.width()//2,pet.height()//2)
        for index in range(7):
            QTest.mouseClick(pet,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
            wait_until(lambda: len(pet.click_history)==index+1)
        assert len(pet.click_history)==7
        assert len(set(pet.click_history[:6]))==6
        assert all(a!=b for a,b in zip(pet.click_history,pet.click_history[1:]))
        checks.append('seven real clicks: six distinct reactions and no adjacent repeats')
        before=len(pet.click_history)
        start=pet.pos()
        QTest.mousePress(pet,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
        global_pos=pet.mapToGlobal(point)+QPoint(-80,-50)
        move=QMouseEvent(QEvent.Type.MouseMove,QPointF(point+QPoint(-80,-50)),QPointF(global_pos),Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(pet,move)
        QTest.mouseRelease(pet,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
        QTest.qWait(QApplication.doubleClickInterval()+70)
        assert pet.pos()!=start and len(pet.click_history)==before
        checks.append('drag moves native window without a click reaction')
        QTest.mouseDClick(pet,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
        QTest.mouseRelease(pet,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
        QTest.qWait(30)
        assert pet.state=='jumping' and not pet.click_timer.isActive()
        checks.append('double click starts jump without pending single click')
        wait_until(lambda: pet.state=='idle')
        checks.append('one-shot action returns to idle')
        pet.play_reaction('shy')
        wait_until(lambda: pet.state=='shy' and pet.frame in (2,3))
        QTest.qWait(200)
        assert pet.state=='shy' and pet.frame in (2,3)
        pet.grab().save(str(output/'window-shy.png'))
        checks.append('shy face-cover hold is shown by actual animation timer')
        pet.toggle_option('paused',True)
        QTest.mouseClick(pet,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
        QTest.qWait(QApplication.doubleClickInterval()+70)
        assert pet.state=='idle' and not pet.frame_timer.isActive()
        assert len(pet.click_history)==before
        checks.append('pause stops animation and reactions')
        pet.toggle_option('paused',False)
        bottom=pet.y()+pet.height()
        pet.change_scale(1.5)
        assert pet.size().width()==288 and pet.y()+pet.height()==bottom
        checks.append('resize preserves bottom anchor')
        pet.toggle_option('topmost',False)
        assert not(pet.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        pet.toggle_option('topmost',True)
        assert pet.isVisible() and pet.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
        checks.append('topmost toggle keeps pet visible')
        menu=pet.make_menu()
        labels=[a.text() for a in menu.actions()]
        assert '和休比互动' in labels and '退出桌宠' in labels
        submenu=next(a.menu() for a in menu.actions() if a.text()=='和休比互动')
        shy_action=next(a for a in submenu.actions() if a.text().startswith('害羞'))
        shy_action.trigger()
        assert pet.state=='shy'
        menu.popup(pet.mapToGlobal(QPoint(pet.width(),40)));QTest.qWait(150)
        menu.grab().save(str(output/'context-menu.png'));menu.hide()
        checks.append('real menu includes and triggers explicit shy action')
        pet.persist()
        stored=json.loads(pet.settings_path.read_text(encoding='utf-8'))
        assert stored['scale']==1.5 and stored['x']==pet.x() and stored['y']==pet.y()
        checks.append('position and preferences persisted')
        if QSystemTrayIcon.isSystemTrayAvailable():
            pet.test_mode=False
            pet.make_tray()
            assert pet.tray is not None and pet.tray.isVisible()
            pet.hide_pet()
            QTest.qWait(100)
            assert not pet.isVisible() and not pet.frame_timer.isActive()
            assert any(a.text()=='显示休比' for a in pet.tray.contextMenu().actions())
            if sys.platform == 'darwin':
                next(a for a in pet.tray.contextMenu().actions() if a.text()=='显示休比').trigger()
            else:
                pet.tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
            QTest.qWait(100)
            assert pet.isVisible() and pet.frame_timer.isActive()
            checks.append('system tray hides and restores the window and its animation')
            pet.tray.hide()
        result={'ok':True,'checks':checks,'click_reactions':pet.click_history,
                'platform':sys.platform,'machine':platform.machine(),
                'qt_platform':QApplication.platformName(),
                'tray_available':QSystemTrayIcon.isSystemTrayAvailable()}
        code=0
    except Exception:
        result={'ok':False,'checks':checks,'error':traceback.format_exc()}
        code=1
    (output/'smoke-test.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    QApplication.instance().exit(code)
