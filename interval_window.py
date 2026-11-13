"""A regular Cocoa window for interval settings in an LSUIElement application."""
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSpinBox, QDialogButtonBox


class IntervalWindow(QWidget):
    accepted=Signal()
    finished=Signal(int)

    def __init__(self):
        super().__init__(None,Qt.WindowType.Window)
        self._completed=False
        self.setMinimumWidth(280)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(18,18,18,18)
        self.label=QLabel(self)
        self.spin=QSpinBox(self)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel,self)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText('确定')
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        layout.addWidget(self.label)
        layout.addWidget(self.spin)
        layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        for key,callback in [(Qt.Key.Key_Escape,self.reject),(Qt.Key.Key_Return,self.accept),(Qt.Key.Key_Enter,self.accept)]:
            shortcut=QShortcut(QKeySequence(key),self)
            shortcut.activated.connect(callback)

    def setLabelText(self,text):self.label.setText(text)
    def setIntRange(self,low,high):self.spin.setRange(low,high)
    def setIntStep(self,step):self.spin.setSingleStep(step)
    def setIntValue(self,value):self.spin.setValue(value)
    def intValue(self):return self.spin.value()

    def complete(self,result):
        if self._completed:return
        self._completed=True
        self.spin.interpretText()
        if result:self.accepted.emit()
        self.hide()
        self.finished.emit(result)
        self.close()

    def accept(self):self.complete(1)
    def reject(self):self.complete(0)

    def closeEvent(self,event):
        if not self._completed:self.reject()
        event.accept()
