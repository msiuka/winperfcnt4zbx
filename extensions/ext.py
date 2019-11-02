from app.models import *
from extensions.MSSQLZabbix import *
import os.path
import re

cnt_filepaths = ["counters_list.txt", "counters_id.txt", "counters_descr.txt"]
instance_delimeters = [":"]


def readfile(filename, enc):
    file = open(filename, 'r', encoding=enc)
    strings = file.read().splitlines()
    file.close()

    return strings


def is_perfcntfiles_exists():
    for paths in cnt_filepaths:
        if not os.path.exists(paths):
            return False
    return True


def fill_db(perfcounters, perflib, perfdescr, regexp):
    perf_ids = {}
    perf_descr = {}
    MSSQLixModel.clear_db()

    try:
        for i in range(0, len(perflib) - 1, 2):
            # some troubles with different dash sizes.
            perflib[i + 1] = perflib[i + 1].replace("—", "-")
            perflib[i + 1] = perflib[i + 1].replace("–", "-")
            perf_ids.update({perflib[i + 1]: int(perflib[i])})
    except ValueError:
        raise ValueError("Data structure of performance counters ids did not match with windows performance library pattern")

    # in data structure of counters description can be more than 1 line of description
    # after the string with id
    tmp_str = ""
    descr_id = 0
    for i in range(0, len(perfdescr) - 1):
        try:
            int(perfdescr[i])
            if tmp_str != "":
                perf_descr.update({descr_id: tmp_str})
                tmp_str = ""
            descr_id = int(perfdescr[i])
        except ValueError:
            tmp_str += perfdescr[i] + " "

    empty_instance, created = Instances.get_or_create(name=EMPTY_INSTANCE_TEXT_REPRESENTATION)
    empty_instance.save()

    prev_group = ''
    prev_cnt = ''

    for filestr in perfcounters:
        if re.search(regexp, filestr) is not None:
            perf_cnt = WindowsPerfCounterParser(filestr)
            skip_add = False

            try:
                perf_ids[perf_cnt.counter]
            except KeyError:
                if prev_cnt != perf_cnt.counter:
                    print("Couldn't find id for counter: {0}".format(perf_cnt.counter))
                    prev_cnt = perf_cnt.counter
                skip_add = True
            try:
                perf_ids[perf_cnt.leftpart]
            except KeyError:
                if prev_group != perf_cnt.leftpart:
                    print("Couldn't find id for group: {0}".format(perf_cnt.leftpart))
                    prev_group = perf_cnt.leftpart
                skip_add = True

            if not skip_add:
                if perf_cnt.instance is not None:
                    instance_rec, created = Instances.get_or_create(name=perf_cnt.instance)
                    instance_rec.delimeter = perf_cnt.delimeter
                    instance_rec.save()
                else:
                    instance_rec = empty_instance

                description = ""
                if perf_descr.get(perf_ids[perf_cnt.leftpart] + 1) is not None:
                    description = perf_descr[perf_ids[perf_cnt.leftpart] + 1]

                group_rec, created = CounterGroup.get_or_create(id=perf_ids[perf_cnt.leftpart], defaults={
                    'name': perf_cnt.group,
                    'instance_id': instance_rec,
                    'description': description
                })
                group_rec.save()

                description = ""
                if perf_descr.get(perf_ids[perf_cnt.counter] + 1) is not None:
                    description = perf_descr[perf_ids[perf_cnt.counter] + 1]

                counter_rec, created = Counters.get_or_create(id=perf_ids[perf_cnt.counter], defaults={
                    'name': perf_cnt.counter,
                    'counter_group_id': group_rec,
                    'description': description
                })
                counter_rec.save()

                if perf_cnt.parameter is not None:
                    parameter_rec, created = Parameters.get_or_create(name=perf_cnt.parameter, counter_group_id=group_rec)
                    parameter_rec.save()
