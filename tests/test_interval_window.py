import os
import unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from interval_window import IntervalWindow


class IntervalWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def make_window(self):
        window=IntervalWindow()
        window.setIntRange(2,300)
        window.setIntValue(10)
        self.addCleanup(window.deleteLater)
        return window

    def test_typed_seconds_are_committed_once_on_accept(self):
        window=self.make_window()
        saved=[];finished=[]
        window.accepted.connect(lambda:saved.append(window.intValue()))
        window.finished.connect(finished.append)
        window.spin.lineEdit().setText('17')
        window.accept()
        window.accept()
        self.assertEqual(saved,[17])
        self.assertEqual(finished,[1])

    def test_cancel_does_not_emit_save(self):
        window=self.make_window()
        saved=[];finished=[]
        window.accepted.connect(lambda:saved.append(window.intValue()))
        window.finished.connect(finished.append)
        window.setIntValue(99)
        window.reject()
        window.close()
        self.assertEqual(saved,[])
        self.assertEqual(finished,[0])

    def test_seconds_remain_within_allowed_range(self):
        window=self.make_window()
        window.setIntValue(1)
        self.assertEqual(window.intValue(),2)
        window.setIntValue(500)
        self.assertEqual(window.intValue(),300)


if __name__=='__main__':unittest.main()
