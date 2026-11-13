"""Exercise real Qt mouse events and timers in source and packaged application."""
import json
import hashlib
import traceback
import platform
import sys
import time
from pathlib import Path
from PySide6.QtCore import QPoint, QPointF, QEvent, QTimer, Qt
from PySide6.QtGui import QCursor, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QInputDialog, QSystemTrayIcon, QSpinBox, QDialogButtonBox
from unittest.mock import patch
from platform_support import APP_VERSION
from behavior import REACTIONS, IDLE_REACTIONS


def wait_until(predicate, timeout=3500):
    deadline = time.monotonic() + timeout / 1000
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(25)
    assert predicate(), 'Animation did not reach the expected state before timeout'


def run_smoke_test(pet, output: Path):
    output.mkdir(parents=True,exist_ok=True)
    class RecordedChecks(list):
        def append(self, check):
            super().append(check)
            (output/'progress.json').write_text(json.dumps(list(self),indent=2),encoding='utf-8')
    checks=RecordedChecks()
    try:
        asset_dir=Path(__file__).resolve().parent/'assets'
        manifest=json.loads((asset_dir/'manifest.json').read_text(encoding='utf-8'))
        assert manifest['version']==APP_VERSION
        for name,info in manifest['files'].items():
            assert hashlib.sha256((asset_dir/name).read_bytes()).hexdigest()==info['sha256'],name
        checks.append('all packaged artwork and portrait icons match the versioned release hashes')
        pet.settings['random_idle']=False
        pet.idle_timer.stop()
        pet.walk_timer.stop()
        pet.move(pet.keep_on_screen(QPoint(300,180)))
        QTest.qWait(100)
        assert pet.isVisible() and pet.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert pet.windowFlags() & Qt.WindowType.FramelessWindowHint
        checks.append('visible transparent frameless native window')
        original=pet.current_pixmap().toImage()
        assert original.pixelColor(0,0).alpha()==0
        checks.append('transparent sprite corners')
        idle=pet.sprites.frames['idle']
        from idle_render import EYE_REGIONS
        from PySide6.QtGui import QPainter
        masked=[]
        for frame in idle:
            copy=frame.toImage().copy()
            painter=QPainter(copy)
            for x,y,w,h in EYE_REGIONS:
                painter.fillRect(x,y,w,h,Qt.GlobalColor.black)
            painter.end()
            masked.append(copy)
        assert all(frame==masked[0] for frame in masked)
        assert idle[3].toImage()!=idle[0].toImage()
        checks.append('idle blink changes only the eye regions; shoulders, body and hair remain pixel-identical')
        assert original.width()==576 and original.height()==624
        right=pet.sprites.frames['running-right']
        left=pet.sprites.frames['running-left']
        for r,l in zip(right,left):
            assert r.toImage().mirrored(True,False)==l.toImage()
        times=pet.sprites.durations['running-right']
        assert times==pet.sprites.durations['running-left'] and len(set(times))==1
        assert sum(times[:4])==sum(times[4:])
        checks.append('triple-resolution source pixels and mirrored run cycles with equal-duration half strides')
        pet.grab().save(str(output/'window-idle.png'))
        pet.frame_timer.stop()
        pet.look=None
        pet.state,pet.frame='idle',0
        pet.repaint()
        clean_idle=pet.grab().toImage()
        for state,index in [('jumping',2),('excited',4),('sleepy',3)]:
            pet.state,pet.frame=state,index
            pet.repaint()
            pet.state,pet.frame='idle',0
            pet.repaint()
            assert pet.grab().toImage()==clean_idle
        checks.append('transparent repaint restores identical idle pixels after raised ears and shifted head poses')
        pet.start_state('idle')
        point=QPoint(pet.width()//2,pet.height()//2)
        for index in range(len(REACTIONS)+1):
            QTest.mouseClick(pet,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
            try:
                wait_until(lambda: len(pet.click_history)==index+1)
            except AssertionError as exc:
                raise AssertionError({'click':index,'history':pet.click_history,'state':pet.state,
                    'dragging':pet.dragging,'press':str(pet.press_global),'last_drag':str(pet.last_drag_global),
                    'position':str(pet.pos()),'click_timer':pet.click_timer.isActive()}) from exc
        assert len(pet.click_history)==len(REACTIONS)+1
        assert set(pet.click_history[:len(REACTIONS)])==set(REACTIONS)
        assert all(a!=b for a,b in zip(pet.click_history,pet.click_history[1:]))
        checks.append(f'{len(REACTIONS)+1} real clicks: {len(REACTIONS)} distinct reactions and no adjacent repeats')
        before=len(pet.click_history)
        start=pet.pos()
        QTest.mousePress(pet,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
        global_pos=pet.mapToGlobal(point)+QPoint(-80,-50)
        move=QMouseEvent(QEvent.Type.MouseMove,QPointF(point+QPoint(-80,-50)),QPointF(global_pos),Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(pet,move)
        assert pet.state=='running-left'
        # Reverse by only 8 px, while still far to the left of the press point.
        global_pos+=QPoint(8,0)
        move=QMouseEvent(QEvent.Type.MouseMove,QPointF(pet.mapFromGlobal(global_pos)),QPointF(global_pos),Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(pet,move)
        assert pet.state=='running-right'
        global_pos+=QPoint(0,8)
        move=QMouseEvent(QEvent.Type.MouseMove,QPointF(pet.mapFromGlobal(global_pos)),QPointF(global_pos),Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(pet,move)
        assert pet.state=='running-right'
        checks.append('drag reverses immediately before crossing press point; vertical motion preserves facing')
        frames_seen=set()
        for step_index in range(12):
            global_pos+=QPoint(2,0)
            move=QMouseEvent(QEvent.Type.MouseMove,QPointF(pet.mapFromGlobal(global_pos)),QPointF(global_pos),Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(pet,move)
            QTest.qWait(40)
            frames_seen.add(pet.frame)
        assert pet.state=='running-right' and len(frames_seen)>=4,frames_seen
        checks.append('continuous same-direction drag advances the running cycle instead of resetting its first frame')
        stride_frame=pet.frame
        global_pos-=QPoint(3,0)
        move=QMouseEvent(QEvent.Type.MouseMove,QPointF(pet.mapFromGlobal(global_pos)),QPointF(global_pos),Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(pet,move)
        assert pet.state=='running-left' and pet.frame==stride_frame
        checks.append('reversing drag preserves the alternating arm and leg cycle phase')
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
        wait_until(lambda: pet.state=='shy' and pet.frame in (3,4))
        QTest.qWait(200)
        assert pet.state=='shy' and pet.frame in (3,4)
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
        shy_action=next(a for a in submenu.actions() if a.text()=='害羞')
        shy_action.trigger()
        assert pet.state=='shy'
        menu.popup(pet.mapToGlobal(QPoint(pet.width(),40)));QTest.qWait(150)
        menu.grab().save(str(output/'context-menu.png'));menu.hide()
        checks.append('real menu includes and triggers explicit shy action')
        for label, state in [('兴奋','excited'), ('打瞌睡','sleepy')]:
            next(a for a in submenu.actions() if a.text()==label).trigger()
            assert pet.state==state
            wait_until(lambda: pet.state==state and pet.frame==3)
            pet.grab().save(str(output/('window-'+state+'.png')))
            wait_until(lambda: pet.state=='idle',4500)
        checks.append('ear flutter and dozing menu actions animate and return to idle')
        for label,state in [('猜拳','rps'),('认真思考','running')]:
            next(a for a in submenu.actions() if a.text()==label).trigger()
            assert pet.state==state
            wait_until(lambda: pet.state==state and pet.frame==3)
            pet.grab().save(str(output/('window-'+state+'.png')))
            wait_until(lambda: pet.state=='idle',4500)
        assert pet.sprites.frames['rps'][5].toImage()!=pet.sprites.frames['running'][3].toImage()
        checks.append('rock-paper-scissors and retained thinking are separate menu actions with full animation recovery')
        pet.persist()
        stored=json.loads(pet.settings_path.read_text(encoding='utf-8'))
        assert stored['scale']==1.5 and stored['x']==pet.x() and stored['y']==pet.y()
        checks.append('position and preferences persisted')
        pet.start_state('idle')
        pet.toggle_option('random_idle',True)
        pet.toggle_option('roam',True)
        pet.toggle_option('follow_mouse',True)
        interval_menu=pet.make_menu()
        idle_menu=next(a.menu() for a in interval_menu.actions() if a.text().startswith('待机动作间隔'))
        next(a for a in idle_menu.actions() if a.text()=='10 秒').trigger()
        assert pet.settings['idle_interval']==10 and pet.idle_timer.isActive()
        assert pet.idle_timer.interval()==10000
        assert pet.walk_timer.remainingTime()>8000
        checks.append('interval menu updates action timer without postponing independent walk timer')
        pet.set_interval('idle_interval',2)
        # Use a controlled cursor position without moving the user's cursor.
        with patch.object(QCursor,'pos',return_value=pet.mapToGlobal(QPoint(pet.width()+100,pet.height()//2))):
            pet.last_interaction=0
            pet.motion_tick()
            assert pet.look is not None
            wait_until(lambda: pet.state!='idle',3000)
            assert pet.state in IDLE_REACTIONS and pet.look is None
            pet.idle_timer.stop()
            wait_until(lambda: pet.state=='idle',4000)
            pet.motion_tick()
            assert pet.look is not None
        checks.append('actual idle timer plays an action during gaze following and restores gaze afterward')
        # Check that a due walk waits for an action instead of interrupting it.
        pet.play_reaction('jumping')
        pet.idle_timer.stop()
        pet.walk_timer.start(1)
        QTest.qWait(50)
        assert pet.state=='jumping' and not pet.walk_end
        wait_until(lambda: bool(pet.walk_end),2500)
        assert pet.state in ('running-left','running-right')
        start_walk=pet.pos()
        wait_until(lambda: pet.pos()!=start_walk,1000)
        checks.append('independent walk timer retries busy state and then moves the pet')
        walking_state,walk_end=pet.state,pet.walk_end
        pet.spontaneous()
        assert pet.state==walking_state and pet.walk_end==walk_end and pet.idle_timer.isActive()
        pet.idle_timer.stop()
        checks.append('idle action also waits while a walk is active instead of interrupting it')
        pet.toggle_option('paused',True)
        assert not pet.idle_timer.isActive() and not pet.walk_timer.isActive() and not pet.walk_end
        pet.toggle_option('paused',False)
        dialog_deadline=time.monotonic()+8
        dialog_errors=[]
        dialog_seen=[]
        dialog_values=[]
        dialog_watchdog=QTimer(pet)
        dialog_watchdog.setSingleShot(True)
        def reject_stuck_dialog():
            dialog_errors.append('Custom interval dialog did not complete within 8 seconds')
            for widget in QApplication.topLevelWidgets()+pet.findChildren(QInputDialog):
                if isinstance(widget,QInputDialog) and widget.isVisible():
                    widget.reject()
        dialog_watchdog.timeout.connect(reject_stuck_dialog)
        dialog_watchdog.start(8000)
        def fill_interval_dialog():
            dialogs=[w for w in QApplication.topLevelWidgets() if isinstance(w,QInputDialog) and w.isVisible()]
            dialog=dialogs[0] if dialogs else None
            if dialog is not None:
                if not dialog_seen:
                    dialog_seen.append(time.monotonic())
                    QTimer.singleShot(250,fill_interval_dialog)
                    return
                spin=dialog.findChild(QSpinBox)
                # Hosted Cocoa desktops may ignore synthetic clicks on a modal
                # sheet. Exercise its real widgets and accepted signal without
                # depending on the runner's foreground focus.
                spin.setValue(7)
                dialog_values.append({'title':dialog.windowTitle(),'value':dialog.intValue()})
                box=dialog.findChild(QDialogButtonBox)
                box.button(QDialogButtonBox.StandardButton.Ok).click()
            elif time.monotonic()>dialog_deadline:
                dialog_errors.append('Custom interval dialog did not become visible')
                # End a nested modal event loop so a failure still produces a report.
                QApplication.instance().exit(1)
            else:
                QTimer.singleShot(100,fill_interval_dialog)
        QTimer.singleShot(250,fill_interval_dialog)
        try:
            pet.choose_interval('idle_interval','待机动作间隔')
            if sys.platform == 'darwin':
                assert pet.interval_dialog.parentWidget() is None
                assert pet.interval_dialog.windowModality()==Qt.WindowModality.ApplicationModal
            checks.append('custom interval dialog opens without blocking the event loop')
            wait_until(lambda: pet.interval_dialog is None,10000)
        finally:
            dialog_watchdog.stop()
            dialog_watchdog.deleteLater()
        assert not dialog_errors,dialog_errors
        assert pet.settings['idle_interval']==7,{'interval':pet.settings['idle_interval'],'dialogs':dialog_values}
        stored=json.loads(pet.settings_path.read_text(encoding='utf-8'))
        assert stored['idle_interval']==7
        pet.choose_interval('idle_interval','待机动作间隔')
        cancel_dialog=pet.interval_dialog
        pet.choose_interval('walk_interval','散步间隔')
        assert pet.interval_dialog is cancel_dialog
        cancel_dialog.setIntValue(99)
        QTimer.singleShot(100,cancel_dialog.reject)
        wait_until(lambda: pet.interval_dialog is None,1000)
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
        result={'ok':True,'version':APP_VERSION,'checks':checks,'click_reactions':pet.click_history,
                'platform':sys.platform,'machine':platform.machine(),
                'qt_platform':QApplication.platformName(),
                'tray_available':QSystemTrayIcon.isSystemTrayAvailable()}
        code=0
    except Exception:
        result={'ok':False,'checks':checks,'error':traceback.format_exc()}
        code=1
    (output/'smoke-test.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    QApplication.instance().exit(code)
