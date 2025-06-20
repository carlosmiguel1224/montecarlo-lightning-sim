from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout,QWidget,QFileDialog,QMessageBox, QListWidget
)
from PyQt5.QtGui import QFont, QPalette, QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import sys
import sqlite3
import csv

class ShapeInfoDialog(QDialog):
    def __init__(self, shape_data, SIM_ID, db_path="collisions.db", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shape Information")
        self.shape_id = shape_data.get('structurestruck') or f"shapeid:{shape_data['id']}"
        self.sim_id = SIM_ID  # ← Store SIM_ID
        self.db_path = db_path

        layout = QVBoxLayout()

        info = (
            f"<b>ID:</b> {shape_data['id']}<br>"
            f"<b>Name:</b> {shape_data.get('name', 'None')}<br>"
            f"<b>Coords:</b> {shape_data.get('coords', 'N/A')}<br>"
            f"<b>Count:</b> {shape_data.get('count', 'N/A')}<br>"
            f"<b>Collection Area:</b> {shape_data.get('collectarea', 'N/A')}<br>"
            f"<b>Z-max Info:</b> {shape_data.get('zmax_info', 'N/A')}<br>"
        )
        info_label = QLabel(info)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Bin input
        bin_layout = QHBoxLayout()
        self.bins_input = QLineEdit("10")
        bin_layout.addWidget(QLabel("Histogram Bins:"))
        bin_layout.addWidget(self.bins_input)
        layout.addLayout(bin_layout)

        # Matplotlib Figure
        self.fig = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        # Toggle Buttons
        button_layout = QHBoxLayout()
        self.positive_btn = QPushButton("Show Positive")
        self.negative_btn = QPushButton("Show Negative")
        self.both_btn = QPushButton("Show Both")

        for btn in [self.positive_btn, self.negative_btn, self.both_btn]:
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: none;
                    border: 1px solid #ccc;
                    padding: 5px 10px;
                }
                QPushButton:checked {
                    background-color: #d0d0d0;
                    color: black;
                }
                QPushButton:focus {
                    outline: none;
                }
            """)

        self.positive_btn.clicked.connect(self.plot_positive)
        self.negative_btn.clicked.connect(self.plot_negative)
        self.both_btn.clicked.connect(self.plot_combined)

        button_layout.addWidget(self.positive_btn)
        button_layout.addWidget(self.negative_btn)
        button_layout.addWidget(self.both_btn)
        layout.addLayout(button_layout)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)
        self.plot_combined()

    def get_bins(self):
        try:
            return max(1, int(self.bins_input.text()))
        except ValueError:
            return 10

    def fetch_peakcurrents(self, polarity=None):
        if self.sim_id is None:
            return []  # No simulation ID means no data to fetch

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if polarity in ("positive", "negative"):
            cursor.execute(
                "SELECT peakcurrent FROM collisions WHERE structurestruck = ? AND strike = ? AND simulation_id = ?",
                (self.shape_id, polarity, self.sim_id)
            )
        else:
            cursor.execute(
                "SELECT peakcurrent FROM collisions WHERE structurestruck = ? AND simulation_id = ?",
                (self.shape_id, self.sim_id)
            )

        result = [row[0] for row in cursor.fetchall()]
        conn.close()
        return result
    
    def plot_positive(self):
        self._set_btn_state(self.positive_btn)
        data = self.fetch_peakcurrents("positive")
        self._plot_histogram(data, title="Positive Peak Currents", color='red')

    def plot_negative(self):
        self._set_btn_state(self.negative_btn)
        data = self.fetch_peakcurrents("negative")
        self._plot_histogram(data, title="Negative Peak Currents", color='blue')

    def plot_combined(self):
        self._set_btn_state(self.both_btn)
        data = self.fetch_peakcurrents()
        self._plot_histogram(data, title="All Peak Currents", color='gray')

    def _plot_histogram(self, data, title, color):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        bins = self.get_bins()
        ax.hist(data, bins=bins, color=color, edgecolor='black')
        ax.set_title(title)
        ax.set_xlabel("Peak Current (kA)")
        ax.set_ylabel("Count")
        self.canvas.draw()

    def _set_btn_state(self, active_btn):
        self.positive_btn.setChecked(active_btn == self.positive_btn)
        self.negative_btn.setChecked(active_btn == self.negative_btn)
        self.both_btn.setChecked(active_btn == self.both_btn)

class SimulationParametersDialog(QDialog):
    def __init__(self, XBOUNDS, YBOUNDS, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Simulation Parameters")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Samples
        self.samples_input = QLineEdit("10000")
        form_layout.addRow("Samples:", self.samples_input)

        # Peak Currents
        self.pos_min = QLineEdit("4")
        self.pos_max = QLineEdit("200")
        self.neg_min = QLineEdit("4")
        self.neg_max = QLineEdit("400")
        form_layout.addRow("Positive Min (kA):", self.pos_min)
        form_layout.addRow("Positive Max (kA):", self.pos_max)
        form_layout.addRow("Negative Min (kA):", self.neg_min)
        form_layout.addRow("Negative Max (kA):", self.neg_max)

        # Meters or Feet
        self.unit_input = QLineEdit("meters")
        form_layout.addRow("Units (meters/feet):", self.unit_input)

        # XBOUNDS and YBOUNDS (placeholder only)
        self.x_bounds_input = QLineEdit()
        self.x_bounds_input.setPlaceholderText(f"{XBOUNDS[0]},{XBOUNDS[1]}")
        form_layout.addRow("XBOUNDS (e.g. -50,50):", self.x_bounds_input)

        self.y_bounds_input = QLineEdit()
        self.y_bounds_input.setPlaceholderText(f"{YBOUNDS[0]},{YBOUNDS[1]}")
        form_layout.addRow("YBOUNDS (e.g. -50,50):", self.y_bounds_input)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def get_parameters(self):
        # Use placeholder values if user left bounds fields empty
        x_bounds_text = self.x_bounds_input.text().strip()
        y_bounds_text = self.y_bounds_input.text().strip()

        if x_bounds_text:
            x_bounds = [float(x.strip()) for x in x_bounds_text.split(",")]
        else:
            x_bounds = [float(v) for v in self.x_bounds_input.placeholderText().split(",")]

        if y_bounds_text:
            y_bounds = [float(y.strip()) for y in y_bounds_text.split(",")]
        else:
            y_bounds = [float(v) for v in self.y_bounds_input.placeholderText().split(",")]

        return {
            "samples": int(self.samples_input.text()),
            "positive_min": float(self.pos_min.text()),
            "positive_max": float(self.pos_max.text()),
            "negative_min": float(self.neg_min.text()),
            "negative_max": float(self.neg_max.text()),
            "units": self.unit_input.text().strip().lower(),
            "XBOUNDS": tuple(x_bounds),
            "YBOUNDS": tuple(y_bounds),
        }
    

class StepFileSelector(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Monte Carlo Lightning Simulation")
        self.setMinimumSize(700, 400)
        self.selected_file_path = None

        # Layout
        layout = QVBoxLayout()
        layout.setSpacing(25)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignCenter)

        # Title label
        title = QLabel("Monte Carlo Lightning Simulation")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Select a STEP file to begin your simulation setup.")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # File selection button
        self.select_button = QPushButton("Browse STEP File")
        self.select_button.setFont(QFont("Segoe UI", 10))
        self.select_button.setMinimumHeight(36)
        self.select_button.setStyleSheet("""
            QPushButton {
                background-color: #2b6cb0;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2c5282;
            }
        """)
        self.select_button.clicked.connect(self.select_file)
        layout.addWidget(self.select_button)

        self.setLayout(layout)
        self.set_dark_theme()

    def set_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(28, 28, 30))
        palette.setColor(QPalette.WindowText, Qt.white)
        self.setPalette(palette)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open STEP File",
            "",
            "STEP Files (*.step *.stp)"
        )
        if file_path:
            self.selected_file_path = file_path
            self.accept()

class SimulationSelectionDialog(QDialog):
    def __init__(self, SIM_ID, db_path="collisions.db", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Previous Simulation")
        self.setMinimumWidth(400)

        self.db_path = db_path
        self.selected_sim_id = None

        layout = QVBoxLayout()
        self.label = QLabel("Select a saved simulation project:")
        layout.addWidget(self.label)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        button_layout = QHBoxLayout()

        self.load_button = QPushButton("Load Selected Simulation")
        self.load_button.clicked.connect(self.load_selection)
        button_layout.addWidget(self.load_button)

        self.delete_button = QPushButton("Delete Selected Simulation")
        self.delete_button.clicked.connect(self.delete_selection)
        button_layout.addWidget(self.delete_button)

        self.export_button = QPushButton("Export Selected to CSV")
        self.export_button.clicked.connect(self.export_simulation)
        button_layout.addWidget(self.export_button)

        self.import_button = QPushButton("Import Simulation from CSV")
        self.import_button.clicked.connect(self.import_simulation)
        button_layout.addWidget(self.import_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.populate_projects()

    def populate_projects(self):
        self.list_widget.clear()
        projects = self.get_all_projects()
        for sim_id, name, timestamp in projects:
            item_text = f"{sim_id} — {name} ({timestamp})"
            self.list_widget.addItem(item_text)

    def get_all_projects(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT simulation_id, name, timestamp FROM projects ORDER BY simulation_id DESC")
        results = cursor.fetchall()
        conn.close()
        return results

    def load_selection(self):
        selected = self.list_widget.currentItem()
        if selected is None:
            QMessageBox.warning(self, "No Selection", "Please select a simulation to load.")
            return

        sim_id_str = selected.text().split("—")[0].strip()
        try:
            self.selected_sim_id = int(sim_id_str)
            QMessageBox.information(self, "Simulation Loaded", f"Simulation ID {self.selected_sim_id} is now active.")
            self.accept()
        except ValueError:
            QMessageBox.critical(self, "Error", "Could not parse the selected simulation ID.")

    def delete_selection(self):
        selected = self.list_widget.currentItem()
        if selected is None:
            QMessageBox.warning(self, "No Selection", "Please select a simulation to delete.")
            return

        sim_id_str = selected.text().split("—")[0].strip()
        try:
            sim_id = int(sim_id_str)
        except ValueError:
            QMessageBox.critical(self, "Error", "Could not parse the selected simulation ID.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete simulation ID {sim_id}?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE simulation_id = ?", (sim_id,))
            conn.commit()
            conn.close()

            QMessageBox.information(self, "Deleted", f"Simulation ID {sim_id} has been deleted.")
            self.populate_projects()

    def export_simulation(self):
        selected = self.list_widget.currentItem()
        if selected is None:
            QMessageBox.warning(self, "No Selection", "Please select a simulation to export.")
            return

        sim_id_str = selected.text().split("—")[0].strip()
        try:
            sim_id = int(sim_id_str)
        except ValueError:
            QMessageBox.critical(self, "Error", "Could not parse the selected simulation ID.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Export to CSV", "simulation_export.csv", "CSV Files (*.csv)")
        if file_path:
            export_simulation_to_csv(sim_id, output_path=file_path, db_path=self.db_path)
            QMessageBox.information(self, "Export Successful", f"Simulation ID {sim_id} exported to '{file_path}'")

    def import_simulation(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV Files (*.csv)")
        if file_path:
            import_simulation_from_csv(file_path, db_path=self.db_path)
            QMessageBox.information(self, "Import Successful", f"Imported simulation from '{file_path}'")
            self.populate_projects()


def export_simulation_to_csv(sim_id, output_path="simulation_export.csv", db_path="collisions.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open(output_path, mode='w', newline='') as file:
        writer = csv.writer(file)

        writer.writerow(["=== Project Metadata ==="])
        cursor.execute("SELECT simulation_id, name, timestamp FROM projects WHERE simulation_id = ?", (sim_id,))
        project_row = cursor.fetchone()
        if project_row:
            writer.writerow(["simulation_id", "name", "timestamp"])
            writer.writerow(project_row)
        else:
            writer.writerow(["No project found for simulation_id =", sim_id])

        writer.writerow([])
        writer.writerow(["=== Shape Metadata ==="])
        cursor.execute("""
            SELECT shape_id, name, coords, count, collectarea, percentofstrikes, kdtreepath 
            FROM shape_metadata 
            WHERE simulation_id = ?
        """, (sim_id,))
        shape_rows = cursor.fetchall()
        if shape_rows:
            writer.writerow(["shape_id", "name", "coords", "count", "collectarea", "percentofstrikes", "kdtreepath"])
            for row in shape_rows:
                writer.writerow(row)
        else:
            writer.writerow(["No shape metadata found for simulation_id =", sim_id])

        writer.writerow([])
        writer.writerow(["=== Collision Records ==="])
        cursor.execute("""
            SELECT center_on_contact, surface_on_contact, peakcurrent, strike, structurestruck, count 
            FROM collisions 
            WHERE simulation_id = ?
        """, (sim_id,))
        collision_rows = cursor.fetchall()
        if collision_rows:
            writer.writerow(["center_on_contact", "surface_on_contact", "peakcurrent", "strike", "structurestruck", "count"])
            for row in collision_rows:
                writer.writerow(row)
        else:
            writer.writerow(["No collisions found for simulation_id =", sim_id])

    conn.close()


def import_simulation_from_csv(csv_path, db_path="collisions.db"):
    with open(csv_path, newline='') as file:
        reader = csv.reader(file)
        rows = list(reader)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        project_start = rows.index(["=== Project Metadata ==="])
        shape_start = rows.index(["=== Shape Metadata ==="])
        collision_start = rows.index(["=== Collision Records ==="])
    except ValueError as e:
        print("Invalid CSV format:", e)
        return

    project_data = rows[project_start + 2]
    project_name = project_data[1] + " (imported)"

    cursor.execute("INSERT INTO projects (name) VALUES (?)", (project_name,))
    new_sim_id = cursor.lastrowid

    shape_header_row = shape_start + 1
    for row in rows[shape_header_row + 1:collision_start - 1]:
        if not row or row[0].startswith("==="): break
        cursor.execute("""
            INSERT INTO shape_metadata (
                simulation_id, shape_id, name, coords, count, collectarea, percentofstrikes, kdtreepath
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_sim_id, *row))

    collision_header_row = collision_start + 1
    for row in rows[collision_header_row + 1:]:
        if not row or row[0].startswith("==="): break
        cursor.execute("""
            INSERT INTO collisions (
                center_on_contact, surface_on_contact, peakcurrent, strike, structurestruck, count, simulation_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (*row, new_sim_id))

    conn.commit()
    conn.close()
