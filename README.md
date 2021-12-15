Time Tracking app developed by 4418 that interfaces to CSV files, inspired by https://github.com/team294/signinapp and https://github.com/mstrperson/qt-timeclock

# Using the application
To get up and running, download the latest release from the [Releases](https://github.com/AndyHegemann/FRC_TimeClock/releases) page and then load your "People File CSV" ([file requirements](https://github.com/AndyHegemann/FRC_TimeClock#people-file-csv-specifications)) in the settings page. Everyone can then enter their ID on the main page to sign in and out.

Everytime someone signs in or out the attendance file will be updated

## Main Page
The Main page handles signing in and out, displaying who is currently active and echoing the sign in/out activity

![main_page](https://github.com/AndyHegemann/FRC_TimeClock/blob/ae71403bd39e6d9926815a07f3cbfc903987aea1/App_Images/main_page.PNG)


## Settings Page
The Settings page handles all of the behind the scenes functions. 

![settings_page](https://github.com/AndyHegemann/FRC_TimeClock/blob/fda066b15b8c19587ac382d68f5d1a2da37b9f77/App_Images/settings_page.PNG)


In order, left to right, top to bottom:
* Automatic Attendance File: Location, Name and Time Cutoff 
  * The time cutoff value is used to keep students who signout after midnight on the previous days attendance file 
* RFID ID card reader settings 
  * The application was designied to poll a serial connection with an arduino that reads the UID of RFID Cards
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
  * **Only make edits when no one is signed in**, the application does not retroactively change peoples ID in attendance files. Making changes while people are signed in will make the applicaiton unsable and potentialy compromise attendance files
  * This shows the current people CSV file used to assign ID's and badge UID's to Names
  * While there is rudimentary editing support it is highly reccomended to only edit values within the application. Adding additional people is best handled with external programs 
  * Unlike other areas of the settings page the People File Viewer does not automatically save so please remember to save the file when you are done editing
    
## People File CSV Specifications
The column names must match the [example file](https://github.com/AndyHegemann/FRC_TimeClock/blob/main/Sample_CSV_Files/test_people.csv) exactly or the applicaiton will not work properly or at all

Required Columns (extras may be included, but will not be used by the application and could cause instability):
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

See the sample attendance file: [20210611_attendance.csv](https://github.com/AndyHegemann/FRC_TimeClock/blob/main/Sample_CSV_Files/20210611_attendance.csv)


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
In an effort to reduce cost a cheap there are 2 options: 
1. **Mifare classic** cards with a clone of an ElecHouse PN532 NFC RFID module V3 was wired via SPI to an Arduino Nano clone (most any arduino campatable MCU should work fine). [Example Wiring](https://youtu.be/2qf6gIqhWNA?t=204)
2. **125kHz** cards with a RDM6300 module wired via serial to an Arduino Nano clone (most any arduino campatable MCU should work fine). [Example Wiring](https://circuitdigest.com/microcontroller-projects/interfacing-rdm6300-rfid-reader-module-interfacing-with-arduino-nano)

Both options have the arduino connected to the computer via USB.



## Software
To keep the application simple the ID Reader communicates through a simple serial port.

Option 1: The software on the arduino is a stripped down version of the example code in the [Adafruit PN532 Library](https://github.com/adafruit/Adafruit-PN532) that waits for a Mifare Classic card to be detected and prints the UID to the serial port. The application continously polls the serial port for any new UID's and then matches that to an ID and signs the person in/out like normal.

Option 2: The software on the arduino is a modified version of the example code in the [RDM6300 Library](https://github.com/arduino12/rdm6300) that waits for a 125kHz card to be detected and prints the UID to the serial port. The application continously polls the serial port for any new UID's and then matches that to an ID and signs the person in/out like normal.

Source code for the ID Reader is in the following folders:
1. [ID_Reader_PN532 folder](https://github.com/AndyHegemann/FRC_TimeClock/tree/main/ID_Reader_PN532)
2. [ID_Reader_RDM6300 folder](https://github.com/AndyHegemann/FRC_TimeClock/tree/main/ID_Reader_RDM6300)
