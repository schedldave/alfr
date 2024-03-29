#!/usr/bin/python3
# -*- coding: utf-8 -*-

import cv2  # opencv
import moderngl
import numpy as np
from PySide6.QtCore import (
    Qt,
    QSize,
    QEvent,
    Signal,
    QObject,
    QPointF,
    QRunnable,
    QWaitCondition,
    QThreadPool,
    QThread,
)
from PySide6.QtGui import (
    QImage,
    QPixmap,
    QPalette,
    QPainter,
    QMouseEvent,
    QWheelEvent,
    QAction,
)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QLabel,
    QSizePolicy,
    QScrollArea,
    QMessageBox,
    QMainWindow,
    QMenu,
    #    qApp,
    QFileDialog,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QTabWidget,
    QDoubleSpinBox,
)

import alfr

# from alfr.camera import Camera
# from alfr.shot import load_shots_from_json
from typing import Tuple, Union
from pyrr import Matrix44, Quaternion, Vector3


class RendererThread(QObject):
    shotsLoaded = Signal(list)
    renderingDone = Signal(QImage)
    # zoomEvent = Signal(QPointF)
    def __init__(
        self,
        image_label: QLabel,
        file_name: str,
        camera: Union[alfr.Camera, None] = None,
        resolution: Tuple[int, int] = (512, 512),
    ):
        super().__init__()

        self._terminate = False

        self._file_name = file_name
        self._image_label = image_label
        self._resolution = resolution

        self._camera = camera
        if self._camera is None:
            self._camera = alfr.Camera()

        # only for testing:
        self._image_label.rotateEvent.connect(
            lambda dxy: print("RT rotateEvent; shots: ", len(self._shots))
        )
        self._image_label.panEvent.connect(lambda dxy: print("RT panEvent", dxy))
        self._image_label.zoomEvent.connect(lambda dxy: print("RT zoomEvent", dxy))

        self.shotsLoaded.connect(lambda s: print(f"RT shots loaded {s}"))
        self.renderingDone.connect(lambda img: print(f"RT rendering done loaded {img}"))

    @property
    def terminate(self) -> bool:
        return self._terminate

    @terminate.setter
    def terminate(self, value: bool):
        self._terminate = value

    def run(self):
        self._ctx = moderngl.create_standalone_context()
        self._renderer = alfr.Renderer(resolution=self._resolution, ctx=self._ctx)

        self._shots = alfr.load_shots_from_json(
            self._file_name, fovy=60.0, ctx=self._ctx
        )
        self.shotsLoaded.emit(self._shots)

        while not self._terminate:
            img = self._renderer.integrate(shots=self._shots, vcam=self._camera)
            # img = self._renderer.project_shot(self._shots[0], vcam)

            # convert to uint8 and only use 3 channels (RGB)
            img = img[:, :, :3].astype("uint8")
            image = QImage(
                img.data, img.shape[1], img.shape[0], QImage.Format_RGB888
            ).rgbSwapped()
            self.renderingDone.emit(image)

        return


# https://stackoverflow.com/questions/41688668/how-to-return-mouse-coordinates-in-realtime
class MouseTracker(QLabel):
    rotateEvent = Signal(QPointF)
    panEvent = Signal(QPointF)
    zoomEvent = Signal(QPointF)

    def __init__(self):
        super().__init__()
        self.setMouseTracking(
            True
        )  # mouseMoveEvent is called when the mouse moves over the label (also when no mouse button is pressed)

        self.setMinimumSize(512, 512)
        self.setMaximumSize(512, 512)

        # self.initUI()
        # self.setMouseTracking(True)

        self._lastpos = QPointF(0, 0)

        # only for testing:
        self.rotateEvent.connect(lambda dxy: print("rotateEvent", dxy))
        self.panEvent.connect(lambda dxy: print("panEvent", dxy))
        self.zoomEvent.connect(lambda dxy: print("zoomEvnent", dxy))

    @property
    def lastpos(self) -> QPointF:
        return self._lastpos

    @lastpos.setter
    def lastpos(self, value: QPointF):
        self._lastpos = value

    def set_image(self, image: QImage):
        self.setPixmap(QPixmap.fromImage(image))
        self.setMinimumSize(image.size())
        self.setMaximumSize(image.size())
        # self._image_label.adjustSize()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:

        currpos = event.position()
        dxy = currpos - self.lastpos

        if event.buttons() == Qt.LeftButton:
            print("Mouse move mit left button at: ( %d : %d )" % (event.x(), event.y()))
            # Todo rotate
            self.rotateEvent.emit(dxy)

        elif event.buttons() == Qt.RightButton:
            print(
                "Mouse move with right button at: ( %d : %d )" % (event.x(), event.y())
            )
            # Todo pan
            self.panEvent.emit(dxy)

        elif event.buttons() == Qt.MiddleButton:
            print(
                "Mouse move with middle button at: ( %d : %d )" % (event.x(), event.y())
            )
            # Todo zoom
            self.zoomEvent.emit(dxy)

        # update last position
        self.lastpos = currpos

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # print("Mouse pressed at: ( %d : %d )" % (event.x(), event.y()))
        self.lastpos = event.position()
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        # print("Mouse released at: ( %d : %d )" % (event.x(), event.y()))
        return super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        # print("Mouse wheel at: ( %d : %d )" % (event.x(), event.y()))
        return super().wheelEvent(event)


class QuaternionWidget(QWidget):

    valueChanged = Signal(Quaternion)

    def initQDblSpinBox(self, value: float):
        q_spinbox = QDoubleSpinBox()
        q_spinbox.setRange(-1, 1)
        q_spinbox.setSingleStep(0.01)
        q_spinbox.setDecimals(3)
        q_spinbox.setValue(value)
        q_spinbox.valueChanged.connect(self._update_quaternion)

        self._layout.addWidget(q_spinbox)

        return q_spinbox

    def __init__(self, label: str, quaternion: Quaternion):
        super().__init__()
        self.setMinimumSize(200, 200)
        # self.setMaximumSize(200, 200)
        # self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._q = quaternion

        self._q_label = QLabel()
        self._q_label.setText(f"{label}")

        self._layout = QHBoxLayout()
        self._layout.addWidget(self._q_label)
        self._q0_spinbox = self.initQDblSpinBox(self._q[0])
        self._q1_spinbox = self.initQDblSpinBox(self._q[1])
        self._q2_spinbox = self.initQDblSpinBox(self._q[2])
        self._q3_spinbox = self.initQDblSpinBox(self._q[3])

        self.setLayout(self._layout)

    def _update_quaternion(self, value: float):
        # print(f"update quaternion {self._q0_spinbox.value()}")
        self._q[0] = self._q0_spinbox.value()
        self._q[1] = self._q1_spinbox.value()
        self._q[2] = self._q2_spinbox.value()
        self._q[3] = self._q3_spinbox.value()

        self.valueChanged.emit(self._q)

    @property
    def quaternion(self) -> Quaternion:
        return self._q


class Vector3Widget(QWidget):
    valueChanged = Signal(Vector3)

    def __init__(self, label: str, vec: Vector3):
        super().__init__()
        self._label = label
        self._vec = vec
        self._initUI()

    def _initUI(self):
        # self.setWindowTitle(self._label)
        self.setMinimumSize(200, 200)

        self._layout = QHBoxLayout()
        self._layout.addWidget(QLabel(self._label))

        self._spinboxes = [
            self.init_dbl_spinbox(self._vec.x),
            self.init_dbl_spinbox(self._vec.y),
            self.init_dbl_spinbox(self._vec.z),
        ]

        self.setLayout(self._layout)

    def init_dbl_spinbox(self, value: float) -> QDoubleSpinBox:
        spinbox = QDoubleSpinBox()
        spinbox.setValue(value)
        spinbox.setRange(-1000, 1000)
        spinbox.valueChanged.connect(self._on_value_changed)

        self._layout.addWidget(spinbox)

        return spinbox

    def _on_value_changed(self, value: float):
        self._vec.x = self._spinboxes[0].value()
        self._vec.y = self._spinboxes[1].value()
        self._vec.z = self._spinboxes[2].value()
        self.valueChanged.emit(self._vec)


class CameraWidget(QWidget):
    cameraChanged = Signal(alfr.Camera)

    def __init__(self, camera: alfr.Camera):
        super().__init__()
        self._camera = camera
        if self._camera is None:
            self._camera = Camera()  # create a dummy camera
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Camera")
        # self.setGeometry(300, 300, 300, 200)

        # self.setMinimumSize(300, 200)
        # self.setMaximumSize(300, 200)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        # position
        pos_widget = Vector3Widget("Position", self._camera.position)
        pos_widget.valueChanged.connect(self._on_position_changed)
        layout.addWidget(pos_widget)
        # rotation
        rot_widget = QuaternionWidget("Rotation", self._camera.rotation)
        rot_widget.valueChanged.connect(self._on_rotation_changed)
        layout.addWidget(rot_widget)
        # Todo: add modificators for rot x,y,z and changing the target ...

        # field of view
        fov_widget = QDoubleSpinBox()
        fov_widget.setRange(10, 179)  # degrees
        fov_widget.setValue(self._camera.fov_degree)
        fov_widget.setSuffix("°")
        fov_widget.valueChanged.connect(self._on_fov_changed)

        fov_layout = QHBoxLayout()
        fov_layout.addWidget(QLabel("FoV (y)"))
        fov_layout.addWidget(fov_widget)
        fov_widget = QWidget()
        fov_widget.setLayout(fov_layout)
        layout.addWidget(fov_widget)

        # aspect ratio
        ar_widget = QDoubleSpinBox()
        ar_widget.setRange(0.01, 1.0)
        ar_widget.setSingleStep(0.01)
        ar_widget.setValue(self._camera.aspect_ratio)
        ar_widget.valueChanged.connect(self._on_ar_changed)

        ar_layout = QHBoxLayout()
        ar_layout.addWidget(QLabel("Aspect Ratio"))
        ar_layout.addWidget(ar_widget)
        ar_widget = QWidget()
        ar_widget.setLayout(ar_layout)
        layout.addWidget(ar_widget)

        self.setLayout(layout)

    def _on_position_changed(self, vec: Vector3):
        # print(f"Camera position: {self._camera.position}")
        # print(f"Signal position: {vec}")
        self.cameraChanged.emit(self._camera)

    def _on_rotation_changed(self, q: Quaternion):
        # print(f"Camera rotation: {self._camera.rotation}")
        # print(f"Signal rotation: {q}")
        self.cameraChanged.emit(self._camera)

    def _on_fov_changed(self, value: float):
        self._camera.fov_degree = value
        self.cameraChanged.emit(self._camera)

    def _on_ar_changed(self, value: float):
        self._camera.aspect_ratio = value
        self.cameraChanged.emit(self._camera)


class QImageViewer(QMainWindow):

    _thread = None
    _camera = alfr.Camera()

    def __init__(self):
        super().__init__()

        self.printer = QPrinter()
        self.scaleFactor = 0.0

        self.imageLabel = MouseTracker()
        self.imageLabel.setBackgroundRole(QPalette.Base)
        # self.imageLabel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.imageLabel.setScaledContents(True)
        self.imageLabel.setVisible(True)
        # self.imageLabel.underMouse.connect(self.dblClick)

        # self.scrollArea = QScrollArea()
        # self.scrollArea.setBackgroundRole(QPalette.Dark)
        # self.scrollArea.setWidget(self.imageLabel)
        # self.scrollArea.setVisible(False)

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.West)
        tabs.setMovable(True)

        cam_widget = CameraWidget(self._camera)
        tabs.addTab(cam_widget, "Camera")

        for n, color in enumerate(["red", "green", "blue", "yellow"]):
            tabs.addTab(QLabel(color), color)

        layout = QHBoxLayout()
        layout.addWidget(self.imageLabel)
        layout.addWidget(tabs)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.createActions()
        self.createMenus()

        self.setWindowTitle("Image Viewer")
        self.resize(800, 600)

        self.init_render_thread()

    def finish_render_thread(self):

        if self._thread is not None and self._rt is not None:
            self._rt.terminate = True
            self._thread.exit(0)
            self._thread.wait(100)
            self._thread.terminate()
            self._thread.wait()
            print("thread exit!")
            # self._thread.quit()
            del self._rt
            del self._thread
            print("thread and rt deleted!")
            self._thread, self._rt = None, None
            print("thread and rt are None!")

    def init_render_thread(self, file_name=r"data\debug_scene\blender_poses.json"):
        # self._pool = QThreadPool.globalInstance()
        # self._rt = RendererThread(self.imageLabel, r"data\debug_scene\blender_poses.json")
        # print("start render thread")
        # self._pool.start(self._rt)

        self._thread = QThread()
        self._rt = RendererThread(self.imageLabel, file_name, self._camera)
        self._rt.moveToThread(self._thread)
        self._thread.started.connect(self._rt.run)

        # self._rt.finished.connect(lambda : print("_rt finished!"))
        self._thread.finished.connect(lambda x: print("_thread finished", x))

        self._rt.renderingDone.connect(self.imageLabel.set_image)

        self._thread.start()

    def open_QImage(self):
        options = QFileDialog.Options()
        # fileName = QFileDialog.getOpenFileName(self, "Open File", QDir.currentPath())
        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "QFileDialog.getOpenFileName()",
            "",
            "Images (*.png *.jpeg *.jpg *.bmp *.gif)",
            options=options,
        )
        if fileName:
            image = QImage(fileName)
            if image.isNull():
                QMessageBox.information(
                    self, "Image Viewer", "Cannot load %s." % fileName
                )
                return

            self.imageLabel.setPixmap(QPixmap.fromImage(image))
            # self.scaleFactor = 1.0

            # self.scrollArea.setVisible(True)
            # self.printAct.setEnabled(True)
            # self.fitToWindowAct.setEnabled(True)
            # self.updateActions()

            # if not self.fitToWindowAct.isChecked():
            #    self.imageLabel.adjustSize()

    def open_json(self):
        options = QFileDialog.Options()
        # fileName = QFileDialog.getOpenFileName(self, "Open File", QDir.currentPath())
        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "QFileDialog.getOpenFileName()",
            "",
            "JSON (*.json)",
            options=options,
        )
        if fileName:
            if not os.path.isfile(fileName):
                QMessageBox.information(
                    self, "Light-Field Viewer", "Cannot load %s." % fileName
                )
                return
        else:
            return

        self.finish_render_thread()
        self.init_render_thread(fileName)

    def open_cv2_old(self):
        options = QFileDialog.Options()
        # fileName = QFileDialog.getOpenFileName(self, "Open File", QDir.currentPath())
        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "QFileDialog.getOpenFileName()",
            "",
            "Images (*.png *.jpeg *.jpg *.bmp *.gif)",
            options=options,
        )
        if fileName:
            img = cv2.imread(fileName)
            if img is None:
                QMessageBox.information(
                    self, "Image Viewer", "Cannot load %s." % fileName
                )
                return

            img = img.astype("uint8")
            image = QImage(
                img.data, img.shape[1], img.shape[0], QImage.Format_RGB888
            ).rgbSwapped()
            self.imageLabel.setPixmap(QPixmap.fromImage(image))
            self.scaleFactor = 1.0

            # self.scrollArea.setVisible(True)
            self.printAct.setEnabled(True)
            self.fitToWindowAct.setEnabled(True)
            self.updateActions()

            if not self.fitToWindowAct.isChecked():
                self.imageLabel.adjustSize()

    def print_(self):
        dialog = QPrintDialog(self.printer, self)
        if dialog.exec_():
            painter = QPainter(self.printer)
            rect = painter.viewport()
            size = self.imageLabel.pixmap().size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(self.imageLabel.pixmap().rect())
            painter.drawPixmap(0, 0, self.imageLabel.pixmap())

    def zoomIn(self):
        self.scaleImage(1.25)

    def zoomOut(self):
        self.scaleImage(0.8)

    def normalSize(self):
        self.imageLabel.adjustSize()
        self.scaleFactor = 1.0

    def fitToWindow(self):
        fitToWindow = self.fitToWindowAct.isChecked()
        # self.scrollArea.setWidgetResizable(fitToWindow)
        if not fitToWindow:
            self.normalSize()

        self.updateActions()

    def about(self):
        QMessageBox.about(
            self,
            "About Image Viewer",
            "<p>The <b>Image Viewer</b> example shows how to combine "
            "QLabel and QScrollArea to display an image. QLabel is "
            "typically used for displaying text, but it can also display "
            "an image. QScrollArea provides a scrolling view around "
            "another widget. If the child widget exceeds the size of the "
            "frame, QScrollArea automatically provides scroll bars.</p>"
            "<p>The example demonstrates how QLabel's ability to scale "
            "its contents (QLabel.scaledContents), and QScrollArea's "
            "ability to automatically resize its contents "
            "(QScrollArea.widgetResizable), can be used to implement "
            "zooming and scaling features.</p>"
            "<p>In addition the example shows how to use QPainter to "
            "print an image.</p>",
        )

    def createActions(self):
        self.openAct = QAction(
            "&Open...", self, shortcut="Ctrl+O", triggered=self.open_json
        )
        self.printAct = QAction(
            "&Print...", self, shortcut="Ctrl+P", enabled=False, triggered=self.print_
        )
        self.exitAct = QAction("E&xit", self, shortcut="Ctrl+Q", triggered=self.close)
        self.zoomInAct = QAction(
            "Zoom &In (25%)",
            self,
            shortcut="Ctrl++",
            enabled=False,
            triggered=self.zoomIn,
        )
        self.zoomOutAct = QAction(
            "Zoom &Out (25%)",
            self,
            shortcut="Ctrl+-",
            enabled=False,
            triggered=self.zoomOut,
        )
        self.normalSizeAct = QAction(
            "&Normal Size",
            self,
            shortcut="Ctrl+S",
            enabled=False,
            triggered=self.normalSize,
        )
        self.fitToWindowAct = QAction(
            "&Fit to Window",
            self,
            enabled=False,
            checkable=True,
            shortcut="Ctrl+F",
            triggered=self.fitToWindow,
        )
        self.aboutAct = QAction("&About", self, triggered=self.about)
        self.aboutQtAct = QAction("About &Qt", self, triggered=qApp.aboutQt)

    def createMenus(self):
        self.fileMenu = QMenu("&File", self)
        self.fileMenu.addAction(self.openAct)
        self.fileMenu.addAction(self.printAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAct)

        self.viewMenu = QMenu("&View", self)
        self.viewMenu.addAction(self.zoomInAct)
        self.viewMenu.addAction(self.zoomOutAct)
        self.viewMenu.addAction(self.normalSizeAct)
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(self.fitToWindowAct)

        self.helpMenu = QMenu("&Help", self)
        self.helpMenu.addAction(self.aboutAct)
        self.helpMenu.addAction(self.aboutQtAct)

        self.menuBar().addMenu(self.fileMenu)
        self.menuBar().addMenu(self.viewMenu)
        self.menuBar().addMenu(self.helpMenu)

    def updateActions(self):
        self.zoomInAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.zoomOutAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.normalSizeAct.setEnabled(not self.fitToWindowAct.isChecked())

    def scaleImage(self, factor):
        self.scaleFactor *= factor
        self.imageLabel.resize(self.scaleFactor * self.imageLabel.pixmap().size())

        self.adjustScrollBar(self.scrollArea.horizontalScrollBar(), factor)
        self.adjustScrollBar(self.scrollArea.verticalScrollBar(), factor)

        self.zoomInAct.setEnabled(self.scaleFactor < 3.0)
        self.zoomOutAct.setEnabled(self.scaleFactor > 0.333)

    def adjustScrollBar(self, scrollBar, factor):
        scrollBar.setValue(
            int(factor * scrollBar.value() + ((factor - 1) * scrollBar.pageStep() / 2))
        )


if __name__ == "__main__":
    import sys
    import os
    from PySide6.QtWidgets import QApplication

    # os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    # app.setAttribute(Qt.AA_EnableHighDpiScaling)
    imageViewer = QImageViewer()
    imageViewer.show()
    sys.exit(app.exec())
    # TODO QScrollArea support mouse
    # base on https://github.com/baoboa/pyqt5/blob/master/examples/widgets/imageviewer.py
    #
    # if you need Two Image Synchronous Scrolling in the window by PyQt5 and Python 3
    # please visit https://gist.github.com/acbetter/e7d0c600fdc0865f4b0ee05a17b858f2
