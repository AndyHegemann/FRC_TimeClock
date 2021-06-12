Time Tracking app developed by 4418 that interfaces to CSV files

# Using the application
To get up and running load your Poeple File CSV (file requirements) in the settings page and then everyone can enter their ID on the main page to sign in and out.

Everytime someone signs in or out the attendance file will be updated

## Main Page
The Main page handles signing in and out, displaying who is currently active and echoing the sign in/out activity

[insert main page picture here]

## Settings Page
The Settings page handles all of the behind the scenes functions. 

[insert settings page picture here]

In order, left to right, top to bottom:
* Automatic Attendance File: Location, Name and Time Cutoff 
  * The time cutoff value is used to keep students who signout after midnight on the previous days attendance file 
* RFID ID card reader settings 
  * The application was designied to poll a serial port for the UID of common Mifare classic cards being read by a PN532 hooked to an arduino
  * A message below the port selector will show when a valid serial port is selected, when an ID card is selected the UID will be shown there instead
  * The ID card reader can also disabled
* Manually Generate Attendance CSV
  * Allows the manual generation of the current days attendance file wherever selected
* Signout Everyone
  * Signs out everyone currently active and sets their destination to "Forced Signout" 
* Clear Temp Files
  * To allow the program to be closed and retain the currently signed in people, a temp file called "active_users" is created in the applicaiton directory that contains the ID and names of everyone that is signed in. While helpful most of the time, on some occasions it is nescessary to clear this file and repair the attendance file manually
* Clear Settings
  * This clears all of the stored settings like: Attendance save location, people file selection, serial port, and the like
* People File Viewer
  * **Only make edits when no one is signed in**, the application currently does not retroactively change peoples ID in attendance files. Making changes while people are signed in will make the applicaiton unsable and potentialy compromise attendance files
  * This shows the current people CSV file used to assign ID's and badge UID's to Names
  * While there is rudimentary editing support it is highly reccomended to only edit values within the application. Adding additional people is best handled with external programs 
  * Unlike other areas of the settings page the People File Viewer does not automatically save so please remember to save the file when you are done editing
    
## People File CSV Specifications
The column names must match the example file exactly or the applicaiton will not work properly or at all

Required Columns (extras may be include but will not be used and could cause instability):
* ID: The person's unique identification number
* First_Name: The person's first name
* Last_Name: The person's last name
* Student?: An optional identifier of if the person is a student 
* Badge: The UID of the badge assigned to that person

## Attendance File Specifications
The attendance file will have the folowing columns:
* ID
* First_Name
* Last_Name
* Time_In
* Time_Out
* Destination: Is selected on the main page before signing out or "Forced Signout" if they were signed out with the Signout Everyone button 
* Hours: Number of hours they were signed in rounded to 2 decimal places 


# Building the application
OS compatability notice: This applicaiton was developed primarily for Windows 10 deployment and the instructions below are for Win10. The PySide2 framework that the application is built on supports iOS and Linux, although there may be issues with file paths and other various functions since there has been no testing for iOS and Linux.

Set up a python 3.6.x [virtual enviroment](https://realpython.com/intro-to-pyenv/) with the following modules: 
`pandas>=1.1.5 pyinstaller>=4.3 pyserial>=3.5 PySide2>=5.15.2`

Edit main_exe.spec (or main.spec for onefolder applications) such that the line: 

`pathex=['C:\\Users\\Andy\\Dropbox\\Projects\\2021_FRC\\py36venv\\Lib\\site-packages\\shiboken2', 'C:\\Users\\Andy\\Dropbox\\Projects\\2021_FRC\\py36venv\\TimeClock']` 
points to your virtual enviroment setup

## Building onefile application

Download and install the [Windows 10 SDK](https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk/) (https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk/)

Run: `pyinstaller main_exe.spec` from the directory containing all of the source files

## Building onefolder applicaiton

Run: `pyinstaller main.spec` from the directory containing all of the source files

## Errors when building
One common error I encountered when building the applicaiton was plugins not being found by PyInstaller, like shiboken2. In that case, just add them to the `pathex` variable. 

Another issue was the application failing to run because of an import that PyInstaller missed, PySide2.QtXml in my case. Just add any that it missed to the `hiddenimports` variable in the .spec file. 

Another common issue was data files not getting bundled, if you add files ensure that they are added to the `datas` variable in the .spec file you are using. 

# Building the ID Reader 
## Hardware
In an effort to reduce cost a cheap clone of an ElecHouse PN532 NFC RFID module V3 was wired via SPI to an Arduino Nano clone (most any arduino campatable MCU should work fine). The arduino then is connected to the computer via USB.

[Example Wiring](https://youtu.be/2qf6gIqhWNA?t=204)

## Software
To keep the application simple the ID Reader communicates through a simple serial port.

The software on the arduino is a stripped down version of the example code in the [Adafruit PN532 Library](https://github.com/adafruit/Adafruit-PN532) that waits for a card to be detected and prints the UID to the serial port. The application continously polls the serial port for any new UID's

Source code for the ID Reader is in the ID Reader folder
