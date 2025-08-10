from QPanda3D.Panda3DWorld import Panda3DWorld
from QPanda3D.QPanda3DWidget import QPanda3DWidget
from PySide6.QtWidgets import QApplication, QMainWindow
import sys
from panda3d.core import Vec3, VBase4


class PandaTest(Panda3DWorld):
    """
    This is the class that defines our world.
    It inherits from Panda3DWorld that inherits from
    Panda3D's ShowBase class.
    """

    def __init__(self):
        # This call initializes ShowBase and creates self.loader, self.render, etc.
        Panda3DWorld.__init__(self)

        # --- Now we can safely use the attributes created by ShowBase ---
        self.cam.setPos(0, -28, 6)
        self.win.setClearColorActive(True)
        self.win.setClearColor(VBase4(0, 0.5, 0, 1))  # Green background

        # --- FIX #1: Use self.loader ---
        self.testModel = self.loader.loadModel('panda')

        # --- FIX #2: Use self.render ---
        self.testModel.reparentTo(self.render)

        # This rotates the actor 180 degrees on heading and 90 degrees on pitch.
        myInterval4 = self.testModel.hprInterval(1.0, Vec3(360, 0, 0))
        myInterval4.loop()


if __name__ == "__main__":
    # 1. Create an instance of our world logic
    world = PandaTest()

    # 2. Set up the Qt Application
    app = QApplication(sys.argv)
    appw = QMainWindow()
    appw.setGeometry(50, 50, 800, 600)

    # 3. Create the QPanda3DWidget and pass it our world instance
    pandaWidget = QPanda3DWidget(world)

    # 4. Set the widget as the main content and show the window
    appw.setCentralWidget(pandaWidget)
    appw.show()

    sys.exit(app.exec())