from testtagqt import *

import sys
from PyQt5.QtWidgets import QApplication, QSlider, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from OCC.Display.SimpleGui import init_display
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Pln
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace

# Initialize the OCC display
display, start_display, add_menu, add_function_to_menu = init_display()

# Global handle for the plane
plane_handle = None

# Function to show the plane at the current z-height
def show_plane_at_z(z_val):
    global plane_handle
    if plane_handle:
        display.Context.Remove(plane_handle, True)

    # Create a new plane at the specified height (z_val)
    plane = gp_Pln(gp_Pnt(0, 0, z_val), gp_Dir(0, 0, 1))
    face = BRepBuilderAPI_MakeFace(plane, -1000, 1000, -1000, 1000).Shape()

    # Display the plane
    plane_handle = display.DisplayShape(face, update=True, color='RED', transparency=0.5)

# Function to handle slider value change
def on_slider_change(value):
    show_plane_at_z(value)

# Create the Qt application
app = QApplication(sys.argv)

# Create a widget and layout for the slider
window = QWidget()
layout = QVBoxLayout()

# Create the slider widget
slider = QSlider(Qt.Horizontal)
slider.setRange(-500, 500)  # Set range for the plane height
slider.setValue(0)  # Initial value
slider.valueChanged.connect(on_slider_change)  # Connect slider change to function

# Add the slider to the layout
layout.addWidget(slider)

# The way to get the QWidget from the OCC display in your version might be different
# For example, `display._viewer` might give access to the widget, or `display._QWidget`
# Try this approach if _QWidget or _viewer isn't working.

# Check for display's QWidget or viewer widget
occ_widget = display._viewer.GetWidget() if hasattr(display, '_viewer') else None

# If occ_widget is found, embed it into the layout
if occ_widget:
    layout.addWidget(occ_widget)

# Set the layout for the main window
window.setLayout(layout)

# Show the window with the slider and the display
window.setWindowTitle("OCC Display with Slider")
window.show()

# Add a menu option to trigger the interactive plane adjustment
add_menu("Tools")
add_function_to_menu("Tools", lambda: None)  # Empty function to prevent blocking

# Start the OCC display and the event loop
start_display()  # This keeps the display running and interactive
app.exec_()  # Start the Qt event loop
