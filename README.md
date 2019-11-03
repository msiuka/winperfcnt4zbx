# Windows Performance Counters for Zabbix
Viewing, selecting and exporting windows performance counters to zabbix. Support export independent of system language type by performance counters id's. 
Used for creating items in zabbix 4.2 to get data from performance counters of MS SQL Server.
## Requirements
* Python 3.5
* Powershell 3.0 (if you will be use script to generate files)

## Installation
* Linux
```shell
git clone https://github.com/msiuka/winperfcnt4zbx.git
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
* Windows
```shell
git clone https://github.com/msiuka/winperfcnt4zbx.git
py -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Usage
Run app by command and go to http://127.0.0.1:5000/
```shell
python mssqlzbx.py
```
After usage you should deactivate python virtual envoirment by this command
```shell
deactivate
```
This app can get performance counters from current windows host where it will be running, but you can run this on any other place and get performance counters by powershell script **get_files.ps1**. This script generates 3 text files with performance counters data. You can put this files in root project directory or select them in settings page.

After first run you must go to settings page and fill regexp string for filtering performance counters for your needs. For example it will be filled for finding MSSQL instances. After getting data on main page will be showing all finded counters by instances and counter groups.

For exporting data to zabbix you must select some counters and parameters, fill url string to zabbix frontend (ex. http://127.0.0.1/zabbix/), template name (only template name that didn't exists) and zabbix credentials with access rights to create templates and items. This app don't store and send credentials anywhere.

## Thanks
* [Michael Klement](https://github.com/mklement0) for powershell [script](https://gist.github.com/mklement0/8689b9b5123a9ba11df7214f82a673be) to save files to UTF8 without BOM
