# This Python file uses the following encoding: utf-8
# Uses a subclassed UiLoader from https://gist.github.com/cpbotha/1b42a20c8f3eb9bb7cb8
# pip install PySide2 pandas PySerial

import os
from pathlib import Path
import sys

from PySide2.QtWidgets import QApplication, QWidget, QFileDialog, QMainWindow, QVBoxLayout
from PySide2.QtCore import QFile, QRegularExpression, QAbstractTableModel, QAbstractListModel, Qt
from PySide2.QtCore import Slot, QMetaObject, QModelIndex, QSettings, QTimer, QDateTime, QTime, QEvent
from PySide2.QtUiTools import QUiLoader
from PySide2.QtGui import QRegularExpressionValidator as QRegExpValidator
from PySide2.QtGui import QIcon
from PySide2 import QtGui
import pandas as pd
import serial.tools.list_ports
import serial
import re


# Main widget that is shown
class Widget(QWidget):
    def __init__(self, parent=None):
        super(Widget, self).__init__(parent)
        self.load_ui()
        self.id_reader_clock = QTimer(self)
        self.id_reader_clock.timeout.connect(self.read_id)
        self.load_timers()
        self.load_settings()
        self.load_data_frames()
        self.load_id_input()
        self.load_btns()
        self.icon_path = resource_path('4418.png')
        self.setWindowIcon(QIcon(self.icon_path))

    def load_ui(self):
        # Load in the ui file created in Qt Designer
        self.ui_path = resource_path('form.ui')
        self.ui = loadUi(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      self.ui_path), self)
        self.setWindowTitle('Time Tracker')
        self.ui.tableView.setSortingEnabled(True)

    # Methods for repeating actions, like updating the clock and polling the id reader
    def load_timers(self):
        self.current_date_time = QDateTime.currentDateTime()

        # start_date should be the day that the meeting started, if the program
        # is started after midnight the start date should be the previous day,
        # we see if the program is started after the cutoff time to determine which day to use
        self.current_time = QTime.currentTime()
        self.start_date = self.current_date_time
        if self.current_time.secsTo(self.ui.timeEdit.time()) > 0 and self.current_time.secsTo(QTime(0,0,0)) < 0:
            # Use previous day if after midnight and before cutoff
            self.start_date = self.start_date.addDays(-1)

        timer_clock = QTimer(self)
        timer_clock.timeout.connect(self.update_clock)
        timer_clock.start(1000)     # 1Hz

        if self.ui.checkBox_enable_reader.checkState():
            self.enable_id_reader_timer(1)
        else:
            self.enable_id_reader_timer(0)
        self.update_clock()

    def update_clock(self):
        self.current_date_time = QDateTime.currentDateTime()
        self.ui.lineEdit_clock.setText(self.current_date_time.toString('M/d/yyyy hh:mm:ss'))

    def read_id(self):
        try:
            self.badge_id = self.arduino.readline()
            if self.badge_id:
                # Convert to a string, pull the number out and convert to an int
                self.badge_id = str(self.badge_id)
                self.badge_id = self.badge_id.split("'")[1]
                self.ui.textEdit_com.append("Badge ID Scanned: " + self.badge_id)
                self.ui.textEdit_com.moveCursor(QtGui.QTextCursor.End)
                try:
                    self.sign_inout(False, self.badge_id)
                except:
                    self.ui.textEdit_com.append("Error: Associated ID not found")
                    self.ui.textEdit_com.moveCursor(QtGui.QTextCursor.End)
                    pass
        except:
            pass

    # Method for retreiving and initializing saved settings
    def load_settings(self):
        self.settings = QSettings('Team Impulse', 'Sign In App')
        try:
            self.select_file(True)
        except:
            pass
        if self.settings.contains("suffix"):
            self.ui.lineEdit_export_suffix.setText(str(self.settings.value("suffix")))
        else:
            self.ui.lineEdit_export_suffix.setText("_attendance")

        if self.settings.contains("prefix_format"):
            self.ui.lineEdit_export_prefix_format.setText(str(self.settings.value("prefix_format")))
        else:
            self.ui.lineEdit_export_prefix_format.setText("yyyyMMdd")

        if self.settings.contains("export_location"):
            self.savepath = self.settings.value("export_location")
            try:
                self.export_file_path_update()
            except:
                pass
        else:
            self.savepath = Path.cwd()
            self.export_file_path_update()
        self.ui.lineEdit_signed_in.setText("0")

        self.update_com()
        if self.settings.contains("com_index"):
            try:
                self.ui.com_selector.setCurrentIndex(self.settings.value("com_index"))
                self.id_reader_com_port = self.ui.com_selector.currentText()
                self.open_com()
            except:
                pass
        else:
            self.id_reader_com_port = "Select Port"


    def clear_settings(self):
        self.settings.clear()

    # Method for initializing the pandas dataframes used to keep track of people
    def load_data_frames(self):
        self.data_records_columns = ["ID", "First_Name", "Last_Name", "Time_In",
                                    "Time_Out", "Destination", "Hours"]
        self.data_records = pd.DataFrame(columns=self.data_records_columns)
        self.active_users = pd.DataFrame(columns=["ID", "First_Name", "Last_Name"])

        self.model_active = ActiveModel(todos=self.active_users)
        self.ui.listView.setModel(self.model_active)
        self.active_users_savepath = str(Path.cwd() / "active_users.csv")
        try:
            self.active_users = pd.read_csv(self.active_users_savepath, dtype=str)
            self.model_active = ActiveModel(todos=self.active_users)
            self.ui.listView.setModel(self.model_active)
            self.ui.lineEdit_signed_in.setText(str(self.active_users.shape[0]))
        except:
            #print("no active user file")
            pass
        try:
            self.data_records = pd.read_csv(self.savepath / self.export_file_name, keep_default_na=False, dtype=str)
            #print("data records file:")
            #with pd.option_context('display.max_rows', None, 'display.max_columns', None):
            #    print(self.data_records)
            #print("data records file end")
        except:
            #print("no data records file")
            pass

    # Setup the validator to only allow numbers in the id field
    def load_id_input(self):
        id_validator = QRegExpValidator(QRegularExpression(r'[0-9]+'))
        self.ui.lineEdit_id_enter.setValidator(id_validator)
        self.ui.lineEdit_id_enter.returnPressed.connect(self.sign_inout)

    # Connect various buttons and actions to their methods
    def load_btns(self):
        self.ui.btn_signin.pressed.connect(self.sign_inout)
        self.ui.btn_people_file_load.pressed.connect(self.select_file)
        self.ui.btn_people_file_save.pressed.connect(self.save_file)
        self.ui.btn_people_file_add_row.pressed.connect(self.insert_above)
        self.ui.btn_people_file_remove_row.pressed.connect(self.remove_rows)
        self.ui.btn_clear_settings.pressed.connect(self.clear_settings)
        self.ui.btn_export_location.pressed.connect(self.set_export_location)
        self.ui.btn_export_manual.pressed.connect(self.manual_export)
        self.ui.rbtn_other.clicked.connect(self.focus_other_text_field)
        self.ui.btn_force_signout.pressed.connect(self.force_signout)
        self.ui.btn_clear_temp_files.pressed.connect(self.clear_temp_files)
        self.ui.checkBox_enable_reader.stateChanged.connect(self.enable_id_reader)
        self.ui.btn_update_com.pressed.connect(self.update_com)
        self.ui.com_selector.currentIndexChanged.connect(self.select_com)
        self.ui.lineEdit_export_prefix_format.returnPressed.connect(self.export_file_path_update)
        self.ui.lineEdit_export_suffix.returnPressed.connect(self.export_file_path_update)
        self.ui.lineEdit_destination_other.returnPressed.connect(self.sign_inout)
        self.ui.lineEdit_destination_other.installEventFilter(self)
        self.ui.btn_open_com.pressed.connect(self.open_com)
        self.ui.btn_close_com.pressed.connect(self.close_com)

    # Methods for the ID reader
    def enable_id_reader(self):
        if self.ui.checkBox_enable_reader.checkState():
            self.enable_id_reader_timer(1)

            self.ui.btn_update_com.setEnabled(1)
            self.ui.com_selector.setEnabled(1)
            self.ui.textEdit_com.setEnabled(1)
            self.ui.btn_open_com.setEnabled(1)
            self.ui.btn_close_com.setEnabled(1)
            self.ui.label_8.setEnabled(1)
            self.ui.textEdit_com.append("ID Reader Enabled")
            self.ui.textEdit_com.moveCursor(QtGui.QTextCursor.End)

        else:
            self.enable_id_reader_timer(0)

            self.ui.btn_update_com.setEnabled(0)
            self.ui.com_selector.setEnabled(0)
            self.ui.textEdit_com.setEnabled(0)
            self.ui.btn_open_com.setEnabled(0)
            self.ui.btn_close_com.setEnabled(0)
            self.ui.label_8.setEnabled(0)
            self.ui.textEdit_com.append("ID Reader Disabled")
            self.ui.textEdit_com.moveCursor(QtGui.QTextCursor.End)

            try:
                self.arduino.close()
                self.ui.textEdit_com.append("Closed Port: " + self.id_reader_com_port)
                self.ui.textEdit_com.moveCursor(QtGui.QTextCursor.End)
            except:
                pass

    def enable_id_reader_timer(self, enable):
        if enable:
            self.id_reader_clock.start(500)     # 2Hz scan rate
        else:
            self.id_reader_clock.stop()

    def select_com(self):
        self.close_com()
        self.settings.setValue("com_index", self.ui.com_selector.currentIndex())
        self.id_reader_com_port = self.ui.com_selector.currentText()
        #self.open_com()

    def update_com(self):
        self.ui.com_selector.clear()
        self.ui.com_selector.addItem("Select Port")
        self.ports = serial.tools.list_ports.comports()
        for p in self.ports:
            self.ui.com_selector.addItem(p.device)


    def open_com(self):
        if self.id_reader_com_port == "Select Port":
            self.ui.textEdit_com.append("Please select a port to open")
            self.ui.textEdit_com.moveCursor(QtGui.QTextCursor.End)
            return
        try:
            if self.arduino.is_open():
                self.arduino.close()
                self.ui.textEdit_com.append("Port already open, closing and reopening")
                self.ui.textEdit_com.moveCursor(QtGui.QTextCursor.End)
        except:
            pass

        try:
            self.arduino = serial.Serial(port=self.id_reader_com_port, baudrate=115200, timeout=.1)
            self.ui.textEdit_com.append("Port connected: " + self.id_reader_com_port)
            self.ui.textEdit_com.moveCursor(QtGui.QTextCursor.End)
        except:
            self.ui.textEdit_com.append("Error: Can't open Serial Port: " + self.id_reader_com_port)
            self.ui.textEdit_com.moveCursor(QtGui.QTextCursor.End)
            return

    def close_com(self):
#        try:
#            self.id_reader_com_port
#        except:
#            self.id_reader_com_port = "Select Port"
#            print("There was an issue with the id_reader_com_port var")
            
        if self.id_reader_com_port == "Select Port" or self.id_reader_com_port == "":
            #self.ui.textEdit_com.append("No Port Selected")
            return
        try:
            self.arduino.close()
            self.ui.textEdit_com.append("Closed Port: " + self.id_reader_com_port)
            self.ui.textEdit_com.moveCursor(QtGui.QTextCursor.End)
        except:
            self.ui.textEdit_com.append("Error: Unable to close Port: " + self.id_reader_com_port)
            self.ui.textEdit_com.moveCursor(QtGui.QTextCursor.End)
            pass

    # Main logic and dateframe minipulation for time tracking
    def sign_inout(self, forced=False, badge_id=None):
        try:
            self.people_csv_data = self.people_csv_data
        except:
            self.ui.textEdit.append("Error: No People File selected, please load a file")
            self.ui.textEdit.moveCursor(QtGui.QTextCursor.End)
            return
        if self.ui.lineEdit_id_enter.text() == "" and badge_id == None:
            self.ui.lineEdit_id_enter.setFocus()
            return

        if not badge_id == None:
            self.badge_id = str(badge_id)
            self.temp_data = self.people_csv_data.query('Badge == @self.badge_id')[['ID', 'First_Name', 'Last_Name']]
            self.temp_data.reset_index(drop=True, inplace=True)
            self.id = self.temp_data['ID'][0]
        else:
            self.id = self.ui.lineEdit_id_enter.text()
        self.temp_data = self.people_csv_data.query('ID == @self.id')[['ID', 'First_Name', 'Last_Name']]
        self.temp_data.reset_index(drop=True, inplace=True)

        if not self.temp_data.empty:
            if self.active_users.query('ID == @self.id').empty:  # Sign in the person and add to active users list
                self.ui.textEdit.append(str(self.temp_data['First_Name'][0]) + " " + str(self.temp_data['Last_Name'][0]) + 
                                                           " signed in at: " + self.current_date_time.toString('hh:mm:ss'))
                self.ui.textEdit.moveCursor(QtGui.QTextCursor.End)
                self.active_users = self.active_users.append(self.temp_data)
                self.active_users.reset_index(drop=True, inplace=True)

                # Create entry in data_records for the login
                self.temp_append_data = [(self.id, self.temp_data['First_Name'][0],
                                          self.temp_data['Last_Name'][0],
                                          self.current_date_time.toString('yyyy-MM-dd_hh:mm:ss'), "", "", "")]
                self.temp_append = pd.DataFrame(self.temp_append_data, columns=self.data_records_columns)
                self.data_records = self.data_records.append(self.temp_append)
                self.data_records.reset_index(drop=True, inplace=True)

                # Save the active users data so that the program can be closed and opened whenever
                self.active_users.to_csv(self.active_users_savepath, index=False)

                # Save data_records data so that the program can be closed and opened whenever
                self.data_records.to_csv(self.savepath / self.export_file_name, index=False)

            else:  # Signout the person and remove from active users list
                self.active_users = self.active_users[self.active_users.ID != self.id]
                self.active_users.reset_index(drop=True, inplace=True)

                # Calculate the hours signed in
                self.data_records.reset_index(drop=True, inplace=True)
                self.initial_time = self.data_records.loc[(self.data_records['ID'] == self.id) & 
                                                          (self.data_records['Time_Out'] == ""), 'Time_In']
                self.initial_time.reset_index(drop=True, inplace=True)
                self.hours = round(QDateTime.fromString(self.initial_time[0], 'yyyy-MM-dd_hh:mm:ss').secsTo(self.current_date_time) / 3600, 2)

                # Get the destination from the buttons
                if self.ui.rbtn_home.isChecked():
                    self.destination = "Home"
                elif self.ui.rbtn_work.isChecked():
                    self.destination = "Work"
                elif self.ui.rbtn_other.isChecked():
                    self.destination = str(self.ui.lineEdit_destination_other.text())
                self.ui.rbtn_home.setChecked(1)

                if forced:
                    self.destination = "Forced Signout"

                # "Time_Out", "Destination", "Hours"
                self.data_records.loc[(self.data_records['ID'] == self.id) & 
                                      (self.data_records['Time_Out'] == ""), 'Destination'] = self.destination
                self.data_records.loc[(self.data_records['ID'] == self.id) & 
                                      (self.data_records['Time_Out'] == ""), 'Hours'] = self.hours
                self.data_records.loc[(self.data_records['ID'] == self.id) & 
                                      (self.data_records['Time_Out'] == ""), 'Time_Out'] = self.current_date_time.toString('yyyy-MM-dd_hh:mm:ss')

                self.ui.textEdit.append(str(self.temp_data['First_Name'][0]) + " " + str(self.temp_data['Last_Name'][0])
                                        + " signed out at: " + self.current_date_time.toString('hh:mm:ss') +
                                        ", worked: " + str(self.hours) + "hours, Destination: "
                                        + str(self.destination))
                self.ui.textEdit.moveCursor(QtGui.QTextCursor.End)

                # Save the active users data so that the program can be closed and opened whenever
                self.active_users.to_csv(self.active_users_savepath, index=False)

                # Save data_records data so that the program can be closed and opened whenever
                self.data_records.to_csv(self.savepath / self.export_file_name, index=False)
        else:
            self.ui.textEdit.append("Error: User Not Found")
            self.ui.textEdit.moveCursor(QtGui.QTextCursor.End)
        self.ui.lineEdit_destination_other.clear()
        self.ui.lineEdit_id_enter.clear()
        self.ui.lineEdit_signed_in.setText(str(self.active_users.shape[0]))
        self.model_active = ActiveModel(todos=self.active_users)
        self.ui.listView.setModel(self.model_active)

    def force_signout(self):
        #need to loop through all of the active users, set the ID field and run signinout with a forced signout flag
        for index, row in self.active_users.iterrows():
            self.forced_id = str(row["ID"])
            self.ui.lineEdit_id_enter.setText(str(self.forced_id))
            self.sign_inout(True)

    # Methods for file handling
    def select_other_dest(self):
        self.ui.rbtn_other.setDown(1)

    def focus_other_text_field(self):
        self.ui.lineEdit_destination_other.selectAll()
        self.ui.lineEdit_destination_other.setFocus()

    def manual_export(self):
        if self.settings.contains("export_location"):
            self.open_location = self.settings.value("export_location")
        else:
            self.open_location = Path.cwd()
        app.setQuitOnLastWindowClosed(False)
        self.manual_savepath,_ = QFileDialog.getSaveFileName(self, 'Open file', str(self.open_location), ("CSV (*.csv)"))
        app.setQuitOnLastWindowClosed(True)
        if self.manual_savepath:
            self.data_records.to_csv(self.manual_savepath, index=False)

    def export_file_path_update(self):
#need to add a check to see if there are any logged in people be for changing files or they wont be able to log out nicely
        self.settings.setValue("suffix", str(self.ui.lineEdit_export_suffix.text()))
        self.export_file_name = self.start_date.toString(self.ui.lineEdit_export_prefix_format.text()) + self.ui.lineEdit_export_suffix.text() + ".csv"
        self.ui.lineEdit_export_location.setText(str(self.savepath / self.export_file_name))
        self.ui.textEdit.append("Export file will be saved to: " + str(self.savepath / self.export_file_name))
        self.ui.textEdit.moveCursor(QtGui.QTextCursor.End)
        self.settings.setValue("export_location", self.savepath)
        self.settings.setValue("prefix_format", self.ui.lineEdit_export_prefix_format.text())
        try:
            self.export_file_name = self.start_date.toString(self.ui.lineEdit_export_prefix_format.text()) + self.ui.lineEdit_export_suffix.text() + ".csv"
            self.ui.lineEdit_export_location.setText(str(self.savepath / self.export_file_name))
        except:
            pass
        self.setFocus()

    def set_export_location(self):
        if self.settings.contains("export_location"):
            self.open_location = self.settings.value("export_location")
        else:
            self.open_location = Path.cwd()

        app.setQuitOnLastWindowClosed(False)
        self.savepath = Path(QFileDialog.getExistingDirectory(self, 'Open file', str(self.open_location)))
        app.setQuitOnLastWindowClosed(True)

        if not str(self.savepath) == ".":
            self.export_file_path_update()
        else:
            self.ui.textEdit.append("Warning: No folder selected")
            self.ui.textEdit.moveCursor(QtGui.QTextCursor.End)

    def clear_temp_files(self):
        # Should delete the active users file and clear the active users dataframe
        try:
            os.remove(self.active_users_savepath)
            self.ui.textEdit.append("Temp Files deleted, please check attendance file for errors and restart the program")
            self.ui.textEdit.moveCursor(QtGui.QTextCursor.End)
        except:
            self.ui.textEdit.append("No Temp Files found")
            self.ui.textEdit.moveCursor(QtGui.QTextCursor.End)

    #Methods for handling the people csv table
    def select_file(self, initial=False):
        if initial:
            self.people_csv_filename = self.settings.value("people_csv_filename")
        else:
            app.setQuitOnLastWindowClosed(False)
            self.people_csv_filename, _ = QFileDialog.getOpenFileName(
                self,
                'Select a CSV file to open…',
                str(Path.cwd()),
                'CSV Files (*.csv) ;; All Files (*)')
            app.setQuitOnLastWindowClosed(True)
        if self.people_csv_filename:
            self.people_csv_data = pd.read_csv(self.people_csv_filename, dtype=str)
            self.model_csv = CsvTableModel(self.people_csv_data, self.people_csv_filename)
            self.ui.tableView.setModel(self.model_csv)
            self.ui.lineEdit_people_file.setText(str(self.people_csv_filename))
            self.settings.setValue("people_csv_filename", self.people_csv_filename)

    def save_file(self):
        if self.model_csv:
            self.model_csv.save_data()
            self.select_file(1)

    def insert_above(self):
        selected = self.ui.tableView.selectedIndexes()
        row = selected[0].row() if selected else 0
        self.model_csv.insertRows(row, 1, None)

    def remove_rows(self):
        selected = self.ui.tableView.selectedIndexes()
        num_rows = len(set(index.row() for index in selected))
        if selected:
            self.model_csv.removeRows(selected[0].row(), num_rows, None)

    def eventFilter(self, object, event):
        if object == self.ui.lineEdit_destination_other and event.type() == QEvent.FocusIn:
            self.ui.rbtn_other.setChecked(1)
            return False
        return False


class ActiveModel(QAbstractListModel):
    def __init__(self, *args, todos=None, **kwargs):
        super(ActiveModel, self).__init__(*args, **kwargs)
        self.todos = todos

    def data(self, index, role):
        if role == Qt.DisplayRole:
            # See below for the data structure.
            text = str(self.todos['First_Name'][index.row()]) + " " + str(self.todos['Last_Name'][index.row()])
            # Return the todo text only.
            return text

    def rowCount(self, index):
        return len(self.todos)


class CsvTableModel(QAbstractTableModel):
    def __init__(self, data, csv_file):
        super().__init__()
        self.filename = csv_file
        self._data = data

    # Minimum necessary methods:
    def rowCount(self, parent):
        return self._data.shape[0]

    def columnCount(self, parent):
        return self._data.shape[1]

    def data(self, index, role):
        if role in (Qt.DisplayRole, Qt.EditRole):
            return str(self._data.iloc[index.row(), index.column()])

    # Additional features methods:
    def headerData(self, section, orientation, role):

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(self._data.columns[section])
        else:
            return super().headerData(section, orientation, role)

    def sort(self, column, order):
        self.layoutAboutToBeChanged.emit()  # needs to be emitted before a sort
        self._data.sort_values(self._data.columns[column], ascending=True, inplace=True)
        if order == Qt.DescendingOrder:
            self._data.sort_values(self._data.columns[column], ascending=False, inplace=True)
        self.layoutChanged.emit()  # needs to be emitted after a sort

    # Methods for Read/Write
    def flags(self, index):
        return super().flags(index) | Qt.ItemIsEditable

    def setData(self, index, value, role):
        if index.isValid() and role == Qt.EditRole:
            self._data.iloc[index.row(), index.column()] = value
            self.dataChanged.emit(index, index, [role])
            return True
        else:
            return False

    # Methods for inserting or deleting
    def insertRows(self, position, rows, parent):
        self.beginInsertRows(
            parent or QModelIndex(),
            position,
            position + rows - 1)

        for i in range(rows):
            self._data = pd.concat([self._data, pd.DataFrame([[''] * self._data.shape[1]],
                                    columns=self._data.columns)], ignore_index=True)
        self.endInsertRows()

    def removeRows(self, position, rows, parent):
        self.beginRemoveRows(
            parent or QModelIndex(),
            position,
            position + rows - 1)

        for i in range(rows):
            self._data = self._data.drop(labels=position, axis=0)

    def save_data(self):
        self._data.to_csv(self.filename, index=False)

# Loader for loading in the UI file
class UiLoader(QUiLoader):
    """
    Subclass :class:`~PySide.QtUiTools.QUiLoader` to create the user interface
    in a base instance.
    Unlike :class:`~PySide.QtUiTools.QUiLoader` itself this class does not
    create a new instance of the top-level widget, but creates the user
    interface in an existing instance of the top-level class.
    This mimics the behaviour of :func:`PyQt4.uic.loadUi`.
    """

    def __init__(self, baseinstance, customWidgets=None):
        QUiLoader.__init__(self, baseinstance)
        self.baseinstance = baseinstance
        self.customWidgets = customWidgets

    def createWidget(self, class_name, parent=None, name=''):
        """
        Function that is called for each widget defined in ui file,
        overridden here to populate baseinstance instead.
        """
        if parent is None and self.baseinstance:
            # supposed to create the top-level widget, return the base instance
            # instead
            return self.baseinstance

        else:
            if class_name in self.availableWidgets():
                # create a new widget for child widgets
                widget = QUiLoader.createWidget(self, class_name, parent, name)

            else:
                # if not in the list of availableWidgets, must be a custom widget
                # this will raise KeyError if the user has not supplied the
                # relevant class_name in the dictionary, or TypeError, if
                # customWidgets is None
                try:
                    widget = self.customWidgets[class_name](parent)

                except (TypeError, KeyError) as e:
                    raise Exception('No custom widget ' + class_name + ' found in customWidgets param of UiLoader __init__.')

            if self.baseinstance:
                # set an attribute for the new child widget on the base
                # instance, just like PyQt4.uic.loadUi does.
                setattr(self.baseinstance, name, widget)

                # this outputs the various widget names, e.g.
                # sampleGraphicsView, dockWidget, samplesTableView etc.
                #print(name)

            return widget


def loadUi(uifile, baseinstance=None, customWidgets=None, workingDirectory=None):
    loader = UiLoader(baseinstance, customWidgets)

    if workingDirectory is not None:
        loader.setWorkingDirectory(workingDirectory)

    widget = loader.load(uifile)
    QMetaObject.connectSlotsByName(widget)
    return widget

# A simple method allowing the program to find the bundled UI file when packaged as an exe
def resource_path(relative_path):
    # Get absolute path to resource, works for dev and for PyInstaller
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)



if __name__ == "__main__":
    app = QApplication([])
    app.setStyle("fusion")
    main_window = Widget()
    main_window.installEventFilter(main_window)
    main_window.showMaximized()
    sys.exit(app.exec_())
