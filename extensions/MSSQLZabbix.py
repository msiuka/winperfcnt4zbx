import re


def perfcnt_winreg_import():
    try:
        import winreg
    except ImportError:
        return None
    return winreg


class WindowsPerfCounterParser:
    """
    Parsing performance counters class

    Performance counters represents as string with two '\' delimeters. In case with installed MSSQL server with one
    or more instances in left part of performance counter has MSSQL instance delimeter with ':' symbol.

    \<MSSQL instance>:<group>(<parameter>)\<counter name>

    In case maybe has some other delimeters for other Windows Server services.
    Usual performance counters (disk performance and others) don't have delimeters.

    \<group>(<parameter>)\<counter name>
    """

    def __init__(self, rawstring, delimeters=None):
        """
        :param rawstring:
            String of performance counter name from windows
        :param delimeters:
            List of delimeters for founding instances in performance counters
            such as [":"] for founding MSSQL instances
        """
        if delimeters is None:
            delimeters = [":"]

        regexp = re.compile(r'\\(.*)(\(.*\))?\\(.*)')
        regexp_result = regexp.findall(rawstring)

        error_msg = "String '{}' did not match with windows performance counter's pattern".format(rawstring)

        try:
            parts = regexp_result[0]
        except IndexError:
            raise ValueError(error_msg)

        if len(parts) != 3:
            raise ValueError(error_msg)

        self.counter = parts[2]

        group = parts[0]
        index = -1
        open_bracket_cnt = 0
        if group[index] == ')':
            param = ''
            index -= 1
            while group[index] != '(' or open_bracket_cnt > 0:
                if group[index] == ')':
                    open_bracket_cnt += 1
                if group[index] == '(':
                    open_bracket_cnt -= 1
                param = group[index] + param
                index -= 1

            # self.parameter = group[group.find('('):].replace('(', '').replace(')', '')
            self.parameter = param
            # self.group = group[:group.find('(')]
            self.group = group.replace('(' + param + ')', '')
        else:
            self.group = group
            self.parameter = None

        for delmtr in delimeters:
            if delmtr in self.group:
                self.instance = self.group.split(delmtr)[0]
                self.group = self.group.replace(self.instance + delmtr, '')
                self.delimeter = delmtr
            else:
                self.instance = None
                self.delimeter = None

    @property
    def leftpart(self):
        """
        :return: left part string of performance counter
        """
        if self.instance is None:
            return self.group
        else:
            return self.instance + self.delimeter + self.group

    @staticmethod
    def get_perfcnt_from_win():
        """
        :return: lists with performance counters data from local machine:
                    * all performance counters on local machine
                    * number ids of performance counters
                    * descriptions of performance counters
        """
        winreg = perfcnt_winreg_import()
        if winreg is not None:
            import subprocess
            import chardet
            out = subprocess.run(["typeperf", "-qx"], stdout=subprocess.PIPE)
            cnt_data = out.stdout.decode(chardet.detect(out.stdout)['encoding']).splitlines()
            cnt_data = cnt_data[:-4]

            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                     "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Perflib\\CurrentLanguage")
            except FileNotFoundError:
                import platform

                bitness = platform.architecture()[0]
                other_view_flag = winreg.KEY_WOW64_64KEY
                if bitness == '64bit':
                    other_view_flag = winreg.KEY_WOW64_32KEY

                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                         "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Perflib\\CurrentLanguage",
                                         access=winreg.KEY_READ | other_view_flag)
                except FileNotFoundError:
                    return None

            cnt_ids, regtype = winreg.QueryValueEx(key, 'counter')
            descr, regtype = winreg.QueryValueEx(key, 'help')
            winreg.CloseKey(key)

            return cnt_data, cnt_ids, descr
        else:
            return None


class WindowsPerfCounterExporter:
    """Exporter performance counters class"""

    def __init__(self, group_tuple, counter_tuple, instance=None, parameter=None):
        """
        :param group_tuple: tuple of performance counter group (<name of group>, <number id of group>)
        :param counter_tuple: tuple of counter  (<name of counter>, <number id of counter>)
        :param instance: instance name of performance counter
        :param parameter: parameter name for performance counter
        """
        self.instance = instance
        self.group, self.group_id = group_tuple
        self.counter, self.counter_id = counter_tuple
        self.parameter = parameter

    def zbx_item_create(self, zabbix_api, template, id_representation=False):
        """
        Creates item in template thru zabbix api
        :param zabbix_api: ZabbixAPI object of pyzabbix package
        :param template: template object in zabbix created with pyzabbix package
        :param id_representation: boolean value that's mean create item of performance counter in current zabbix template
            with text or number representation. 'False' - creates items with text else creates with number id's
        :return: boolean value of successfully zabbix item creation and text message with info about zabbix item
        """
        if self.instance is None:
            appname = self.group
        else:
            appname = self.instance + " " + self.group

        zbx_applist = zabbix_api.application.get(
            hostids=template['templateids'][0],
            templated=True
        )
        app_id = ""
        for appitem in zbx_applist:
            if appitem['name'] == appname:
                app_id = appitem['applicationid']

        if app_id == "":
            new_app = zabbix_api.application.create(
                hostid=template['templateids'][0],
                name=appname
            )
            app_id = new_app['applicationids'][0]

        if id_representation:
            if self.parameter is None:
                itemkey = "\{0}\{1}".format(self.group_id, self.counter_id)
            else:
                itemkey = "\{0}({2})\{1}".format(self.group_id, self.counter_id, self.parameter)
        else:
            if self.instance is None:
                if self.parameter is None:
                    itemkey = "\{0}\{1}".format(self.group, self.counter)
                else:
                    itemkey = "\{0}({2})\{1}".format(self.group, self.counter, self.parameter)
            else:
                if self.parameter is None:
                    itemkey = "\{0}{1}\{2}".format(self.instance, self.group, self.counter)
                else:
                    itemkey = "\{0}{1}({3})\{2}".format(self.instance, self.group, self.counter, self.parameter)

        if self.parameter is None:
            itemname = "{0}: {1}".format(self.group, self.counter)
        else:
            itemname = "{0}({2}): {1}".format(self.group, self.counter, self.parameter)

        itemkey = 'perf_counter["{}"]'.format(itemkey)

        item = zabbix_api.item.create(
            hostid=template['templateids'][0],
            name=itemname,
            key_=itemkey,
            type=0,
            value_type=0,
            delay='1m',
            description='**AUTOCREATED**',
            applications=[app_id]
        )

        msg = "ZABBIX: item '{0}' in application '{1}' {2}"
        if item.get("itemids") is not None:
            if len(item["itemids"]) > 0:
                return True, msg.format(itemname, appname, "is created")
            else:
                return False, msg.format(itemname, appname, "is not created")
        else:
            return False, msg.format(itemname, appname, "is not created")
