"""Schwi desktop companion. Local animations only; no online services."""
from __future__ import annotations

import argparse
import hashlib
import faulthandler
import json
import logging
import os
from pathlib import Path
import random
import sys
import time

from PySide6.QtCore import QLockFile, QPoint, QRect, QTimer, Qt
from PySide6.QtGui import QActionGroup, QCursor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QInputDialog, QMenu, QMessageBox, QSystemTrayIcon, QWidget

from behavior import DEFAULTS, IDLE_REACTIONS, ReactionBag, clamp_position, direction_index, load_settings, save_settings
from platform_support import APP_VERSION, default_data_dir

VERSION = APP_VERSION
IS_MAC = sys.platform == 'darwin'
CELL_W, CELL_H = 192, 208
STATES = {
    'idle': (0, [650, 160, 180, 120, 180, 750]),
    'running-right': (1, [95] * 8),
    'running-left': (2, [95] * 8),
    'waving': (3, [250, 240, 320, 320]),
    'jumping': (4, [160, 140, 230, 140, 250]),
    'failed': (5, [180, 220, 280, 330, 600, 280, 220, 220]),
    'waiting': (6, [220, 260, 450, 650, 280, 220]),
    'running': (7, [220, 350, 500, 400, 400, 300]),
    'review': (8, [250, 300, 300, 400, 500, 300]),
}
EXTRAS = {
    'shy': [180, 300, 650, 950, 450, 500],
    'happy': [200, 300, 700, 500, 300, 350],
    'surprised': [180, 260, 500, 650, 300, 350],
    'excited': [220, 160, 190, 160, 240, 350],
    'sleepy': [400, 500, 650, 850, 450, 350],
}
LABELS = {
    'shy': '害羞', 'happy': '开心', 'surprised': '惊讶',
    'excited': '兴奋', 'sleepy': '打瞌睡',
    'waving': '挥挥手', 'jumping': '跳一下', 'waiting': '期待',
    'running': '认真思考', 'review': '探头看看', 'failed': '有点失落',
}


def resource_path(name):
    return Path(__file__).resolve().parent / 'assets' / name


class Sprites:
    def __init__(self):
        atlas = QImage(str(resource_path('schwi.png')))
        if atlas.size().width() != 1536 or atlas.size().height() != 2288:
            raise RuntimeError('休比的动作素材缺失或损坏，请重新解压完整软件包。')
        self.frames = {}
        self.durations = {}
        for name, (row, times) in STATES.items():
            self.frames[name] = [QPixmap.fromImage(atlas.copy(i * CELL_W, row * CELL_H, CELL_W, CELL_H)) for i in range(len(times))]
            self.durations[name] = times
        self.looks = [QPixmap.fromImage(atlas.copy((i % 8) * CELL_W, (9 + i // 8) * CELL_H, CELL_W, CELL_H)) for i in range(16)]
        for name, times in EXTRAS.items():
            strip = QImage(str(resource_path(name + '.png')))
            if strip.width() != 6 * CELL_W or strip.height() != CELL_H:
                raise RuntimeError('互动表情素材缺失：' + name)
            self.frames[name] = [QPixmap.fromImage(strip.copy(i * CELL_W, 0, CELL_W, CELL_H)) for i in range(6)]
            self.durations[name] = times
        self.icon = QIcon(str(resource_path('schwi-portrait.png')))
        if self.icon.isNull():
            raise RuntimeError('休比的程序图标缺失，请重新解压完整软件包。')


class PetWindow(QWidget):
    def __init__(self, sprites: Sprites, data_dir: Path, *, test_mode=False):
        super().__init__()
        self.sprites = sprites
        self.data_dir = data_dir
        self.settings_path = data_dir / 'settings.json'
        self.settings = load_settings(self.settings_path)
        self.test_mode = test_mode
        self.setWindowTitle('休比桌宠')
        self.setWindowIcon(sprites.icon)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        if IS_MAC:
            self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setMouseTracking(True)
        self.apply_window_flags()
        self.resize(round(CELL_W * self.settings['scale']), round(CELL_H * self.settings['scale']))
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip('单击互动 · 双击跳跃 · 按住拖动 · 右键菜单')
        self.state = 'idle'
        self.frame = 0
        self.remaining_loops = 1
        self.look = None
        self.reactions = ReactionBag()
        self.click_history = []
        self.press_global = None
        self.press_window = None
        self.last_drag_global = None
        self.drag_direction = 1
        self.dragging = False
        self.double_click = False
        self.menu_open = False
        self.walk_end = 0.0
        self.walk_direction = 1
        self.last_tick = time.monotonic()
        self.last_interaction = 0.0
        self.tray = None
        self.before_quit = None
        self.quitting = False
        self.frame_timer = QTimer(self)
        self.frame_timer.setSingleShot(True)
        self.frame_timer.timeout.connect(self.advance_frame)
        self.click_timer = QTimer(self)
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self.react)
        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self.spontaneous)
        self.walk_timer = QTimer(self)
        self.walk_timer.setSingleShot(True)
        self.walk_timer.timeout.connect(self.spontaneous_walk)
        self.motion_timer = QTimer(self)
        self.motion_timer.setInterval(40)
        self.motion_timer.timeout.connect(self.motion_tick)
        self.motion_timer.start()
        self.restore_position()
        self.make_tray()
        QApplication.instance().screenAdded.connect(self.screen_changed)
        QApplication.instance().screenRemoved.connect(self.screen_changed)
        for screen in QApplication.screens():
            screen.availableGeometryChanged.connect(self.screen_changed)
        self.start_state('idle')
        self.schedule_idle()
        self.schedule_walk()

    def apply_window_flags(self):
        # A macOS Tool is an NSPanel, which remains above normal windows even
        # without WindowStaysOnTopHint. Use a regular borderless window there.
        kind = Qt.WindowType.Window if IS_MAC else Qt.WindowType.Tool
        flags = Qt.WindowType.FramelessWindowHint | kind | Qt.WindowType.WindowDoesNotAcceptFocus
        if self.settings['topmost']:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def current_screen(self):
        return QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()

    def keep_on_screen(self, target: QPoint, screen=None):
        screen = screen or QApplication.screenAt(target + self.rect().center()) or self.current_screen()
        r = screen.availableGeometry()
        return QPoint(*clamp_position(target.x(), target.y(), self.width(), self.height(), (r.x(), r.y(), r.width(), r.height())))

    def restore_position(self):
        if self.settings['x'] is not None and self.settings['y'] is not None:
            target = QPoint(self.settings['x'], self.settings['y'])
            screen = QApplication.screenAt(target + self.rect().center())
            if screen:
                self.move(self.keep_on_screen(target, screen))
                return
        self.reset_position(save=False)

    def reset_position(self, checked=False, *, save=True):
        r = QApplication.primaryScreen().availableGeometry()
        self.move(self.keep_on_screen(QPoint(r.right() - self.width() - 40, r.bottom() - self.height() - 12), QApplication.primaryScreen()))
        if save:
            self.persist()
        self.reveal()

    def persist(self):
        self.settings['x'], self.settings['y'] = self.x(), self.y()
        try:
            save_settings(self.settings_path, self.settings)
        except OSError:
            logging.exception('Unable to save settings')

    def screen_changed(self, *args):
        self.move(self.keep_on_screen(self.pos()))
        self.persist()

    def current_pixmap(self):
        if self.look is not None and self.state == 'idle' and not self.settings['paused']:
            return self.sprites.looks[self.look]
        return self.sprites.frames[self.state][self.frame]

    def paintEvent(self, event):
        painter = QPainter(self)
        # Replace the entire previous transparent frame, including hair edges.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(self.rect(), self.current_pixmap())

    def start_state(self, name, *, loops=1, force=False):
        if self.settings['paused'] and not force:
            return
        self.frame_timer.stop()
        self.state, self.frame, self.remaining_loops = name, 0, loops
        self.look = None
        self.update()
        if not self.settings['paused'] and self.isVisible():
            self.frame_timer.start(self.sprites.durations[name][0])

    def advance_frame(self):
        if self.settings['paused'] or not self.isVisible() or self.menu_open:
            return
        self.frame += 1
        if self.frame == len(self.sprites.frames[self.state]):
            self.frame = 0
            if self.state not in ('idle', 'running-left', 'running-right'):
                self.remaining_loops -= 1
                if self.remaining_loops <= 0:
                    self.start_state('idle')
                    return
        self.update()
        self.frame_timer.start(self.sprites.durations[self.state][self.frame])

    def turn_running(self, name):
        if self.state in ('running-left', 'running-right'):
            # Opposite directions share the same stride phase. Keep its timer.
            self.state = name
            self.look = None
            self.update()
        else:
            self.start_state(name)

    def react(self):
        if self.settings['paused'] or self.dragging or self.menu_open or not self.isVisible():
            return
        name = self.reactions.next()
        self.click_history.append(name)
        self.click_history = self.click_history[-64:]
        self.play_reaction(name)

    def play_reaction(self, name):
        self.walk_end = 0
        self.last_interaction = time.monotonic()
        self.start_state(name)
        self.schedule_idle()
        self.schedule_walk()

    def schedule_idle(self, *, retry=False):
        self.idle_timer.stop()
        if self.settings['random_idle'] and not self.settings['paused'] and self.isVisible():
            self.idle_timer.start(500 if retry else self.settings['idle_interval'] * 1000)

    def schedule_walk(self, *, retry=False):
        self.walk_timer.stop()
        if self.settings['random_idle'] and self.settings['roam'] and not self.settings['paused'] and self.isVisible():
            self.walk_timer.start(500 if retry else self.settings['walk_interval'] * 1000)

    def ready_for_auto_action(self):
        return (self.settings['random_idle'] and not self.settings['paused'] and self.isVisible()
                and self.state == 'idle' and not self.dragging and self.press_global is None
                and not self.menu_open)

    def spontaneous(self):
        ready = self.ready_for_auto_action()
        if ready:
            self.start_state(random.choice(IDLE_REACTIONS))
        self.schedule_idle(retry=not ready)

    def spontaneous_walk(self):
        ready = self.settings['roam'] and self.ready_for_auto_action()
        if ready:
            self.begin_walk()
        self.schedule_walk(retry=not ready)

    def begin_walk(self):
        self.look = None
        self.walk_direction = random.choice((-1, 1))
        self.walk_end = time.monotonic() + random.uniform(2.0, 4.0)
        self.start_state('running-right' if self.walk_direction > 0 else 'running-left')

    def motion_tick(self):
        now = time.monotonic()
        dt, self.last_tick = min(now - self.last_tick, .1), now
        if not self.isVisible() or self.settings['paused'] or self.dragging or self.menu_open or self.press_global is not None:
            return
        if self.walk_end:
            if now >= self.walk_end:
                self.walk_end = 0
                self.start_state('idle')
                self.persist()
            else:
                target = self.pos() + QPoint(round(self.walk_direction * 70 * dt), 0)
                safe = self.keep_on_screen(target, self.current_screen())
                if safe.x() != target.x():
                    self.walk_direction *= -1
                    self.turn_running('running-right' if self.walk_direction > 0 else 'running-left')
                self.move(safe)
            return
        old = self.look
        self.look = None
        if self.settings['follow_mouse'] and self.state == 'idle' and now - self.last_interaction > 2:
            eye = self.mapToGlobal(QPoint(self.width() // 2, round(self.height() * .42)))
            delta = QCursor.pos() - eye
            distance = delta.manhattanLength()
            if 70 < distance < 850:
                self.look = direction_index(delta.x(), delta.y())
        if old != self.look:
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_global = event.globalPosition().toPoint()
            self.press_window = self.pos()
            self.last_drag_global = self.press_global
            self.dragging = False
            self.double_click = False
            self.walk_end = 0
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        if self.press_global is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        current = event.globalPosition().toPoint()
        delta = current - self.press_global
        step = current - self.last_drag_global
        self.last_drag_global = current
        if delta.manhattanLength() >= QApplication.startDragDistance():
            self.dragging = True
            self.click_timer.stop()
        if self.dragging:
            self.move(self.keep_on_screen(self.press_window + delta))
            if step.x():
                self.drag_direction = 1 if step.x() > 0 else -1
            name = 'running-right' if self.drag_direction > 0 else 'running-left'
            if self.state != name and not self.settings['paused']:
                self.turn_running(name)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.press_global is None:
            return
        was_dragged = self.dragging
        self.press_global, self.press_window = None, None
        self.last_drag_global = None
        self.dragging = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if was_dragged:
            self.persist()
            self.start_state('idle')
            self.schedule_idle()
            self.schedule_walk()
        elif not self.double_click and not self.settings['paused']:
            self.click_timer.start(QApplication.doubleClickInterval() + 25)
        self.double_click = False
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.click_timer.stop()
            self.double_click = True
            self.press_global = event.globalPosition().toPoint()
            self.press_window = self.pos()
            self.last_drag_global = self.press_global
            if not self.settings['paused']:
                self.play_reaction('jumping')
            event.accept()

    def contextMenuEvent(self, event):
        self.click_timer.stop()
        self.menu_open = True
        self.frame_timer.stop()
        menu = self.make_menu()
        menu.exec(event.globalPos())
        menu.deleteLater()
        self.menu_open = False
        if not self.settings['paused'] and self.isVisible():
            self.frame_timer.start(self.sprites.durations[self.state][self.frame])

    def make_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet('QMenu { background:#fff8f3; color:#48243f; border:1px solid #d5b3c0; padding:5px; font-family:"Microsoft YaHei UI"; font-size:12px; } QMenu::item { padding:6px 22px; border-radius:4px; } QMenu::item:selected { background:#f4d7df; } QMenu::separator { height:1px; background:#ead4dc; margin:4px 6px; }')
        if IS_MAC:
            menu.setStyleSheet(menu.styleSheet().replace('Microsoft YaHei UI', 'PingFang SC'))
        title = menu.addAction('休比 · 离线陪伴')
        title.setEnabled(False)
        actions = menu.addMenu('和休比互动')
        for state, label in LABELS.items():
            action = actions.addAction(label)
            action.setEnabled(not self.settings['paused'])
            action.triggered.connect(lambda checked=False, s=state: self.play_reaction(s))
        actions.addSeparator()
        a = actions.addAction('随机一个动作')
        a.setEnabled(not self.settings['paused'])
        a.triggered.connect(lambda: self.play_reaction(self.reactions.next()))
        sizes = menu.addMenu('桌宠大小')
        group = QActionGroup(sizes)
        for scale, label in ((.75,'小 · 75%'),(1.0,'标准 · 100%'),(1.25,'舒适 · 125%'),(1.5,'大 · 150%'),(2.0,'特大 · 200%')):
            a = sizes.addAction(label)
            a.setCheckable(True)
            a.setChecked(self.settings['scale'] == scale)
            group.addAction(a)
            a.triggered.connect(lambda checked=False, s=scale: self.change_scale(s))
        menu.addSeparator()
        for key, label in (('topmost','始终置顶'),('random_idle','偶尔自己做动作'),('follow_mouse','视线跟随鼠标'),('roam','允许小范围散步'),('paused','暂停动画与互动')):
            a = menu.addAction(label)
            a.setCheckable(True)
            a.setChecked(self.settings[key])
            a.triggered.connect(lambda checked, k=key: self.toggle_option(k, checked))
        self.add_interval_menu(menu, 'idle_interval', '待机动作间隔', (2, 4, 6, 10, 20, 30))
        self.add_interval_menu(menu, 'walk_interval', '散步间隔', (5, 10, 15, 20, 30, 60))
        menu.addSeparator()
        menu.addAction('找回休比 / 重置位置', self.reset_position)
        if self.tray is not None:
            menu.addAction('暂时收起' if self.isVisible() else '显示休比', self.hide_pet if self.isVisible() else self.reveal)
        menu.addAction('使用说明', self.show_help)
        menu.addAction('退出桌宠', self.quit_app)
        return menu

    def add_interval_menu(self, menu, key, title, choices):
        seconds = self.settings[key]
        submenu = menu.addMenu(f'{title} · {seconds} 秒')
        group = QActionGroup(submenu)
        for value in choices:
            action = submenu.addAction(f'{value} 秒')
            action.setCheckable(True)
            action.setChecked(seconds == value)
            group.addAction(action)
            action.triggered.connect(lambda checked=False, k=key, v=value: self.set_interval(k, v))
        submenu.addSeparator()
        action = submenu.addAction('自定义…')
        action.triggered.connect(lambda checked=False, k=key, t=title: self.choose_interval(k, t))

    def set_interval(self, key, seconds):
        self.settings[key] = max(2, min(300, int(seconds)))
        (self.schedule_idle if key == 'idle_interval' else self.schedule_walk)()
        self.persist()
        self.refresh_tray_menu()

    def choose_interval(self, key, title):
        was_open = self.menu_open
        self.menu_open = True
        self.frame_timer.stop()
        try:
            seconds, accepted = QInputDialog.getInt(
                self, title, '间隔（秒，2–300）：', self.settings[key], 2, 300, 1)
            if accepted:
                self.set_interval(key, seconds)
        finally:
            self.menu_open = was_open
            if not self.menu_open and not self.settings['paused'] and self.isVisible():
                self.frame_timer.start(self.sprites.durations[self.state][self.frame])

    def change_scale(self, scale):
        center = self.x() + self.width() / 2
        bottom = self.y() + self.height()
        self.settings['scale'] = scale
        self.resize(round(CELL_W * scale), round(CELL_H * scale))
        self.move(self.keep_on_screen(QPoint(round(center - self.width() / 2), bottom - self.height())))
        self.persist()
        self.update()
        self.refresh_tray_menu()

    def toggle_option(self, key, checked):
        self.settings[key] = checked
        if key == 'topmost':
            position = self.pos()
            self.apply_window_flags()
            self.move(position)
            self.show()
        if key == 'paused':
            self.click_timer.stop()
            self.walk_end = 0
            self.start_state('idle', force=True)
        if key in ('roam', 'random_idle') and not checked and self.walk_end:
            self.walk_end = 0
            self.start_state('idle')
        if key == 'follow_mouse':
            self.look = None
            self.update()
        if key in ('topmost','paused') and not self.settings['paused']:
            self.frame_timer.start(self.sprites.durations[self.state][self.frame])
        self.schedule_idle()
        self.schedule_walk()
        self.persist()
        self.refresh_tray_menu()

    def make_tray(self):
        if self.test_mode or not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self.sprites.icon, self)
        self.tray.setToolTip('休比桌宠 · 点击打开菜单' if IS_MAC else '休比桌宠 · 单击显示，右键菜单')
        self.tray.activated.connect(self.tray_activated)
        self.refresh_tray_menu()
        self.tray.show()

    def refresh_tray_menu(self):
        if self.tray:
            old = self.tray.contextMenu()
            self.tray.setContextMenu(self.make_menu())
            if old:
                old.deleteLater()

    def tray_activated(self, reason):
        # macOS opens its menu on mouse press; do not rebuild that open menu.
        if not IS_MAC and reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.reveal()

    def hide_pet(self):
        if not self.tray:
            return
        self.walk_end = 0
        self.frame_timer.stop()
        self.click_timer.stop()
        self.idle_timer.stop()
        self.walk_timer.stop()
        self.hide()
        self.refresh_tray_menu()

    def reveal(self):
        self.show()
        self.raise_()
        if hasattr(self, 'frame_timer'):
            self.start_state('idle', force=True)
            self.schedule_idle()
            self.schedule_walk()
            self.refresh_tray_menu()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'frame_timer') and not self.settings['paused']:
            self.frame_timer.start(self.sprites.durations[self.state][self.frame])
            self.schedule_idle()
            self.schedule_walk()

    def show_help(self):
        tray_help = '顶部菜单栏图标：显示、收起或退出休比。' if IS_MAC else '托盘图标：找回或退出休比。'
        QMessageBox.information(self, '休比桌宠',
            f'休比桌宠 {VERSION}\n\n单击：随机表情或动作，不会连续重复。\n双击：跳一下。\n按住左键：拖动休比。\n右键：指定动作、调整大小和偏好。\n{tray_help}\n\n待机动作默认间隔 4 秒，散步默认间隔 10 秒；右键菜单可设置间隔或输入自定义秒数。\n动作进行中会稍后执行，不会互相打断。\n视线跟随和散步默认关闭，可在菜单开启。\n所有互动均在本机运行。')

    def quit_app(self):
        if self.quitting:
            return
        self.quitting = True
        self.persist()
        if self.before_quit:
            self.before_quit()
        if self.tray:
            self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        self.quit_app()
        event.accept()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--self-test', type=Path)
    parser.add_argument('--quit-after', type=float)
    args = parser.parse_args()
    data_dir = args.data_dir or default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=str(data_dir / 'app.log'), encoding='utf-8', level=logging.WARNING,
                        format='%(asctime)s %(levelname)s %(message)s')
    fault_log = (data_dir / 'native-crash.log').open('a', encoding='utf-8')
    faulthandler.enable(file=fault_log)
    app = QApplication(sys.argv[:1])
    app.setApplicationName('SchwiDesktopPet')
    app.setApplicationVersion(VERSION)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle('Fusion')
    lock = QLockFile(str(data_dir / 'instance.lock'))
    lock.setStaleLockTime(0)
    def trace_lifecycle(event):
        if args.quit_after:
            with (data_dir / 'lifecycle.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps({'event': event, 'pid': os.getpid(),
                                         'locked': lock.isLocked(),
                                         'file_exists': (data_dir / 'instance.lock').exists()}) + '\n')
    pipe_name = 'schwi-pet-' + hashlib.sha256(str(data_dir.resolve()).encode()).hexdigest()[:18]
    if not args.self_test and not lock.tryLock(200):
        trace_lifecycle('secondary-instance')
        socket = QLocalSocket()
        socket.connectToServer(pipe_name)
        if socket.waitForConnected(1800):
            socket.write(b'show')
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
        return 0
    trace_lifecycle('primary-started')
    try:
        sprites = Sprites()
        pet = PetWindow(sprites, data_dir, test_mode=bool(args.self_test))
    except Exception:
        logging.exception('Startup failed')
        QMessageBox.critical(None, '休比桌宠无法启动', '程序或素材不完整，请重新解压软件包。详细信息已写入本机日志。')
        return 1
    server = QLocalServer()
    if not args.self_test:
        QLocalServer.removeServer(pipe_name)
        server.listen(pipe_name)

        def receive():
            while server.hasPendingConnections():
                client = server.nextPendingConnection()
                client.readyRead.connect(lambda c=client: c.readAll())
                client.disconnected.connect(client.deleteLater)
                pet.reveal()
        server.newConnection.connect(receive)
    pet.show()
    if args.quit_after:
        QTimer.singleShot(round(args.quit_after * 1000), pet.quit_app)
    if args.self_test:
        from smoke_test import run_smoke_test
        QTimer.singleShot(250, lambda: run_smoke_test(pet, args.self_test))
    def cleanup():
        # On macOS, application termination may not return through app.exec().
        # Release IPC and the instance lock before native application teardown.
        trace_lifecycle('cleanup-start')
        pet.frame_timer.stop()
        pet.motion_timer.stop()
        pet.idle_timer.stop()
        pet.walk_timer.stop()
        pet.click_timer.stop()
        server.close()
        lock.unlock()
        trace_lifecycle('cleanup-finished')

    pet.before_quit = cleanup
    app.aboutToQuit.connect(cleanup)
    result = app.exec()
    cleanup()
    faulthandler.disable()
    fault_log.close()
    return result


if __name__ == '__main__':
    raise SystemExit(main())
